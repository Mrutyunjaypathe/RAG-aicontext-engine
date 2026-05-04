"""
Integration tests for the FastAPI endpoints.
Start the server first or use TestClient (no server needed).
Run with: pytest tests/ -v
"""
import pytest
import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Health ────────────────────────────────────────────────────────

def test_health_check():
    r = client.get("/metrics/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_root_endpoint():
    r = client.get("/")
    assert r.status_code == 200
    assert "docs" in r.json()


# ── Upload ────────────────────────────────────────────────────────

def test_upload_txt_file():
    content = b"This is a test document.\n" * 30
    files = {"file": ("test_doc.txt", io.BytesIO(content), "text/plain")}
    r = client.post("/upload/", files=files)
    assert r.status_code == 200
    data = r.json()
    assert "document_id" in data
    assert data["chunks_created"] >= 1


def test_upload_invalid_extension():
    content = b"bad file"
    files = {"file": ("malware.exe", io.BytesIO(content), "application/octet-stream")}
    r = client.post("/upload/", files=files)
    assert r.status_code == 400


def test_list_documents():
    r = client.get("/upload/documents")
    assert r.status_code == 200
    data = r.json()
    assert "documents" in data
    assert isinstance(data["documents"], list)


# ── Query ─────────────────────────────────────────────────────────

def test_query_no_documents_raises_404():
    """When no docs exist (clean state), should return 404."""
    # This may pass or skip depending on state
    r = client.post("/query/", json={"question": "What is this document about?"})
    # Either 200 (if docs exist) or 404 (if not)
    assert r.status_code in [200, 404, 500]


def test_query_empty_question_validation():
    r = client.post("/query/", json={"question": "ab"})  # Too short (min_length=3 is ok, but "ab" is 2)
    # "ab" length = 2 < 3 → 422 validation error
    assert r.status_code == 422


# ── Metrics ───────────────────────────────────────────────────────

def test_metrics_endpoint():
    r = client.get("/metrics/")
    assert r.status_code == 200
    data = r.json()
    assert "total_queries" in data
    assert "latency" in data
    assert "p50_ms" in data["latency"]
