import os
import warnings
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
warnings.filterwarnings("ignore", category=UserWarning)

import chromadb
from sentence_transformers import SentenceTransformer

try:
    import streamlit as st
    _cache = st.cache_resource
except ImportError:
    def _cache(fn):
        return fn

DB_FOLDER = "chroma_db"
TOP_K = 8
MIN_SCORE = 0.2


@_cache
def _get_resources():
    client = chromadb.PersistentClient(path=DB_FOLDER)
    collection = client.get_or_create_collection(name="study_docs")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return collection, model


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
        score = round(1 - dist, 4)
        if score >= MIN_SCORE:
            chunks.append({"text": doc, "source": meta["source"], "score": score})
    return chunks


def get_all_chunks(limit: int = 30) -> list[dict]:
    collection, _ = _get_resources()
    results = collection.get(limit=limit, include=["documents", "metadatas"])
    return [
        {"text": doc, "source": meta["source"]}
        for doc, meta in zip(results["documents"], results["metadatas"])
    ]


if __name__ == "__main__":
    question = input("Enter your question: ")
    results = query(question)
    for i, chunk in enumerate(results, 1):
        print(f"\n--- Result {i} (score: {chunk['score']}) | source: {chunk['source']} ---")
        print(chunk["text"])
