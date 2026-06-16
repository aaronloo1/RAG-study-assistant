import os
import chromadb
from sentence_transformers import SentenceTransformer
import fitz  # PyMuPDF

# --- Setup ---
DOCS_FOLDER = "docs"
DB_FOLDER = "chroma_db"

client = chromadb.PersistentClient(path=DB_FOLDER)
collection = client.get_or_create_collection(name="study_docs")
model = SentenceTransformer("all-MiniLM-L6-v2")


def extract_text_from_pdf(path):
  doc = fitz.open(path)
  return "\n".join(page.get_text() for page in doc)


def extract_text_from_txt(path):
  with open(path, "r", encoding="utf-8") as f:
    return f.read()


def chunk_text(text, chunk_size=500, overlap=50):
  words = text.split()
  chunks = []
  i = 0
  while i < len(words):
    chunk = " ".join(words[i:i + chunk_size])
    chunks.append(chunk)
    i += chunk_size - overlap
  return chunks


def ingest_documents():
  for filename in os.listdir(DOCS_FOLDER):
    path = os.path.join(DOCS_FOLDER, filename)

    if not os.path.isfile(path):
      continue

    if filename.endswith(".pdf"):
      text = extract_text_from_pdf(path)
    elif filename.endswith(".txt") or filename.endswith(".md"):
      text = extract_text_from_txt(path)
    else:
      print(f"Skipping unsupported file: {filename}")
      continue

    chunks = chunk_text(text)
    embeddings = model.encode(chunks).tolist()

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
      collection.upsert(
          documents=[chunk],
          embeddings=[embedding],
          ids=[f"{filename}_chunk_{i}"],
          metadatas=[{"source": filename}]
      )

    print(f"Ingested {len(chunks)} chunks from {filename}")


if __name__ == "__main__":
  ingest_documents()
  print("Done! All documents ingested.")
