import eval_type_backport
import json
import os
import time
import subprocess
import streamlit as st
import config
from rag_core import StudyEngine

@st.cache_resource
def load_engine():
    return StudyEngine()

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

st.set_page_config(page_title="Ders Notu Asistanı", layout="wide")
st.title("Offline Ders Notu Asistanı (Foundry Local RAG)")

st.sidebar.header("📁 Not & Kaynak Yönetimi")

uploaded_files = st.sidebar.file_uploader(
    "Yeni ders notu ekle", 
    type=["pdf", "docx", "txt", "md"], 
    accept_multiple_files=True
)

if uploaded_files:
    os.makedirs(config.NOTES_DIR, exist_ok=True)
    for uploaded_file in uploaded_files:
        file_path = os.path.join(config.NOTES_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"{len(uploaded_files)} dosya yüklendi!")

st.sidebar.divider()

engine = load_engine()
topics = engine.topics()

mode = st.sidebar.radio("Mod", ["Soru-Cevap", "Quiz", "Flashcard", "İlerleme"])
topic_filter = st.sidebar.selectbox("Konu (isteğe bağlı filtre)", ["(hepsi)"] + topics)
selected_topic = None if topic_filter == "(hepsi)" else topic_filter

if "history" not in st.session_state:
    st.session_state.history = load_json(config.CHAT_HISTORY_PATH, [])
if "progress" not in st.session_state:
    st.session_state.progress = load_json(config.PROGRESS_PATH, {})
if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "quiz_raw" not in st.session_state:
    st.session_state.quiz_raw = None
if "flashcards" not in st.session_state:
    st.session_state.flashcards = None
if "fc_raw" not in st.session_state:
    st.session_state.fc_raw = None

if mode == "Soru-Cevap":
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🗑️ Sohbeti Temizle"):
            st.session_state.history = []
            save_json(config.CHAT_HISTORY_PATH, [])
            st.rerun()

    for turn in st.session_state.history:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            st.write(turn["answer"])
            if turn.get("sources"):
                with st.expander(f"📚 Kaynaklar ({len(turn['sources'])} Parça) · {turn.get('elapsed', 0):.1f}s"):
                    for idx, src in enumerate(turn["sources"]):
                        st.markdown(f"**Kaynak {idx+1}:** `{src['file']}` (Skor: {src.get('score', 0):.2f})")
                        st.caption(src.get("text", "Metin detayı yok."))

    question = st.chat_input("Notların hakkında bir soru sor...")
    if question:
        with st.chat_message("user"):
            st.write(question)
        start = time.time()
        answer, chunks, widened = engine.answer(question, selected_topic)
        elapsed = time.time() - start
        sources = [{"file": c["file"], "score": c["score"], "text": c["text"]} for c in chunks]

        with st.chat_message("assistant"):
            st.write(answer)
            with st.expander(f"📚 Kaynaklar ({len(sources)} Parça) · {elapsed:.1f}s"):
                for idx, src in enumerate(sources):
                    st.markdown(f"**Kaynak {idx+1}:** `{src['file']}` (Skor: {src['score']:.2f})")
                    st.caption(src["text"])

        st.session_state.history.append(
            {"question": question, "answer": answer, "sources": sources, "elapsed": elapsed}
        )
        save_json(config.CHAT_HISTORY_PATH, st.session_state.history)

elif mode == "Quiz":
    quiz_topic = selected_topic or "(hepsi)"
    st.subheader(f"Quiz: {quiz_topic}")

    if st.button("Yeni quiz oluştur"):
        st.session_state.quiz = None
        st.session_state.quiz_raw = None
        with st.spinner("Model sırayla 5 adet soru üretiyor, biraz zaman alabilir..."):
            quiz_data, raw_out = engine.generate_quiz(quiz_topic, n_questions=5)
            st.session_state.quiz = quiz_data
            st.session_state.quiz_raw = raw_out
            st.session_state.quiz_topic = quiz_topic
            st.session_state.quiz_answers = {}

    if st.session_state.quiz:
        st.info(f"Toplam {len(st.session_state.quiz)} soru yüklendi.")
        for i, q in enumerate(st.session_state.quiz):
            st.markdown(f"**{i + 1}. {q['question']}**")
            choice = st.radio("", q["options"], key=f"q_{i}", index=None, label_visibility="collapsed")
            st.session_state.quiz_answers[i] = choice

        if st.button("Cevapları kontrol et"):
            correct_count = 0
            qt = st.session_state.quiz_topic
            prog = st.session_state.progress.setdefault(qt, {"correct": 0, "total": 0})
            for i, q in enumerate(st.session_state.quiz):
                chosen = st.session_state.quiz_answers.get(i)
                correct_answer = q["options"][q["correct_index"]] if q["correct_index"] < len(q["options"]) else q["options"][0]
                is_correct = chosen == correct_answer
                correct_count += is_correct
                prog["total"] += 1
                prog["correct"] += int(is_correct)
                icon = "✅" if is_correct else "❌"
                st.write(f"{icon} Soru {i + 1}: doğru cevap **{correct_answer}** — {q['explanation']}")
            st.success(f"Sonuç: {correct_count}/{len(st.session_state.quiz)}")
            save_json(config.PROGRESS_PATH, st.session_state.progress)
    elif st.session_state.quiz_raw and not st.session_state.quiz:
        st.error("Model çıktı üretti ama ayrıştırılamadı. Model çıktısı:")
        st.code(st.session_state.quiz_raw)

elif mode == "Flashcard":
    fc_topic = selected_topic or "(hepsi)"
    st.subheader(f"Flashcard: {fc_topic}")

    if st.button("Yeni flashcard seti oluştur"):
        st.session_state.flashcards = None
        st.session_state.fc_raw = None
        with st.spinner("Flashcardlar oluşturuluyor..."):
            cards, raw_out = engine.generate_flashcards(fc_topic, n_cards=5)
            st.session_state.flashcards = cards
            st.session_state.fc_raw = raw_out

    if st.session_state.flashcards:
        valid_cards = 0
        for i, card in enumerate(st.session_state.flashcards):
            if isinstance(card, dict):
                # Olası tüm anahtar isimlerini yakala
                front = card.get("front") or card.get("soru") or card.get("Soru") or card.get("Q") or list(card.values())[0] if card else "Soru Yok"
                back = card.get("back") or card.get("cevap") or card.get("Cevap") or card.get("A") or list(card.values())[-1] if len(card) > 1 else "Cevap Yok"
                
                with st.expander(f"📌 {valid_cards + 1}. {front}"):
                    st.markdown(f"**Cevap:** {back}")
                valid_cards += 1

        if valid_cards == 0:
            st.warning("Çıktı ayrıştırılamadı. Ham çıktı:")
            st.code(st.session_state.fc_raw)
    elif st.session_state.fc_raw:
        st.warning("Kartlar standart formatta ayrıştırılamadı. Model çıktısı aşağıdadır:")
        st.code(st.session_state.fc_raw)

elif mode == "İlerleme":
    st.subheader("Konu bazında ilerleme")
    if not st.session_state.progress:
        st.info("Henüz quiz çözülmedi. 'Quiz' modundan başla.")
    else:
        for topic_name, stats in st.session_state.progress.items():
            total = stats["total"] or 1
            pct = 100 * stats["correct"] / total
            st.write(f"**{topic_name}**: {stats['correct']}/{stats['total']} doğru ({pct:.0f}%)")
            st.progress(pct / 100)
