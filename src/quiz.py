import json
import os
import time
from dotenv import load_dotenv
from google import genai
from query import query, get_all_chunks

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash"
_MAX_RETRIES = 3
_RETRY_DELAY = 5


def _build_quiz_prompt(chunks: list[dict], n_questions: int, topic: str | None) -> str:
    context = "\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in chunks)
    topic_line = f" focused on: {topic}" if topic else ""
    return (
        f"You are generating a quiz for a student{topic_line}. "
        f"Create exactly {n_questions} multiple-choice questions based only on the context below.\n\n"
        f"Context:\n{context}\n\n"
        "Return ONLY valid JSON — no markdown, no code fences, no explanation. "
        "Use this exact structure:\n"
        '[{"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, '
        '"answer": "A", "explanation": "..."}]'
    )


def _parse_response(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def generate_quiz(topic: str | None, n_questions: int) -> list[dict] | None:
    chunks = query(topic) if topic else get_all_chunks(limit=30)
    if not chunks:
        return None

    prompt = _build_quiz_prompt(chunks, n_questions, topic)

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            return _parse_response(response.text)
        except json.JSONDecodeError:
            if attempt == _MAX_RETRIES - 1:
                return None
        except Exception as e:
            msg = str(e).lower()
            if ("high demand" in msg or "429" in str(e) or "quota" in msg) and attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY * (attempt + 1))
            else:
                return None
    return None
