import os
import re
import json
import time
from dotenv import load_dotenv
from google import genai
from query import query, get_chunks_for_document
from storage import sync_up, delete_blob

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


def summarize_document(filename: str) -> str:
  chunks = get_chunks_for_document(filename)
  if not chunks:
    return "No content found for this document. Make sure it has been ingested."
  context = "\n\n".join(c["text"] for c in chunks)
  prompt = (
      f"Summarize the following document called '{filename}' in 3-5 clear bullet points. "
      f"Focus on the key concepts and main ideas a student would need to know.\n\n{context}"
  )
  return _generate_with_retry(prompt)


SESSIONS_FOLDER = "chat_sessions"


def _safe_filename(name: str) -> str:
  # Strip characters that are invalid in Windows/Mac/Linux filenames.
  return re.sub(r'[<>:"/\\|?*]', '', name).strip()


def list_sessions() -> list[str]:
  if not os.path.exists(SESSIONS_FOLDER):
    return []
  return sorted(f[:-5] for f in os.listdir(SESSIONS_FOLDER) if f.endswith(".json"))


def load_session(name: str) -> list[dict]:
  path = os.path.join(SESSIONS_FOLDER, f"{_safe_filename(name)}.json")
  if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
      return json.load(f)
  return []


def save_session(name: str, messages: list[dict]):
  os.makedirs(SESSIONS_FOLDER, exist_ok=True)
  safe = _safe_filename(name)
  path = os.path.join(SESSIONS_FOLDER, f"{safe}.json")
  with open(path, "w", encoding="utf-8") as f:
    json.dump(messages, f, ensure_ascii=False, indent=2)
  sync_up(SESSIONS_FOLDER, "chat_sessions")


def delete_session(name: str):
  safe = _safe_filename(name)
  path = os.path.join(SESSIONS_FOLDER, f"{safe}.json")
  if os.path.exists(path):
    os.remove(path)
  delete_blob(f"chat_sessions/{safe}.json")


if __name__ == "__main__":
  print("Run from the project root with: python main.py")
