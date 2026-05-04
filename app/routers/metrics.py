"""
/metrics router — returns observability metrics,
latency stats, cost estimates, and recent query history.
"""
from fastapi import APIRouter
from app.models.schemas import MetricsResponse
from app.services.observability import get_metrics
from app.models.schemas import LatencyStats

router = APIRouter(prefix="/metrics", tags=["Observability"])


@router.get(
    "/",
    response_model=MetricsResponse,
    summary="Get system metrics",
    description="Returns latency statistics, total queries, token usage, cost estimates, and recent query history.",
)
async def get_system_metrics():
    data = get_metrics()
    return MetricsResponse(
        total_queries=data["total_queries"],
        total_documents=data["total_documents"],
        total_chunks=data["total_chunks"],
        latency=LatencyStats(**data["latency"]),
        total_tokens_used=data["total_tokens_used"],
        estimated_total_cost_usd=data["estimated_total_cost_usd"],
        uptime_seconds=data["uptime_seconds"],
        recent_queries=data["recent_queries"],
    )


@router.get("/health", summary="Health check")
async def health():
    return {"status": "ok", "message": "AI Knowledge System is running 🚀"}
