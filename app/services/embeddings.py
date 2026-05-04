"""
Embedding generation service.
Uses Google Generative AI embeddings (free tier).
Includes a simple in-memory + disk cache to avoid redundant API calls.
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)

# ── Cache ─────────────────────────────────────────────────────────────────────

_CACHE_FILE = Path(settings.vector_dir) / "embedding_cache.json"
_cache: dict = {}


def _load_cache():
    global _cache
    if _CACHE_FILE.exists():
        try:
            _cache = json.loads(_CACHE_FILE.read_text())
        except Exception:
            _cache = {}


def _save_cache():
    _CACHE_FILE.write_text(json.dumps(_cache))


def _cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


# ── Embedder ──────────────────────────────────────────────────────────────────

_embedder = None


def _get_embedder():
    """Lazy-initialize the embedding client."""
    global _embedder
    if _embedder is not None:
        return _embedder

    if settings.llm_provider == "gemini":
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            _embedder = GoogleGenerativeAIEmbeddings(
                model=settings.embedding_model,
                google_api_key=settings.gemini_api_key,
            )
            logger.info("Initialized Google Generative AI embeddings")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini embeddings: {e}")
            raise
    else:
        try:
            from langchain_community.embeddings import OpenAIEmbeddings
            _embedder = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
            logger.info("Initialized OpenAI embeddings")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embeddings: {e}")
            raise

    return _embedder


# ── Public API ────────────────────────────────────────────────────────────────

def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    Results are cached to minimize API calls.
    """
    _load_cache()
    embedder = _get_embedder()

    results: List[List[float] | None] = [None] * len(texts)
    uncached_indices = []
    uncached_texts = []

    # Check cache first
    for i, text in enumerate(texts):
        key = _cache_key(text)
        if key in _cache:
            results[i] = _cache[key]
        else:
            uncached_indices.append(i)
            uncached_texts.append(text)

        # Embed uncached texts
        if uncached_texts:
            logger.info(f"Embedding {len(uncached_texts)} new text chunks...")
            all_embeddings = []
            
            if settings.llm_provider == "gemini":
                # Workaround for langchain-google-genai 4.2.2 bug where embed_documents treats 
                # a list of strings as a single document's multi-part content.
                import time
                for i, text in enumerate(uncached_texts):
                    all_embeddings.append(embedder.embed_query(text))
                    if i < len(uncached_texts) - 1:
                        time.sleep(2)  # Avoid 15 RPM rate limit on free tier
            else:
                batch_size = 100
                for start in range(0, len(uncached_texts), batch_size):
                    batch = uncached_texts[start : start + batch_size]
                    all_embeddings.extend(embedder.embed_documents(batch))

            # Store in cache and results
            for idx, embedding in zip(uncached_indices, all_embeddings):
                key = _cache_key(texts[idx])
                _cache[key] = embedding
                results[idx] = embedding

        _save_cache()
        logger.info(f"Cached {len(uncached_texts)} new embeddings")

    return results  # type: ignore


def embed_query(query: str) -> List[float]:
    """Embed a single query string (uses query-optimized embedding)."""
    _load_cache()
    key = _cache_key(f"query::{query}")
    if key in _cache:
        return _cache[key]

    embedder = _get_embedder()
    embedding = embedder.embed_query(query)
    _cache[key] = embedding
    _save_cache()
    return embedding
