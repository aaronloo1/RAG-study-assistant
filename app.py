import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st  # noqa
from ingest import ingest_documents, delete_document, DOCS_FOLDER  # noqa
from chat import ask_with_sources  # noqa
from quiz import generate_quiz  # noqa


st.set_page_config(page_title="RAG Study Assistant", page_icon="📚")
st.title("📚 RAG Study Assistant")

# --- Sidebar ---
with st.sidebar:
  st.header("Upload Documents")
  uploaded_files = st.file_uploader(
      "Upload PDFs or text files",
      type=["pdf", "txt", "md"],
      accept_multiple_files=True
  )

  if uploaded_files:
    os.makedirs(DOCS_FOLDER, exist_ok=True)
    for file in uploaded_files:
      dest = os.path.join(DOCS_FOLDER, file.name)
      with open(dest, "wb") as f:
        f.write(file.getbuffer())

    if st.button("Ingest Documents"):
      with st.spinner("Ingesting..."):
        summary = ingest_documents()
      if summary["new"]:
        st.success(f"Added: {', '.join(summary['new'])}")
      if summary["updated"]:
        st.info(f"Re-ingested: {', '.join(summary['updated'])}")
      if summary["skipped"]:
        st.warning(f"Skipped (unsupported): {', '.join(summary['skipped'])}")

  st.divider()
  if st.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()

  st.divider()
  st.subheader("Documents in Database")
  if os.path.exists(DOCS_FOLDER):
    existing_files = [f for f in os.listdir(DOCS_FOLDER) if os.path.isfile(os.path.join(DOCS_FOLDER, f))]
    if existing_files:
      for f in existing_files:
        col1, col2 = st.columns([4, 1])
        with col1:
          st.write(f"- {f}")
        with col2:
          if st.button("Del", key=f"del_{f}"):
            delete_document(f)
            file_path = os.path.join(DOCS_FOLDER, f)
            if os.path.exists(file_path):
              os.remove(file_path)
            st.rerun()
    else:
      st.caption("No documents uploaded yet.")
  else:
    st.caption("No documents uploaded yet.")

  st.divider()
  st.subheader("Quiz Generator")
  quiz_topic = st.text_input("Topic (optional)", placeholder="e.g. photosynthesis")
  n_questions = st.slider("Number of questions", min_value=3, max_value=10, value=5)
  if st.button("Generate Quiz"):
    with st.spinner("Generating quiz..."):
      quiz = generate_quiz(quiz_topic.strip() or None, n_questions)
    if quiz:
      st.session_state.quiz = quiz
      st.session_state.quiz_reveals = {}
      st.rerun()
    else:
      st.error("Could not generate quiz. Make sure documents are ingested.")

# --- Tabs ---
tab_chat, tab_quiz = st.tabs(["💬 Chat", "📝 Quiz"])

# --- Chat tab ---
with tab_chat:
  if "messages" not in st.session_state:
    st.session_state.messages = []

  for message in st.session_state.messages:
    with st.chat_message(message["role"]):
      st.markdown(message["content"])

# --- Quiz tab ---
with tab_quiz:
  if not st.session_state.get("quiz"):
    st.info("Use the **Quiz Generator** in the sidebar to create a quiz from your documents.")
  else:
    quiz = st.session_state.quiz
    col1, col2 = st.columns([6, 1])
    with col1:
      st.markdown(f"### Quiz — {len(quiz)} questions")
    with col2:
      if st.button("Clear"):
        del st.session_state.quiz
        st.session_state.quiz_reveals = {}
        st.rerun()

    for i, q in enumerate(quiz):
      st.markdown(f"**Q{i + 1}. {q['question']}**")
      for letter, option in q["options"].items():
        st.write(f"{letter}) {option}")

      reveal_key = f"reveal_{i}"
      if not st.session_state.quiz_reveals.get(reveal_key):
        if st.button("Reveal Answer", key=f"btn_{i}"):
          st.session_state.quiz_reveals[reveal_key] = True
          st.rerun()
      else:
        st.success(f"**Answer: {q['answer']}**")
        if q.get("explanation"):
          st.info(q["explanation"])

      st.divider()

# --- Chat input (always at bottom) ---
if question := st.chat_input("Ask a question about your documents..."):
  if "messages" not in st.session_state:
    st.session_state.messages = []

  st.session_state.messages.append({"role": "user", "content": question})
  with tab_chat:
    with st.chat_message("user"):
      st.markdown(question)

    with st.chat_message("assistant"):
      result = ask_with_sources(question, history=st.session_state.messages[:-1])
      full_answer = st.write_stream(result["answer_stream"])

      seen = set()
      unique_sources = []
      for chunk in result["sources"]:
        if chunk["source"] not in seen:
          seen.add(chunk["source"])
          unique_sources.append(chunk)

      if unique_sources:
        with st.expander(f"Sources ({len(unique_sources)} document(s))"):
          for chunk in unique_sources:
            st.markdown(f"**{chunk['source']}** — relevance: `{chunk['score']}`")
            preview = chunk["text"].strip()[:300].replace("\n", " ")
            st.caption(f"{preview}...")
            st.divider()

  st.session_state.messages.append({"role": "assistant", "content": full_answer})
