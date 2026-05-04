"""
/query router — accepts a natural language question,
retrieves relevant chunks, and generates a grounded LLM response.
"""
import logging
import time

from fastapi import APIRouter, HTTPException

from app.models.schemas import QueryRequest, QueryResponse, SourceChunk
from app.services.llm import generate_answer
from app.services.observability import log_query
from app.services.retrieval import retrieve
from app.models.store import add_query_log

router = APIRouter(prefix="/query", tags=["Query"])
logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Query your documents",
    description=(
        "Ask a natural language question. The system will retrieve relevant "
        "document chunks and generate a grounded answer with source citations."
    ),
)
async def query_documents(request: QueryRequest):
    t_start = time.perf_counter()

    # ── Retrieval ─────────────────────────────────────────────────────────────
    logger.info(f"Query received: '{request.question}'")

    chunks = retrieve(
        query=request.question,
        top_k=request.top_k,
        doc_id=request.document_id,
    )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No documents found in the knowledge base. Please upload documents first.",
        )

    # ── LLM Generation ────────────────────────────────────────────────────────
    llm_result = generate_answer(
        question=request.question,
        retrieved_chunks=chunks,
    )

    total_latency_ms = (time.perf_counter() - t_start) * 1000

    # ── Build response ────────────────────────────────────────────────────────
    sources = [
        SourceChunk(
            document_id=c["document_id"],
            filename=c["filename"],
            chunk_index=c["chunk_index"],
            content=c["content"],
            relevance_score=round(c["relevance_score"], 4),
        )
        for c in chunks
    ]

    response = QueryResponse(
        question=request.question,
        answer=llm_result["answer"],
        sources=sources,
        latency_ms=round(total_latency_ms, 2),
        tokens_used=llm_result["tokens_used"],
        estimated_cost_usd=llm_result["estimated_cost_usd"],
    )

    # ── Observability ─────────────────────────────────────────────────────────
    log_query(
        question=request.question,
        answer=llm_result["answer"],
        sources=chunks,
        latency_ms=total_latency_ms,
        tokens_used=llm_result["tokens_used"],
        estimated_cost_usd=llm_result["estimated_cost_usd"],
    )

    add_query_log({
        "question": request.question,
        "latency_ms": round(total_latency_ms, 2),
        "num_sources": len(sources),
        "tokens_used": llm_result["tokens_used"],
    })

    return response
