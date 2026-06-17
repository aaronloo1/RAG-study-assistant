# Developer
- Aaron Loo


# Overview
This project is a local AI study assistant that lets you ask questions about your own documents. You drop in your notes, textbooks, or worksheets, and it finds the most relevant sections and generates an answer using Google Gemini.

The retrieval is done using vector embeddings — your documents are chunked, converted into numerical vectors, and stored in a local ChromaDB database. When you ask a question, it's embedded the same way and the closest matching chunks are retrieved and sent to Gemini to generate the answer.


## Tech Stack
| Component | Library |
| :---------| :-------|
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) |
| Vector database | `ChromaDB` |
| PDF parsing | `PyMuPDF (fitz)` |
| LLM | Google Gemini 2.5 Flash via `google-genai` |
| Environment | `python-dotenv` |


### Pre-requisites
- Python 3.10+
- A Gemini API key from [aistudio.google.com](https://aistudio.google.com)


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
pip install sentence-transformers chromadb pymupdf python-dotenv google-genai
```

### Step 4. Add your Gemini API key
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_key_here
```

### Step 5. Add your documents
Drop any `.pdf`, `.txt`, or `.md` files into the `docs/` folder.

### Step 6. Ingest your documents
```bash
python src/ingest.py
```
Only needs to be run once, or whenever you add new documents.

### Step 7. Start the assistant
```bash
python main.py
```


## Usage
```
Ask a question (or 'quit' to exit): What is the difference between supervised and unsupervised learning?

Supervised learning uses labeled training data where the correct output is known...
```
Type `quit`, `exit`, or `q` to stop.


## Supported File Types
| Format | Notes |
| :------| :-----|
| `.pdf` | Text-based PDFs only — scanned/image PDFs are not supported |
| `.txt` | Plain text files |
| `.md` | Markdown files |


# Developer Documentation
The system is split into three files that each handle one part of the pipeline.

### Key Files

| File | Description |
| :----| :-----------|
| `src/ingest.py` | Reads files from `docs/`, chunks the text, embeds each chunk, and stores them in ChromaDB |
| `src/query.py` | Embeds the user's question and retrieves the top 5 most similar chunks from ChromaDB |
| `src/chat.py` | Builds a prompt from the retrieved chunks and sends it to Gemini to generate an answer |
| `main.py` | Entry point — adds `src/` to the Python path and runs the chat loop |


## How the System Works
1. `ingest.py` reads each document, splits it into overlapping word chunks, embeds them using `all-MiniLM-L6-v2`, and upserts them into a ChromaDB collection with their source filename stored as metadata
2. `query.py` embeds the question the same way and calls `collection.query()` to find the 5 nearest chunks by vector distance
3. `chat.py` formats those chunks into a prompt and calls the Gemini API, instructing it to only answer from the provided context
4. `main.py` adds `src/` to `sys.path` so all imports resolve correctly when run from the project root


## Project Structure
```
RAG-study-assistant/
├── main.py              
├── src/
│   ├── ingest.py        
│   ├── query.py         
│   └── chat.py          
├── docs/                # Your documents go here (gitignored)
├── chroma_db/           # Auto-generated vector database (gitignored)
└── .env                 # Your Gemini API key (gitignored)
```
