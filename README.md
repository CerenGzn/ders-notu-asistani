# Offline AI Study Assistant

A local study assistant built with Python, Streamlit, and Microsoft Foundry Local. The application uses Retrieval-Augmented Generation (RAG) to answer questions from uploaded course notes rather than relying only on the language model's existing knowledge.

I developed this project during my software engineering internship at Microsoft to explore local LLM inference and how it can be integrated into a practical application.

The assistant can work with PDF, DOCX, TXT, and Markdown files. It also includes quiz generation, flashcards, and basic progress tracking.

## Features

- **Document-based Q&A:** Ask questions about course notes and receive answers based on retrieved content, with references to the source documents.
- **Quiz generation:** Generate multiple-choice questions from study materials, check answers, and view explanations.
- **Flashcards:** Create revision cards from the content of uploaded notes.
- **Progress tracking:** Save quiz results locally and track performance by topic.
- **Local inference:** Run the language model through Microsoft Foundry Local without sending prompts to an external hosted LLM API.

## Tech Stack

- **Python** — Main application and processing logic
- **Streamlit** — User interface
- **Microsoft Foundry Local** — Local LLM inference
- **Phi-3.5 Mini** — Language model
- **FAISS** — Vector similarity search
- **Sentence Transformers (all-MiniLM-L6-v2)** — Text embeddings
- **NumPy** — Vector processing
- **JSON** — Local storage for metadata, chat history, and quiz progress

## How It Works

The application has two main parts: document indexing and question answering.

During indexing, the uploaded study materials are converted into text and divided into overlapping chunks. The chunks are embedded using `all-MiniLM-L6-v2` and stored in a FAISS index alongside their source metadata.

When a question is submitted, the system retrieves the most relevant chunks and passes them to the local language model as context. If the model indicates that the retrieved information is insufficient, the application retries with a larger retrieval set.

The quiz and flashcard features use the same document retrieval process to generate study material based on the user's notes.

## Project Structure

The main application files are located in the `ders-notu-asistani.pdf/` directory.

```text
app.py             Streamlit interface
rag_core.py        Retrieval, LLM calls, quiz and flashcard generation
ingest.py          Document parsing, chunking and indexing
config.py          Model and retrieval settings
requirements.txt   Python dependencies
notes/             Study documents
index.faiss        FAISS vector index
meta.json          Document chunk metadata
```

## Running Locally

**Requirements**

- Python environment with the required dependencies
- Microsoft Foundry Local installed and configured
- A compatible local model (configured as `phi-3.5-mini`)

**1. Clone the repository**

```bash
git clone https://github.com/CerenGzn/ders-notu-asistani.git
cd ders-notu-asistani/ders-notu-asistani.pdf
```

**2. Install dependencies**

```bash
python -m pip install -r requirements.txt
```

**3. Prepare the documents**

Place supported study documents in the `notes/` folder.

**4. Build the document index**

```bash
python ingest.py
```

This creates the FAISS index and metadata files used by the application. Run this command again when adding or changing study documents.

**5. Start the application**

```bash
streamlit run app.py
```

The application opens in your browser, where you can select a topic and use the study features.

The first run may require downloading the embedding model and the local language model.

## Notes

- The application uses local model inference and stores its application data locally.
- Quiz and flashcard quality depends on the language model and the content of the notes.
- Document indexing is currently a separate step. Uploading a new file through the interface does not automatically rebuild the FAISS index.
- The project was developed as an internship application and has not been packaged as a production service.

## Author

Ceren Güzen

Software Engineering | Data Science & AI

[GitHub](https://github.com/CerenGzn) | [LinkedIn](https://www.linkedin.com/in/ceren-guzen-18aa73332/)
