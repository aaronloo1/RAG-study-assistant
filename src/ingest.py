import os
import re
import chromadb
from sentence_transformers import SentenceTransformer
import fitz  # PyMuPDF
import docx  # python-docx

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


def extract_text_from_docx(path):
  document = docx.Document(path)
  return "\n".join(para.text for para in document.paragraphs)


def _split_sentences(text: str) -> list[str]:
  # Collapse 3+ newlines to a paragraph break, then split on sentence-ending
  # punctuation OR paragraph breaks so chunks never cut mid-sentence.
  text = re.sub(r'\n{3,}', '\n\n', text)
  parts = re.split(r'(?<=[.!?])\s+|\n\n', text)
  return [p.strip() for p in parts if p.strip()]


def chunk_text(text, target_words=200, overlap_sentences=2):
  sentences = _split_sentences(text)
  if not sentences:
    return []
  chunks = []
  i = 0
  while i < len(sentences):
    group, word_count, j = [], 0, i
    while j < len(sentences) and word_count < target_words:
      group.append(sentences[j])
      word_count += len(sentences[j].split())
      j += 1
    chunks.append(" ".join(group))
    # Overlap: step forward but keep the last N sentences for the next chunk.
    i = max(i + 1, j - overlap_sentences)
  return chunks


def delete_document(filename: str):
  results = collection.get(where={"source": filename})
  if results["ids"]:
    collection.delete(ids=results["ids"])


def is_already_ingested(filename):
  results = collection.get(where={"source": filename}, limit=1)
  return len(results["ids"]) > 0


def ingest_documents():
  summary = {"new": [], "updated": [], "skipped": []}

  for filename in os.listdir(DOCS_FOLDER):
    path = os.path.join(DOCS_FOLDER, filename)

    if not os.path.isfile(path):
      continue

    if filename.endswith(".pdf"):
      text = extract_text_from_pdf(path)
    elif filename.endswith(".txt") or filename.endswith(".md"):
      text = extract_text_from_txt(path)
    elif filename.endswith(".docx"):
      text = extract_text_from_docx(path)
    else:
      summary["skipped"].append(filename)
      continue

    already_exists = is_already_ingested(filename)

    chunks = chunk_text(text)
    embeddings = model.encode(chunks).tolist()

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
      collection.upsert(
          documents=[chunk],
          embeddings=[embedding],
          ids=[f"{filename}_chunk_{i}"],
          metadatas=[{"source": filename}]
      )

    if already_exists:
      summary["updated"].append(filename)
    else:
      summary["new"].append(filename)

  return summary


if __name__ == "__main__":
  ingest_documents()
  print("Done! All documents ingested.")
