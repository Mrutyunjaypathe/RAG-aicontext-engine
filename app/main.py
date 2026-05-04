"""
FastAPI Application Entry Point
================================
Production AI Knowledge System (RAG + Observability)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.services.observability import setup_logging
from app.routers import upload, query, metrics

# ── Logging ───────────────────────────────────────────────────────────────────
setup_logging()

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="🧠 AI Knowledge System",
    description=(
        "A Production-Ready Retrieval-Augmented Generation (RAG) system.\n\n"
        "Upload your documents and query them with natural language.\n"
        "Every answer comes with source citations and observability metrics."
    ),
    version="1.0.0",
    contact={
        "name": "Mrrutyunjay Pathe",
    },
    license_info={"name": "MIT"},
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow the frontend (served on any port locally) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(query.router)
app.include_router(metrics.router)

# ── Frontend Hosting ──────────────────────────────────────────────────────────
# Serve the HTML/CSS/JS directly from FastAPI so we only need one server in production
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


# ── Startup / Shutdown Events ─────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    import logging
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("🚀 AI Knowledge System starting up...")
    logger.info(f"   LLM Provider : {settings.llm_provider}")
    logger.info(f"   LLM Model    : {settings.llm_model}")
    logger.info(f"   Upload Dir   : {settings.upload_dir}")
    logger.info(f"   Vector Dir   : {settings.vector_dir}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def on_shutdown():
    import logging
    logging.getLogger(__name__).info("AI Knowledge System shutting down. Goodbye! 👋")
