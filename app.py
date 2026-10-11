import json
import os
import time

import streamlit as st

import config
from ingest import main as rebuild_index
from rag_core import StudyEngine


st.set_page_config(page_title="Ders Notu Asistanı", layout="wide")
st.title("Offline Ders Notu Asistanı (Foundry Local RAG)")


@st.cache_resource
def load_engine():
    return StudyEngine()


def load_json(path, default):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


st.sidebar.header("📁 Not & Kaynak Yönetimi")
uploaded_files = st.sidebar.file_uploader(
    "Yeni ders notu ekle",
    type=["pdf", "docx", "txt", "md"],
    accept_multiple_files=True,
)

if uploaded_files:
    os.makedirs(config.NOTES_DIR, exist_ok=True)
    changed_files = []
    for uploaded_file in uploaded_files:
        # Uploaded files must stay inside the notes directory.
        name = os.path.basename(uploaded_file.name.replace("\\", "/"))
        if not name or name.startswith("."):
            st.sidebar.error("Geçersiz dosya adı.")
            continue
        path = os.path.join(config.NOTES_DIR, name)
        content = uploaded_file.getvalue()
        try:
            existing = None
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    existing = f.read()
            if existing != content:
                with open(path, "wb") as f:
                    f.write(content)
                changed_files.append(name)
        except OSError as exc:
            st.sidebar.error(f"Dosya kaydedilemedi: {exc}")

    if changed_files:
        with st.sidebar:
            with st.spinner("Yeni notlar indeksleniyor..."):
                try:
                    rebuild_index()
                except Exception as exc:
                    st.error(f"İndeks güncellenemedi: {exc}")
                else:
                    load_engine.clear()
                    st.success(f"{len(changed_files)} dosya kaydedildi, indeks güncellendi.")
                    st.rerun()

st.sidebar.divider()

try:
    engine = load_engine()
except (FileNotFoundError, ValueError) as exc:
    st.error(str(exc))
    st.info("Önce `python ingest.py` komutuyla örnek notların indeksini oluştur.")
    st.stop()
except Exception as exc:
    st.error(f"AI modeli başlatılamadı: {exc}")
    st.info("Microsoft Foundry Local kurulumunu ve model ayarlarını kontrol et.")
    st.stop()

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
if "quiz_scored" not in st.session_state:
    st.session_state.quiz_scored = False

if mode == "Soru-Cevap":
    _, control = st.columns([4, 1])
    with control:
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
                with st.expander(
                    f"📚 Kaynaklar ({len(turn['sources'])} Parça) · "
                    f"{turn.get('elapsed', 0):.1f}s"
                ):
                    for i, src in enumerate(turn["sources"], 1):
                        st.markdown(
                            f"**Kaynak {i}:** `{src['file']}` "
                            f"(Skor: {src.get('score', 0):.2f})"
                        )
                        st.caption(src.get("text", "Metin detayı yok."))

    question = st.chat_input("Notların hakkında bir soru sor...")
    if question:
        with st.chat_message("user"):
            st.write(question)
        try:
            start = time.time()
            answer, chunks, _ = engine.answer(question, selected_topic)
            elapsed = time.time() - start
        except Exception as exc:
            st.error(f"Cevap oluşturulamadı: {exc}")
        else:
            sources = [
                {"file": c["file"], "score": c["score"], "text": c["text"]}
                for c in chunks
            ]
            with st.chat_message("assistant"):
                st.write(answer)
                with st.expander(f"📚 Kaynaklar ({len(sources)} Parça) · {elapsed:.1f}s"):
                    for i, src in enumerate(sources, 1):
                        st.markdown(
                            f"**Kaynak {i}:** `{src['file']}` "
                            f"(Skor: {src['score']:.2f})"
                        )
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
        st.session_state.quiz_scored = False
        with st.spinner("Model 5 adet soru üretiyor, biraz zaman alabilir..."):
            try:
                quiz_data, raw_out = engine.generate_quiz(quiz_topic, n_questions=5)
            except Exception as exc:
                st.error(f"Quiz oluşturulamadı: {exc}")
            else:
                st.session_state.quiz = quiz_data
                st.session_state.quiz_raw = raw_out
                st.session_state.quiz_topic = quiz_topic

    if st.session_state.quiz:
        st.info(f"Toplam {len(st.session_state.quiz)} soru yüklendi.")
        answers = {}
        for i, q in enumerate(st.session_state.quiz):
            st.markdown(f"**{i + 1}. {q['question']}**")
            answers[i] = st.radio(
                f"Soru {i + 1} seçenekleri",
                q["options"],
                key=f"quiz_{id(st.session_state.quiz)}_{i}",
                index=None,
                label_visibility="collapsed",
                disabled=st.session_state.quiz_scored,
            )

        if st.button("Cevapları kontrol et", disabled=st.session_state.quiz_scored):
            correct_count = 0
            for i, q in enumerate(st.session_state.quiz):
                correct_answer = q["options"][q["correct_index"]]
                is_correct = answers[i] == correct_answer
                correct_count += int(is_correct)
                icon = "✅" if is_correct else "❌"
                st.write(
                    f"{icon} Soru {i + 1}: doğru cevap **{correct_answer}** "
                    f"— {q['explanation']}"
                )
            prog = st.session_state.progress.setdefault(
                st.session_state.quiz_topic, {"correct": 0, "total": 0}
            )
            prog["correct"] += correct_count
            prog["total"] += len(st.session_state.quiz)
            save_json(config.PROGRESS_PATH, st.session_state.progress)
            st.session_state.quiz_scored = True
            st.success(f"Sonuç: {correct_count}/{len(st.session_state.quiz)}")
    elif st.session_state.quiz_raw:
        st.error("Model çıktı üretti ancak sorular ayrıştırılamadı.")
        st.code(st.session_state.quiz_raw)

elif mode == "Flashcard":
    fc_topic = selected_topic or "(hepsi)"
    st.subheader(f"Flashcard: {fc_topic}")
    if st.button("Yeni flashcard seti oluştur"):
        st.session_state.flashcards = None
        st.session_state.fc_raw = None
        with st.spinner("Flashcardlar oluşturuluyor..."):
            try:
                cards, raw_out = engine.generate_flashcards(fc_topic, n_cards=5)
            except Exception as exc:
                st.error(f"Flashcard oluşturulamadı: {exc}")
            else:
                st.session_state.flashcards = cards
                st.session_state.fc_raw = raw_out

    if st.session_state.flashcards:
        valid_cards = 0
        for card in st.session_state.flashcards:
            if not isinstance(card, dict) or not card:
                continue
            values = list(card.values())
            front = (card.get("front") or card.get("soru") or card.get("Soru")
                     or card.get("Q") or values[0])
            back = (card.get("back") or card.get("cevap") or card.get("Cevap")
                    or card.get("A") or values[-1])
            valid_cards += 1
            with st.expander(f"📌 {valid_cards}. {front}"):
                st.markdown(f"**Cevap:** {back}")
        if not valid_cards:
            st.warning("Kartlar ayrıştırılamadı.")
            st.code(st.session_state.fc_raw)
    elif st.session_state.fc_raw:
        st.warning("Kartlar standart formatta ayrıştırılamadı. Model çıktısı:")
        st.code(st.session_state.fc_raw)

elif mode == "İlerleme":
    st.subheader("Konu bazında ilerleme")
    if not st.session_state.progress:
        st.info("Henüz quiz çözülmedi. 'Quiz' modundan başla.")
    else:
        for topic_name, stats in st.session_state.progress.items():
            total = stats["total"]
            pct = 100 * stats["correct"] / total if total else 0
            st.write(
                f"**{topic_name}**: {stats['correct']}/{total} doğru ({pct:.0f}%)"
            )
            st.progress(pct / 100)
