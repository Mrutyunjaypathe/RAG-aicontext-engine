"""
Observability service — structured logging, latency tracking,
cost monitoring, and query evaluation storage.
"""
import json
import logging
import time
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_LOG_DIR = Path(settings.log_dir)
_METRICS_FILE = _LOG_DIR / "metrics.json"
_QUERY_LOG_FILE = _LOG_DIR / "query_log.jsonl"

# In-memory metrics buffer
_latencies: list[float] = []
_total_tokens: int = 0
_total_cost: float = 0.0
_start_time: float = time.time()


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_logging():
    """Configure structured logging with rich formatting."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler for persistent logs
    log_file = _LOG_DIR / "app.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    logging.getLogger().addHandler(file_handler)
    logger.info("Logging initialized")


# ── Query Logging ─────────────────────────────────────────────────────────────

def log_query(
    question: str,
    answer: str,
    sources: list[dict],
    latency_ms: float,
    tokens_used: int = 0,
    estimated_cost_usd: float = 0.0,
):
    """Log a query event to JSONL file and update in-memory metrics."""
    global _total_tokens, _total_cost

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "question": question,
        "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
        "num_sources": len(sources),
        "source_docs": [s.get("filename", "?") for s in sources],
        "latency_ms": round(latency_ms, 2),
        "tokens_used": tokens_used,
        "estimated_cost_usd": round(estimated_cost_usd, 6),
    }

    # Append to JSONL
    with open(_QUERY_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # Update in-memory stats
    _latencies.append(latency_ms)
    _total_tokens += tokens_used
    _total_cost += estimated_cost_usd

    # Keep memory bounded
    if len(_latencies) > 10_000:
        _latencies.pop(0)

    logger.info(
        f"QUERY | latency={latency_ms:.1f}ms | tokens={tokens_used} | "
        f"sources={len(sources)} | q='{question[:60]}...'"
    )


# ── Latency Stats ─────────────────────────────────────────────────────────────

def _load_latencies_from_log() -> list[float]:
    """Load all latencies from JSONL log (for persistence across restarts)."""
    lats = []
    if _QUERY_LOG_FILE.exists():
        for line in _QUERY_LOG_FILE.read_text().splitlines():
            try:
                entry = json.loads(line)
                lats.append(entry["latency_ms"])
            except Exception:
                pass
    return lats


def get_latency_stats() -> dict:
    """Compute p50, p95, p99 latency statistics."""
    lats = _latencies or _load_latencies_from_log()
    if not lats:
        return {"p50_ms": 0, "p95_ms": 0, "p99_ms": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0}

    sorted_lats = sorted(lats)
    n = len(sorted_lats)

    def percentile(p: float) -> float:
        idx = int(n * p / 100)
        return sorted_lats[min(idx, n - 1)]

    return {
        "p50_ms": round(percentile(50), 2),
        "p95_ms": round(percentile(95), 2),
        "p99_ms": round(percentile(99), 2),
        "avg_ms": round(statistics.mean(lats), 2),
        "min_ms": round(min(lats), 2),
        "max_ms": round(max(lats), 2),
    }


# ── Aggregate Metrics ─────────────────────────────────────────────────────────

def get_metrics() -> dict:
    """Return full observability metrics snapshot."""
    from app.models.store import get_all_documents, get_recent_queries
    from app.services.retrieval import get_index_stats

    docs = get_all_documents()
    index_stats = get_index_stats()
    total_chunks = sum(index_stats.values())

    # Load totals from log if in-memory is empty (post-restart)
    total_tokens = _total_tokens
    total_cost = _total_cost
    if total_tokens == 0 and _QUERY_LOG_FILE.exists():
        for line in _QUERY_LOG_FILE.read_text().splitlines():
            try:
                e = json.loads(line)
                total_tokens += e.get("tokens_used", 0)
                total_cost += e.get("estimated_cost_usd", 0)
            except Exception:
                pass

    # Recent queries for the dashboard
    recent = []
    if _QUERY_LOG_FILE.exists():
        lines = _QUERY_LOG_FILE.read_text().splitlines()
        for line in lines[-10:]:
            try:
                recent.append(json.loads(line))
            except Exception:
                pass

    return {
        "total_queries": len(_QUERY_LOG_FILE.read_text().splitlines()) if _QUERY_LOG_FILE.exists() else 0,
        "total_documents": len(docs),
        "total_chunks": total_chunks,
        "latency": get_latency_stats(),
        "total_tokens_used": total_tokens,
        "estimated_total_cost_usd": round(total_cost, 6),
        "uptime_seconds": round(time.time() - _start_time, 1),
        "recent_queries": recent,
    }
