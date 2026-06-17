import os
from dotenv import load_dotenv
from google import genai
from query import query

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in chunks
    )
    return (
        "You are a helpful study assistant. Answer the question below using only "
        "the provided context. If the context does not contain enough information "
        "to answer, say so.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )


def ask(question: str) -> str:
    chunks = query(question)
    prompt = build_prompt(question, chunks)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text


if __name__ == "__main__":
    print("Run from the project root with: python main.py")
