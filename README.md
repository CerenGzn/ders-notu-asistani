# Offline AI Study Assistant

A local study assistant built with Python, Streamlit, and Microsoft Foundry Local. The application uses Retrieval-Augmented Generation (RAG) to answer questions based on course notes rather than relying only on the language model's existing knowledge.

I developed this project during my software engineering internship at Microsoft to explore local LLM inference and integrate it into a practical learning application.

The assistant supports PDF, DOCX, TXT, and Markdown documents and includes question answering, quiz generation, flashcards, and learning progress tracking.

## Features

- **Document-based Q&A:** Ask questions about course notes and receive answers based on relevant document content, with source references.
- **Quiz generation:** Generate multiple-choice questions from study materials, check answers, and receive explanations.
- **Flashcards:** Create flashcards from uploaded study materials to review important concepts.
- **Progress tracking:** Save quiz results locally and track performance across different topics.
- **Local inference:** Run the language model through Microsoft Foundry Local without relying on an external hosted LLM API.

## Technologies Used

- **Python** — Application logic and document processing
- **Streamlit** — User interface
- **Microsoft Foundry Local** — Local LLM inference
- **Phi-3.5 Mini** — Language model
- **FAISS** — Vector similarity search
- **Sentence Transformers (all-MiniLM-L6-v2)** — Text embeddings
- **NumPy** — Vector processing
- **JSON** — Local storage for metadata, chat history, and learning progress

## How It Works

The application uses a RAG pipeline to retrieve relevant information from study materials before generating a response.

First, documents are converted into text and divided into smaller, overlapping chunks. Each chunk is converted into an embedding using `all-MiniLM-L6-v2` and stored in a FAISS vector index.

When a user asks a question, the application searches the index for relevant content and passes the retrieved text to the language model as context.

If the available context is insufficient, the system can retry the retrieval process with a larger set of document chunks.

The same retrieval process is also used to generate quizzes and flashcards based on the uploaded materials.

All language model inference is handled locally using Microsoft Foundry Local.

## Project Structure

```text
app.py             Streamlit application
rag_core.py        RAG pipeline and LLM integration
ingest.py          Document processing and indexing
config.py          Application settings
requirements.txt   Python dependencies
notes/             Sample study notes
README.md          Project documentation
```

The FAISS index and document metadata are generated locally and are not included in the repository.

## Running Locally

### Requirements

- Python and the required dependencies
- Microsoft Foundry Local installed and configured
- A compatible local language model, configured as `phi-3.5-mini`

### 1. Clone the repository

```bash
git clone https://github.com/CerenGzn/ders-notu-asistani.git
cd ders-notu-asistani
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Add study materials

Place your documents in the `notes/` folder.

Supported formats include PDF, DOCX, TXT, and Markdown.

The repository includes sample study notes for testing.

### 4. Build the document index

```bash
python ingest.py
```

This processes the documents and generates the FAISS vector index and its metadata.

Run this command again whenever documents are added, removed, or modified.

### 5. Run the application

```bash
streamlit run app.py
```

The application opens in your browser.

Make sure Microsoft Foundry Local is properly installed and the configured model is available before using the AI features.

The first run may require downloading the embedding model and the local language model.

## Notes

- The application uses local model inference and stores its data locally.
- Generated answers, quizzes, and flashcards depend on the quality of the uploaded documents and the language model.
- Document indexing is handled separately through `ingest.py`.
- Adding new documents requires rebuilding the index.
- This project was developed as an internship application and has not been packaged as a production service.

## Author

**Ceren Güzen**

Software Engineering | Data Science & AI

[GitHub](https://github.com/CerenGzn) | [LinkedIn](https://www.linkedin.com/in/ceren-guzen-18aa73332/)
