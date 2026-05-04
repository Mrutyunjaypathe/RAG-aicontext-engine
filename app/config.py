"""
Configuration management for the AI Knowledge System.
Reads from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    # ── LLM ──────────────────────────────────────────────────────
    gemini_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: Literal["gemini", "openai"] = "gemini"
    llm_model: str = "gemini-2.5-flash"
    embedding_model: str = "models/gemini-embedding-2"

    # ── RAG ──────────────────────────────────────────────────────
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_results: int = 5
    similarity_threshold: float = 0.7

    # ── Storage ──────────────────────────────────────────────────
    upload_dir: str = "data/uploads"
    vector_dir: str = "data/vectors"
    log_dir: str = "data/logs"

    # ── API ──────────────────────────────────────────────────────
    max_upload_size_mb: int = 50
    allowed_extensions: str = "pdf,txt,docx"

    # ── Observability ────────────────────────────────────────────
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_retention_days: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def allowed_ext_list(self) -> list[str]:
        return [e.strip().lower() for e in self.allowed_extensions.split(",")]

    def ensure_dirs(self):
        """Create all required directories."""
        for d in [self.upload_dir, self.vector_dir, self.log_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
