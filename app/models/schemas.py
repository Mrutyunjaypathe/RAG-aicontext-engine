"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_created: int
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="Your question")
    document_id: Optional[str] = Field(None, description="Target a specific document (optional)")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of chunks to retrieve")

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "What are the main findings of this document?",
                "top_k": 5
            }
        }
    }


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    content: str
    relevance_score: float


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceChunk]
    latency_ms: float
    tokens_used: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Metrics ───────────────────────────────────────────────────────────────────

class LatencyStats(BaseModel):
    p50_ms: float
    p95_ms: float
    p99_ms: float
    avg_ms: float
    min_ms: float
    max_ms: float


class MetricsResponse(BaseModel):
    total_queries: int
    total_documents: int
    total_chunks: int
    latency: LatencyStats
    total_tokens_used: int
    estimated_total_cost_usd: float
    uptime_seconds: float
    recent_queries: list[dict]


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    chunks: int
    uploaded_at: datetime
    size_bytes: int
