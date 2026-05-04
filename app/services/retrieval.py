"""
FAISS vector store service.
- Maintains one FAISS index per document (allows targeted retrieval)
- Also maintains a global merged index for cross-document search
- Persists indexes to disk for restarts
"""
import json
import logging
import pickle
from pathlib import Path
from typing import List, Optional

import numpy as np

from app.config import settings
from app.services.embeddings import embed_texts, embed_query

logger = logging.getLogger(__name__)

_VECTOR_DIR = Path(settings.vector_dir)
_META_FILE = _VECTOR_DIR / "chunk_metadata.json"

# In-memory store: doc_id → {"index": faiss.Index, "chunks": [...]}
_indexes: dict = {}
_chunk_meta: dict = {}  # chunk_id → {doc_id, filename, chunk_index, content}


# ── Persistence ───────────────────────────────────────────────────────────────

def _index_path(doc_id: str) -> Path:
    return _VECTOR_DIR / f"{doc_id}.faiss"


def _save_index(doc_id: str):
    import faiss
    idx = _indexes[doc_id]["index"]
    faiss.write_index(idx, str(_index_path(doc_id)))
    # Save chunk texts alongside
    chunks_path = _VECTOR_DIR / f"{doc_id}_chunks.pkl"
    with open(chunks_path, "wb") as f:
        pickle.dump(_indexes[doc_id]["chunks"], f)


def _load_index(doc_id: str):
    import faiss
    path = _index_path(doc_id)
    if not path.exists():
        return False
    idx = faiss.read_index(str(path))
    chunks_path = _VECTOR_DIR / f"{doc_id}_chunks.pkl"
    chunks = []
    if chunks_path.exists():
        with open(chunks_path, "rb") as f:
            chunks = pickle.load(f)
    _indexes[doc_id] = {"index": idx, "chunks": chunks}
    logger.info(f"Loaded FAISS index for doc {doc_id} ({idx.ntotal} vectors)")
    return True


def _save_meta():
    _META_FILE.write_text(json.dumps(_chunk_meta, indent=2))


def _load_meta():
    global _chunk_meta
    if _META_FILE.exists():
        _chunk_meta = json.loads(_META_FILE.read_text())


# ── Index Building ────────────────────────────────────────────────────────────

def build_index(doc_id: str, filename: str, chunks: List[str]):
    """
    Embed chunks and build a FAISS Flat L2 index for a document.
    Persists index to disk.
    """
    import faiss

    logger.info(f"Building FAISS index for '{filename}' ({len(chunks)} chunks)")

    # Generate embeddings
    embeddings = embed_texts(chunks)
    dim = len(embeddings[0])

    # Build FAISS index (FlatL2 = exact search, good for < 100k chunks)
    index = faiss.IndexFlatIP(dim)  # Inner product ≈ cosine sim (with normalized vecs)

    vectors = np.array(embeddings, dtype=np.float32)
    # L2 normalize for cosine similarity
    faiss.normalize_L2(vectors)
    index.add(vectors)

    _indexes[doc_id] = {"index": index, "chunks": chunks}

    # Store chunk metadata
    _load_meta()
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}_{i}"
        _chunk_meta[chunk_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "chunk_index": i,
            "content": chunk,
        }

    _save_index(doc_id)
    _save_meta()
    logger.info(f"Index built and saved for doc {doc_id}")


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    top_k: int = None,
    doc_id: Optional[str] = None,
) -> List[dict]:
    """
    Retrieve top-k most relevant chunks for a query.
    If doc_id is given, search only that document's index.
    Otherwise, search all loaded indexes and merge results.
    """
    import faiss

    top_k = top_k or settings.top_k_results
    _load_meta()

    # Embed the query
    q_vec = np.array([embed_query(query)], dtype=np.float32)
    faiss.normalize_L2(q_vec)

    # Determine which indexes to search
    if doc_id:
        if doc_id not in _indexes:
            _load_index(doc_id)
        search_docs = [doc_id] if doc_id in _indexes else []
    else:
        # Load all persisted indexes
        for p in _VECTOR_DIR.glob("*.faiss"):
            did = p.stem
            if did not in _indexes:
                _load_index(did)
        search_docs = list(_indexes.keys())

    if not search_docs:
        logger.warning("No FAISS indexes available for retrieval")
        return []

    all_results = []
    for did in search_docs:
        idx_data = _indexes[did]
        index = idx_data["index"]
        chunks = idx_data["chunks"]

        k = min(top_k, index.ntotal)
        scores, indices = index.search(q_vec, k)

        for score, chunk_idx in zip(scores[0], indices[0]):
            if chunk_idx < 0:
                continue
            chunk_id = f"{did}_{chunk_idx}"
            meta = _chunk_meta.get(chunk_id, {})
            all_results.append({
                "document_id": did,
                "filename": meta.get("filename", "unknown"),
                "chunk_index": int(chunk_idx),
                "content": chunks[chunk_idx] if chunk_idx < len(chunks) else "",
                "relevance_score": float(score),
            })

    # Sort by relevance score descending, return top_k
    all_results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return all_results[:top_k]


def get_index_stats() -> dict:
    """Return stats about all loaded indexes."""
    stats = {}
    for p in _VECTOR_DIR.glob("*.faiss"):
        did = p.stem
        if did not in _indexes:
            _load_index(did)
        if did in _indexes:
            stats[did] = _indexes[did]["index"].ntotal
    return stats
