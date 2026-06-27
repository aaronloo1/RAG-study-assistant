import sys
import os
import html as html_lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Must run before ingest is imported — ingest initialises ChromaDB at module level
# and needs the chroma_db/ folder already populated from GCS.
from storage import bootstrap_from_gcs  # noqa
bootstrap_from_gcs()

import streamlit as st  # noqa
from ingest import ingest_documents, delete_document, DOCS_FOLDER  # noqa
from chat import (  # noqa
    ask_with_sources, summarize_document,
    list_sessions, load_session, save_session, delete_session,
)
from quiz import generate_quiz  # noqa


st.set_page_config(page_title="RAG Study Assistant", page_icon="💡")

# Persist dark-mode and session choice across reruns.
st.session_state.setdefault("dark_mode", False)
st.session_state.setdefault("current_session", None)

# Base styling — applies in both light and dark.
base_css = """
  h1 { font-size: 1.8rem !important; margin-bottom: 0.2rem !important; }
  .sidebar .sidebar-content { padding-top: 1rem; }
  section[data-testid="stSidebar"] .stButton > button { width: 100%; }
  [data-testid="stChatInput"] textarea { border-radius: 10px; }

  /* User message — right-aligned bubble */
  .user-bubble {
    background-color: #6366f1;
    color: white;
    padding: 0.75rem 1.25rem;
    border-radius: 18px 18px 4px 18px;
    max-width: 70%;
    margin-left: auto;
    margin-bottom: 1rem;
    line-height: 1.6;
    word-wrap: break-word;
  }

  /* Assistant message — full width, no cramped column */
  [data-testid="stChatMessage"] {
    border-radius: 12px;
    margin-bottom: 0.75rem;
    max-width: 100% !important;
  }
"""

# Dark overrides — only injected when the toggle is on.
dark_css = """
  .stApp { background-color: #1a1a2e; }
  .stApp, .stApp p, .stApp span, .stApp label, .stApp li,
  h1, h2, h3, h4, h5, [data-testid="stMarkdownContainer"] { color: #e8e8e8 !important; }
  section[data-testid="stSidebar"] { background-color: #16213e; }
  [data-testid="stChatMessage"] { background-color: #16213e; }
  [data-testid="stChatInput"] textarea { background-color: #16213e; color: #e8e8e8; }
  [data-testid="stAlert"] * { color: #1a1a2e !important; }
"""

css = base_css + (dark_css if st.session_state.dark_mode else "")
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.title("✦ RAG Study Assistant")

# --- Sidebar ---
with st.sidebar:
  # --- Upload ---
  st.header("Upload Documents")
  uploaded_files = st.file_uploader(
      "Upload PDFs or text files",
      type=["pdf", "txt", "md", "docx"],
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

  # --- Documents in Database ---
  st.subheader("Documents in Database")
  if os.path.exists(DOCS_FOLDER):
    existing_files = [f for f in os.listdir(DOCS_FOLDER) if os.path.isfile(os.path.join(DOCS_FOLDER, f))]
    if existing_files:
      for f in existing_files:
        st.write(f"- {f}")
        col1, col2 = st.columns(2)
        with col1:
          if st.button("Summarize", key=f"sum_{f}"):
            with st.spinner("Summarizing..."):
              summary_text = summarize_document(f)
            st.session_state.summary = {"filename": f, "content": summary_text}
            st.rerun()
        with col2:
          if st.button("Delete", key=f"del_{f}"):
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

  # --- Chat Sessions ---
  st.subheader("Chat Sessions")

  sessions = list_sessions()
  if sessions:
    # Show a dropdown of existing sessions. When the user picks a different one,
    # load its messages and switch the active session.
    current_idx = 0
    if st.session_state.current_session in sessions:
      current_idx = sessions.index(st.session_state.current_session) + 1
    selected = st.selectbox(
        "Switch session",
        ["— select a session —"] + sessions,
        index=current_idx,
    )
    if selected != "— select a session —" and selected != st.session_state.current_session:
      st.session_state.current_session = selected
      st.session_state.messages = load_session(selected)
      st.rerun()

  # Create a new named session.
  new_name = st.text_input("New session name", placeholder="e.g. Biology exam")
  if st.button("Create Session") and new_name.strip():
    name = new_name.strip()
    save_session(name, [])
    st.session_state.current_session = name
    st.session_state.messages = []
    st.rerun()

  if st.session_state.current_session:
    st.caption(f"Active: **{st.session_state.current_session}**")
    if st.button("Delete Session"):
      delete_session(st.session_state.current_session)
      st.session_state.current_session = None
      st.session_state.messages = []
      st.rerun()

  st.divider()

  # --- Quiz Generator ---
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

  st.divider()

  # --- Utility ---
  st.toggle("🌙 Dark mode", key="dark_mode")

  if st.button("Clear Chat"):
    st.session_state.messages = []
    if st.session_state.current_session:
      save_session(st.session_state.current_session, [])
    st.rerun()

# --- Summary panel ---
if st.session_state.get("summary"):
  with st.expander(f"Summary: {st.session_state.summary['filename']}", expanded=True):
    st.markdown(st.session_state.summary["content"])
    if st.button("Close Summary"):
      del st.session_state.summary
      st.rerun()

# --- Tabs ---
tab_chat, tab_quiz = st.tabs(["💬 Chat", "📝 Quiz"])

# --- Chat tab ---
with tab_chat:
  if "messages" not in st.session_state:
    st.session_state.messages = []

  for message in st.session_state.messages:
    if message["role"] == "user":
      st.markdown(
          f'<div class="user-bubble">{html_lib.escape(message["content"])}</div>',
          unsafe_allow_html=True,
      )
    else:
      with st.chat_message("assistant"):
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
    st.markdown(
        f'<div class="user-bubble">{html_lib.escape(question)}</div>',
        unsafe_allow_html=True,
    )

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
  # Only persist if the user has an active named session.
  if st.session_state.current_session:
    save_session(st.session_state.current_session, st.session_state.messages)
