# 📚 Offline Ders Notu Asistanı (Foundry Local RAG)

Bu proje, ders notlarınızı (PDF, TXT, DOCX) kullanarak çevrimdışı çalışan, veri gizliliğini ön planda tutan RAG tabanlı bir çalışma asistanıdır.

---

### 🛠️ Proje Mimari Yapısı

Proje, yerel makinede yüksek performansla çalışmak üzere tasarlanmıştır:

- **Frontend:** Streamlit
- **LLM Engine:** Foundry Local
- **Vector Indexing:** FAISS
- **Embeddings:** sentence-transformers (`all-MiniLM-L6-v2`)
- **Veri Saklama:** Local JSON & Vector Index

---

### ✨ Temel Özellikler

- **💬 Soru-Cevap (QA):** Ders notlarınızdan doğrudan yanıt üretir. Yetersiz bilgi durumunda arama kapsamını otomatik genişletir ve kaynak gösterir.
- **📝 Quiz Modu:** Notlara dayalı çoktan seçmeli sorular üretir, yanıtları değerlendirir ve açıklama sunar.
- **🗂️ Flashcard:** Notlardaki kritik kavramları tespit ederek soru-cevap kartları oluşturur.
- **📊 İlerleme Takibi:** Çözülen quiz performansını konu bazında saklar.

---

### 🚀 Kurulum ve Çalıştırma

#### 1. Gereksinimler
- Python 3.9+
- Foundry Local (Yerel model servisi)

#### 2. Adım Adım Kurulum

1. Proje klasörüne gidin:
```bash
cd ders-notu-asistani
