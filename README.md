# Developer
- Aaron Loo


# Overview
This project is a local AI study assistant that lets you ask questions about your own documents. You drop in your notes, textbooks, or worksheets, and it finds the most relevant sections and generates an answer using Google Gemini.

The retrieval is done using vector embeddings. Your documents are chunked, converted into numerical vectors, and stored in a local ChromaDB database. When you ask a question, it gets embedded the same way and the closest matching chunks are retrieved and sent to Gemini to generate the answer.

The app has a Streamlit web UI and supports chat history, document summaries, and AI-generated multiple-choice quizzes. Documents and the vector database are persisted to Google Cloud Storage so they survive container restarts.


## Tech Stack
| Component | Library |
| :---------| :-------|
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) |
| Vector database | `ChromaDB` |
| PDF parsing | `PyMuPDF (fitz)` |
| Word doc parsing | `python-docx` |
| LLM | Google Gemini 2.0 Flash via `google-genai` |
| Frontend | `Streamlit` |
| Cloud storage | `google-cloud-storage` (GCS) |
| Environment | `python-dotenv` |


### Pre-requisites
- Python 3.10+
- A Gemini API key from [aistudio.google.com](https://aistudio.google.com)
- (Optional) A Google Cloud Storage bucket for persistent storage across deployments


# User Documentation

### Getting Started
Follow the steps below to get the assistant running on your machine.

### Step 1. Clone the repo
```bash
git clone https://github.com/aaronloo1/RAG-study-assistant.git
cd RAG-study-assistant
```

### Step 2. Create and activate a virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3. Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4. Add your Gemini API key
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_key_here
```

Optionally, add your GCS bucket name to enable cloud persistence:
```
GCS_BUCKET_NAME=your_bucket_name_here
```

### Step 5. Start the app
```bash
streamlit run app.py
```

### Step 6. Upload and ingest documents
Use the sidebar to upload your documents and click **Ingest Documents**. This only needs to be done once per document, or whenever you add new ones.

### Step 7. Ask questions
Type your question in the chat input at the bottom. The assistant will find the most relevant passages and answer using Gemini.


## Features
- **Chat** — Ask questions about your documents with inline source citations
- **Document summaries** — Click "Summarize" on any document to get a 3–5 bullet-point summary
- **Named sessions** — Create, switch between, and delete named chat sessions
- **Quiz generator** — Generate multiple-choice quizzes from your documents, with optional topic filtering
- **Dark mode** — Toggle via the sidebar
- **CLI fallback** — Run `python main.py` for a simple terminal-based chat loop without the UI


## Supported File Types
| Format | Notes |
| :------| :-----|
| `.pdf` | Text-based PDFs only. Scanned/image PDFs are not supported |
| `.txt` | Plain text files |
| `.md` | Markdown files |
| `.docx` | Microsoft Word documents |


# Developer Documentation
The system is split into modules that each handle one part of the pipeline.

### Key Files

| File | Description |
| :----| :-----------|
| `app.py` | Streamlit web UI — sidebar controls, chat tab, quiz tab, dark mode |
| `main.py` | CLI entry point for terminal-based chat (no UI) |
| `src/ingest.py` | Reads files from `docs/`, chunks the text, embeds each chunk, and stores them in ChromaDB |
| `src/query.py` | Embeds the user's question and retrieves the top 8 most similar chunks from ChromaDB |
| `src/chat.py` | Builds a prompt from the retrieved chunks and sends it to Gemini to generate an answer; manages chat sessions |
| `src/quiz.py` | Generates multiple-choice quizzes from document chunks using Gemini |
| `src/storage.py` | Syncs `docs/`, `chroma_db/`, and `chat_sessions/` to and from Google Cloud Storage |


## How the System Works
1. `ingest.py` reads each document, splits it into overlapping word chunks (~200 words each, with a 2-sentence overlap), embeds them using `all-MiniLM-L6-v2`, and upserts them into a ChromaDB collection with their source filename stored as metadata
2. `query.py` embeds the question the same way and calls `collection.query()` to find the 8 nearest chunks by vector distance
3. `chat.py` formats those chunks into a prompt (with source labels and relevance scores) and calls the Gemini API, instructing it to cite sources inline and distinguish document knowledge from general knowledge
4. `storage.py` syncs all data to GCS on every ingest, delete, or session save — and pulls it all back down on startup so the app picks up where it left off after a restart
5. `app.py` runs the Streamlit frontend, bootstrapping from GCS before ChromaDB is initialized


## Docker
A `Dockerfile` is included for containerized deployment. It bakes the `all-MiniLM-L6-v2` embedding model into the image at build time so cold starts don't download ~90 MB from HuggingFace.

```bash
docker build -t rag-study-assistant .
docker run -p 8501:8501 \
  -e GEMINI_API_KEY=your_key \
  -e GCS_BUCKET_NAME=your_bucket \
  rag-study-assistant
```
