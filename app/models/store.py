"""
Metadata store — persists document info and query history as JSON.
Thread-safe via a simple lock.
"""
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.config import settings


_STORE_FILE = Path(settings.log_dir) / "metadata_store.json"
_lock = threading.Lock()


def _load() -> dict:
    if _STORE_FILE.exists():
        with open(_STORE_FILE, "r") as f:
            return json.load(f)
    return {"documents": {}, "queries": []}


def _save(data: dict):
    with open(_STORE_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ── Documents ─────────────────────────────────────────────────────────────────

def add_document(doc_id: str, filename: str, chunks: int, size_bytes: int):
    with _lock:
        data = _load()
        data["documents"][doc_id] = {
            "document_id": doc_id,
            "filename": filename,
            "chunks": chunks,
            "uploaded_at": datetime.utcnow().isoformat(),
            "size_bytes": size_bytes,
        }
        _save(data)


def get_document(doc_id: str) -> Optional[dict]:
    data = _load()
    return data["documents"].get(doc_id)


def get_all_documents() -> list[dict]:
    data = _load()
    return list(data["documents"].values())


def remove_document(doc_id: str):
    with _lock:
        data = _load()
        if doc_id in data["documents"]:
            del data["documents"][doc_id]
            _save(data)


# ── Queries ───────────────────────────────────────────────────────────────────

def add_query_log(entry: dict):
    with _lock:
        data = _load()
        data["queries"].append(entry)
        # Keep last 500 queries only
        data["queries"] = data["queries"][-500:]
        _save(data)


def get_recent_queries(n: int = 10) -> list[dict]:
    data = _load()
    return data["queries"][-n:]


def get_all_queries() -> list[dict]:
    data = _load()
    return data["queries"]
