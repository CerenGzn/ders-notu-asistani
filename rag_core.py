import json
import os
import re
import faiss
import random
import numpy as np
import openai
from foundry_local import FoundryLocalManager
from sentence_transformers import SentenceTransformer
import config

INSUFFICIENT_MARKER = "NOT_ENOUGH_INFO"

QA_SYSTEM_PROMPT = f"""You are a study assistant. Answer the student's question using ONLY
the provided notes context, in clear and simple language. If not enough info, say {INSUFFICIENT_MARKER}.
"""

FLASHCARD_JSON_PROMPT = """Aşağıdaki notları kullanarak 5 adet çalışma kartı oluştur.
Çıktıyı SADECE geçerli bir JSON listesi olarak ver. Başka hiçbir açıklama yazma.

Format:
[
  {"front": "Soru veya Kavram 1", "back": "Açıklayıcı ve tam cevap 1"},
  {"front": "Soru veya Kavram 2", "back": "Açıklayıcı ve tam cevap 2"}
]
"""

class StudyEngine:
    def __init__(self):
        self.embedder = SentenceTransformer(config.EMBEDDING_MODEL)
        self.reload_index()

        self.manager = FoundryLocalManager(config.FOUNDRY_MODEL_ALIAS)
        self.client = openai.OpenAI(base_url=self.manager.endpoint, api_key=self.manager.api_key)
        self.model_id = self.manager.get_model_info(config.FOUNDRY_MODEL_ALIAS).id

    def reload_index(self):
        if not os.path.isfile(config.INDEX_PATH) or not os.path.isfile(config.META_PATH):
            raise FileNotFoundError("Document index not found. Run python ingest.py first.")
        index = faiss.read_index(config.INDEX_PATH)
        with open(config.META_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if index.ntotal != len(meta):
            raise ValueError("Index and metadata do not match. Run python ingest.py again.")
        self.index = index
        self.meta = meta

    def topics(self):
        return sorted(set(c["topic"] for c in self.meta))

    def retrieve(self, query: str, k: int, topic: str = None):
        if self.index.ntotal == 0 or k <= 0:
            return []
        q_vec = self.embedder.encode([query], normalize_embeddings=True)
        q_vec = np.asarray(q_vec, dtype="float32")
        fetch_k = k * 5 if topic else k
        scores, idxs = self.index.search(q_vec, min(fetch_k, self.index.ntotal))
        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            chunk = dict(self.meta[idx])
            if topic and chunk["topic"] != topic:
                continue
            chunk["score"] = float(score)
            results.append(chunk)
            if len(results) >= k:
                break
        return results

    def _context_block(self, chunks):
        return "\n\n".join(f"--- {c['file']} ---\n{c['text']}" for c in chunks)

    def _chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 800) -> str:
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()

    def answer(self, query: str, topic: str = None):
        chunks = self.retrieve(query, config.TOP_K, topic)
        if not chunks:
            return "Bu soruyla ilgili not bulunamadı.", [], False
        prompt = f"Notes:\n{self._context_block(chunks)}\n\nQuestion: {query}\n\nAnswer:"
        text = self._chat(QA_SYSTEM_PROMPT, prompt, temperature=0.0)

        if INSUFFICIENT_MARKER in text:
            wide_chunks = self.retrieve(query, config.TOP_K_FALLBACK, topic)
            wide_prompt = f"Notes:\n{self._context_block(wide_chunks)}\n\nQuestion: {query}\n\nAnswer:"
            wide_text = self._chat(QA_SYSTEM_PROMPT, wide_prompt, temperature=0.0)
            if INSUFFICIENT_MARKER in wide_text:
                return "Notlarımda bu soruyu güvenle cevaplayacak yeterli bilgi yok.", wide_chunks, True
            return wide_text, wide_chunks, True

        return text, chunks, False

    def generate_quiz(self, topic: str, n_questions: int = 5):
        all_chunks = self.retrieve(topic or "notlar", k=15, topic=topic if topic != "(hepsi)" else None)
        if not all_chunks:
            all_chunks = self.meta

        if not all_chunks:
            return [], "No indexed study notes available."

        quizzes = []
        raw_all = ""
        letter_to_idx = {"A": 0, "B": 1, "C": 2, "D": 3}
        
        QUIZ_TEXT_PROMPT = """Aşağıdaki notları incele ve 1 adet çoktan seçmeli test sorusu üret.
Format:
SORU: [Soru]
A) [Şık 1]
B) [Şık 2]
C) [Şık 3]
D) [Şık 4]
CEVAP: [A, B, C veya D]
AÇIKLAMA: [Açıklama]
---"""

        attempts = 0
        while len(quizzes) < n_questions and attempts < 12:
            attempts += 1
            sampled_chunks = random.sample(all_chunks, min(2, len(all_chunks)))
            prompt = f"Notes:\n{self._context_block(sampled_chunks)}\n\nSoru yaz."
            
            raw = self._chat(QUIZ_TEXT_PROMPT, prompt, temperature=0.85, max_tokens=500)
            raw_all += f"\n--- Deneme {attempts} ---\n" + raw

            lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
            q_text = ""
            options = []
            correct_idx = None
            explanation = "Açıklama yok."

            for line in lines:
                if line.startswith("SORU:"):
                    q_text = line.replace("SORU:", "").strip()
                elif re.match(r"^[A-Da-d][\)\.]", line):
                    options.append(re.sub(r"^[A-Da-d][\)\.]", "", line).strip())
                elif line.startswith("CEVAP:"):
                    ans_let = line.replace("CEVAP:", "").strip().upper()
                    correct_idx = letter_to_idx.get(ans_let[0] if ans_let else "")
                elif line.startswith("AÇIKLAMA:"):
                    explanation = line.replace("AÇIKLAMA:", "").strip()

            if q_text and len(options) == 4 and correct_idx is not None:
                quizzes.append({
                    "question": q_text,
                    "options": options[:4],
                    "correct_index": correct_idx,
                    "explanation": explanation
                })

        return quizzes, raw_all

    def generate_flashcards(self, topic: str, n_cards: int = 5):
        chunks = self.retrieve(topic or "notlar", k=config.TOP_K_FALLBACK, topic=topic if topic != "(hepsi)" else None)
        if not chunks:
            chunks = self.meta[:3]
        
        if not chunks:
            return [], "No indexed study notes available."
        prompt = f"Notes:\n{self._context_block(chunks)}\n\nJSON formatında 5 çalışma kartı üret."
        raw = self._chat(FLASHCARD_JSON_PROMPT, prompt, temperature=0.3, max_tokens=1000)
        
        cards = []
        
        # 1. Deneme: Direkt JSON parse et
        try:
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                cards = json.loads(match.group(0))
        except Exception:
            pass

        # 2. Deneme: Model bozuk JSON (virgül yerine sayı vs.) yazdıysa Regex ile objeleri tek tek çek
        if not cards:
            matches = re.findall(r'\{\s*"front"\s*:\s*"(.*?)"\s*,\s*"back"\s*:\s*"(.*?)"\s*\}', raw, re.DOTALL)
            for f, b in matches:
                cards.append({"front": f, "back": b})

        return cards, raw
