import os
import warnings
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
warnings.filterwarnings("ignore", category=UserWarning)

import chromadb
from sentence_transformers import SentenceTransformer

DB_FOLDER = "chroma_db"
TOP_K = 5

_client = None
_collection = None
_model = None


def _get_resources():
    global _client, _collection, _model
    if _model is None:
        _client = chromadb.PersistentClient(path=DB_FOLDER)
        _collection = _client.get_or_create_collection(name="study_docs")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _collection, _model


def query(question: str) -> list[dict]:
    collection, model = _get_resources()
    embedding = model.encode([question]).tolist()
    results = collection.query(
        query_embeddings=embedding,
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"]
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "text": doc,
            "source": meta["source"],
            "score": round(1 - dist, 4)
        })
    return chunks


if __name__ == "__main__":
    question = input("Enter your question: ")
    results = query(question)
    for i, chunk in enumerate(results, 1):
        print(f"\n--- Result {i} (score: {chunk['score']}) | source: {chunk['source']} ---")
        print(chunk["text"])
