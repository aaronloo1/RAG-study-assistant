import os
from google.cloud import storage as gcs

BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "")
_bootstrapped = False
_gcs_client = None


def _is_enabled() -> bool:
    return bool(BUCKET_NAME)


def _client():
    global _gcs_client
    if _gcs_client is None:
        _gcs_client = gcs.Client()
    return _gcs_client


def sync_down(gcs_prefix: str, local_dir: str):
    if not _is_enabled():
        return
    try:
        os.makedirs(local_dir, exist_ok=True)
        bucket = _client().bucket(BUCKET_NAME)
        for blob in bucket.list_blobs(prefix=gcs_prefix + "/"):
            rel = blob.name[len(gcs_prefix) + 1:]
            if not rel:
                continue
            local_path = os.path.join(local_dir, rel)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            blob.download_to_filename(local_path)
    except Exception:
        pass


def sync_up(local_dir: str, gcs_prefix: str):
    if not _is_enabled() or not os.path.exists(local_dir):
        return
    try:
        bucket = _client().bucket(BUCKET_NAME)
        for root, _, files in os.walk(local_dir):
            for fname in files:
                local_path = os.path.join(root, fname)
                rel = os.path.relpath(local_path, local_dir).replace("\\", "/")
                bucket.blob(f"{gcs_prefix}/{rel}").upload_from_filename(local_path)
    except Exception:
        pass


def delete_blob(gcs_path: str):
    if not _is_enabled():
        return
    try:
        bucket = _client().bucket(BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        if blob.exists():
            blob.delete()
    except Exception:
        pass


def bootstrap_from_gcs():
    global _bootstrapped
    if _bootstrapped:
        return
    _bootstrapped = True
    sync_down("docs", "docs")
    sync_down("chroma_db", "chroma_db")
    sync_down("chat_sessions", "chat_sessions")
