import os
import time
from dotenv import load_dotenv
from google import genai
from query import query

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-2.0-flash"
_MAX_RETRIES = 5
_RETRY_DELAY = 5  # seconds between retries


def _is_retryable(e: Exception) -> bool:
  msg = str(e).lower()
  return "high demand" in msg or "429" in str(e) or "quota" in msg


def _generate_with_retry(prompt: str) -> str:
  for attempt in range(_MAX_RETRIES):
    try:
      response = client.models.generate_content(model=MODEL, contents=prompt)
      return response.text
    except Exception as e:
      if _is_retryable(e) and attempt < _MAX_RETRIES - 1:
        time.sleep(_RETRY_DELAY * (attempt + 1))
      else:
        raise


def _generate_stream(prompt: str):
  for attempt in range(_MAX_RETRIES):
    try:
      for chunk in client.models.generate_content_stream(model=MODEL, contents=prompt):
        if chunk.text:
          yield chunk.text
      return
    except Exception as e:
      if _is_retryable(e) and attempt < _MAX_RETRIES - 1:
        time.sleep(_RETRY_DELAY * (attempt + 1))
      else:
        raise


def build_prompt(question: str, chunks: list[dict], history: list[dict]) -> str:
  if chunks:
    context_block = "CONTEXT FROM YOUR DOCUMENTS:\n" + "\n\n".join(
        f"[Source: {c['source']} | relevance: {c['score']}]\n{c['text']}" for c in chunks
    )
  else:
    context_block = "CONTEXT FROM YOUR DOCUMENTS:\nNo relevant passages found in the uploaded documents."

  history_text = ""
  if history:
    lines = []
    for msg in history[-6:]:
      role = "User" if msg["role"] == "user" else "Assistant"
      lines.append(f"{role}: {msg['content']}")
    history_text = "CONVERSATION HISTORY:\n" + "\n".join(lines) + "\n\n"

  return (
      "You are a knowledgeable study assistant helping a student understand their own study material.\n\n"

      "CITATIONS:\n"
      "Each context block is labeled with its source file. When your answer draws from a source, "
      "cite it inline like this: 'The mitochondria produces ATP [notes.pdf].' "
      "If multiple sources support a point, cite all of them. "
      "If a part of your answer comes from your own general knowledge rather than the context, "
      "prefix that part with 'Based on general knowledge:' so the student knows.\n\n"

      "CONFIDENCE:\n"
      "If the context fully covers the question, answer confidently from it. "
      "If the context only partially covers it, say so explicitly — for example: "
      "'The context covers X but not Y. For Y, based on general knowledge...' "
      "Never silently blend document content with outside knowledge.\n\n"

      "FORMATTING:\n"
      "- **Bold** key terms and concepts the first time you introduce them.\n"
      "- Use ## headers when your answer has multiple distinct sections.\n"
      "- Use numbered lists for steps or sequences; bullet points for non-ordered items.\n"
      "- Put each multiple choice option (A, B, C, D) on its own line.\n"
      "- When introducing an unfamiliar concept, include a one-sentence analogy or real-world example.\n"
      "- Show your reasoning step by step when solving problems.\n\n"

      f"{context_block}\n\n"
      f"{history_text}"
      f"Question: {question}\n\n"
      "Answer:"
  )


def ask(question: str, history: list[dict] | None = None) -> str:
  chunks = query(question)
  prompt = build_prompt(question, chunks, history or [])
  return _generate_with_retry(prompt)


def ask_with_sources(question: str, history: list[dict] | None = None) -> dict:
  chunks = query(question)
  prompt = build_prompt(question, chunks, history or [])
  return {"answer_stream": _generate_stream(prompt), "sources": chunks}


if __name__ == "__main__":
  print("Run from the project root with: python main.py")
