FROM python:3.12-slim

WORKDIR /app

# System libraries required by PyMuPDF (fitz) and python-docx (lxml)
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies as a separate layer so Docker can cache them.
# Only re-runs this expensive step when requirements.txt actually changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers embedding model and bake it into the
# image. Without this, every cold start would download ~90MB from HuggingFace,
# adding 30+ seconds to startup time.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application source
COPY . .

EXPOSE 8501

# headless=true  — disables the browser-open prompt and analytics nag
# fileWatcherType=none — no need to watch for file changes in production
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.fileWatcherType=none"]
