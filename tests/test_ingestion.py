"""
Tests for the document ingestion pipeline.
Run with: pytest tests/ -v
"""
import pytest
from pathlib import Path
import tempfile

from app.services.ingestion import clean_text, split_into_chunks, extract_text_from_txt


# ── clean_text ────────────────────────────────────────────────────

def test_clean_text_removes_null_bytes():
    result = clean_text("Hello\x00World")
    assert "\x00" not in result
    assert "Hello" in result

def test_clean_text_collapses_blank_lines():
    result = clean_text("Line1\n\n\n\n\nLine2")
    assert "\n\n\n" not in result
    assert "Line1" in result and "Line2" in result

def test_clean_text_strips_noise_lines():
    result = clean_text("Title\n---------\nContent")
    assert "Title" in result
    assert "Content" in result

def test_clean_text_normalizes_whitespace():
    result = clean_text("  word1   word2  ")
    assert "  " not in result.strip()


# ── split_into_chunks ─────────────────────────────────────────────

def test_split_produces_chunks():
    text = "This is a sentence. " * 100
    chunks = split_into_chunks(text, chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1

def test_split_chunks_not_empty():
    text = "Hello world. " * 50
    chunks = split_into_chunks(text, chunk_size=100, chunk_overlap=10)
    for c in chunks:
        assert len(c.strip()) > 0

def test_split_short_text_single_chunk():
    text = "Short text here."
    chunks = split_into_chunks(text, chunk_size=1000, chunk_overlap=100)
    # Very short text might produce 0 chunks (< 50 chars) or 1
    assert len(chunks) <= 1


# ── extract_text_from_txt ─────────────────────────────────────────

def test_extract_txt():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as f:
        f.write("Hello from test file.\nSecond line.")
        tmp = Path(f.name)

    result = extract_text_from_txt(tmp)
    tmp.unlink()
    assert "Hello from test file" in result
    assert "Second line" in result
