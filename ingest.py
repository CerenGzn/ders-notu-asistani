import json
import os
import faiss
import numpy as np
from pypdf import PdfReader
from docx import Document as DocxDocument
from sentence_transformers import SentenceTransformer
import config

def read_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def read_docx(path: str) -> str:
    doc = DocxDocument(path)
    return "\n".join(p.text for p in doc.paragraphs)

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

READERS = {".pdf": read_pdf, ".docx": read_docx, ".txt": read_text, ".md": read_text}

def iter_source_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fname in sorted(filenames):
            ext = os.path.splitext(fname)[1].lower()
            if ext in config.INDEXED_EXTENSIONS:
                yield os.path.join(dirpath, fname)

def chunk_text(text: str, source: str):
    chunks = []
    step = config.CHUNK_CHARS - config.CHUNK_OVERLAP
    if step <= 0:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_CHARS")
    for start in range(0, len(text), step):
        end = min(start + config.CHUNK_CHARS, len(text))
        piece = text[start:end].strip()
        if piece:
            topic = os.path.relpath(source, config.NOTES_DIR).split(os.sep)[0]
            chunks.append({"file": source, "topic": topic, "text": piece})
        if end == len(text):
            break
    return chunks

def main():
    if not os.path.isdir(config.NOTES_DIR):
        raise SystemExit(f"'{config.NOTES_DIR}' not found. Create it and add your PDF/DOCX/TXT notes.")

    print(f"Scanning {config.NOTES_DIR} ...")
    all_chunks = []
    for path in iter_source_files(config.NOTES_DIR):
        ext = os.path.splitext(path)[1].lower()
        try:
            text = READERS[ext](path)
        except Exception as e:
            print(f"  Skipping {path}: {e}")
            continue
        new_chunks = chunk_text(text, path)
        all_chunks.extend(new_chunks)
        print(f"  {path}: {len(new_chunks)} chunks")

    if not all_chunks:
        raise SystemExit("No readable content found. Add some files to notes/ first.")

    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Loading embedding model '{config.EMBEDDING_MODEL}' ...")
    model = SentenceTransformer(config.EMBEDDING_MODEL)

    print("Embedding ...")
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.asarray(embeddings, dtype="float32")

    print("Building FAISS index ...")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    index_tmp = config.INDEX_PATH + ".tmp"
    meta_tmp = config.META_PATH + ".tmp"
    faiss.write_index(index, index_tmp)
    with open(meta_tmp, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    os.replace(index_tmp, config.INDEX_PATH)
    os.replace(meta_tmp, config.META_PATH)

    topics = sorted(set(c["topic"] for c in all_chunks))
    print(f"\nDone. Indexed {len(all_chunks)} chunks across topics: {', '.join(topics)}")

if __name__ == "__main__":
    main()
