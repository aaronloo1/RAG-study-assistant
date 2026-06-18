import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st
from chat import ask
from ingest import ingest_documents, DOCS_FOLDER

st.set_page_config(page_title="RAG Study Assistant", page_icon="📚")
st.title("📚 RAG Study Assistant")

# --- Sidebar: upload documents ---
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
                ingest_documents()
            st.success(f"Ingested {len(uploaded_files)} file(s)")

# --- Chat history ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Input ---
if question := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = ask(question)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
