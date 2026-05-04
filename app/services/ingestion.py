"""
Document ingestion pipeline:
  1. Accept uploaded file (PDF / TXT / DOCX)
  2. Extract raw text
  3. Clean and preprocess text
  4. Split into semantic chunks
"""
import re
import uuid
import logging
from pathlib import Path
from typing import Union

from app.config import settings

logger = logging.getLogger(__name__)


# ── Text Extraction ───────────────────────────────────────────────────────────

def extract_text_from_pdf(path: Path) -> str:
    """Extract text from a PDF file using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append(f"[Page {i + 1}]\n{text}")
        return "\n\n".join(pages)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise RuntimeError(f"Could not extract text from PDF: {e}")


def extract_text_from_txt(path: Path) -> str:
    """Read plain text file."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"Could not read text file: {e}")


def extract_text_from_docx(path: Path) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        raise RuntimeError(f"Could not extract text from DOCX: {e}")


def extract_text(path: Path) -> str:
    """Dispatch to the right extractor based on file extension."""
    ext = path.suffix.lower().lstrip(".")
    extractors = {
        "pdf": extract_text_from_pdf,
        "txt": extract_text_from_txt,
        "docx": extract_text_from_docx,
    }
    if ext not in extractors:
        raise ValueError(f"Unsupported file type: .{ext}")
    return extractors[ext](path)


# ── Text Preprocessing ────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Clean raw extracted text:
    - Normalize whitespace
    - Remove null bytes and control characters
    - Collapse excessive blank lines
    """
    # Remove null bytes
    text = text.replace("\x00", "")
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove non-printable control characters (except newline/tab)
    text = re.sub(r"[^\S\n\t ]+", " ", text)
    # Collapse 3+ blank lines → 2 blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    # Remove lines that are pure noise (e.g., just dots or dashes)
    lines = [l for l in lines if not re.match(r"^[.\-_=*]{3,}$", l)]
    return "\n".join(lines).strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

def split_into_chunks(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> list[str]:
    """
    Split text into overlapping chunks while trying to respect
    paragraph/sentence boundaries.
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    # Try to use LangChain's RecursiveCharacterTextSplitter for quality splits
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_text(text)
        return [c.strip() for c in chunks if len(c.strip()) > 50]
    except ImportError:
        # Fallback: simple character-based splitting
        return _simple_split(text, chunk_size, chunk_overlap)


def _simple_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 50]


# ── Full Pipeline ─────────────────────────────────────────────────────────────

def ingest_document(file_path: Union[str, Path]) -> tuple[str, list[str]]:
    """
    Full ingestion pipeline.
    Returns: (document_id, list_of_chunks)
    """
    path = Path(file_path)
    logger.info(f"Ingesting document: {path.name}")

    # Step 1: Extract
    raw_text = extract_text(path)
    logger.info(f"Extracted {len(raw_text)} characters from {path.name}")

    # Step 2: Clean
    cleaned = clean_text(raw_text)

    # Step 3: Chunk
    chunks = split_into_chunks(cleaned)
    logger.info(f"Created {len(chunks)} chunks from {path.name}")

    # Generate unique document ID
    doc_id = str(uuid.uuid4())[:8]

    return doc_id, chunks
