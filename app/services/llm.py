"""
LLM service — handles prompt engineering, context injection,
and response generation using Gemini or OpenAI.
"""
import logging
import time
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ── Prompt Templates ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a precise, helpful AI assistant that answers questions \
based ONLY on the provided document context.

Rules you MUST follow:
1. Answer ONLY using information from the context below.
2. If the context does not contain enough information, say: \
   "I could not find sufficient information in the uploaded documents to answer this."
3. Always be factual and concise.
4. Do NOT make up information or use external knowledge.
5. When quoting or paraphrasing, reference which document/chunk it came from.
"""

RAG_TEMPLATE = """{system_prompt}

=== DOCUMENT CONTEXT ===
{context}
========================

User Question: {question}

Answer (based strictly on the context above):"""


# ── Context Builder ───────────────────────────────────────────────────────────

def build_context(retrieved_chunks: List[dict]) -> str:
    """Format retrieved chunks into a structured context block."""
    if not retrieved_chunks:
        return "No relevant documents found."

    parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        parts.append(
            f"[Source {i} | Doc: {chunk['filename']} | Chunk #{chunk['chunk_index']+1}]\n"
            f"{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


# ── LLM Client ────────────────────────────────────────────────────────────────

_llm_client = None


def _get_llm():
    """Lazy-initialize the LLM client."""
    global _llm_client
    if _llm_client is not None:
        return _llm_client

    if settings.llm_provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            _llm_client = ChatGoogleGenerativeAI(
                model=settings.llm_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.1,  # Low temp for factual accuracy
                max_output_tokens=2048,
            )
            logger.info(f"Initialized Gemini LLM: {settings.llm_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM: {e}")
            raise
    else:
        try:
            from langchain_community.chat_models import ChatOpenAI
            _llm_client = ChatOpenAI(
                model=settings.llm_model or "gpt-3.5-turbo",
                openai_api_key=settings.openai_api_key,
                temperature=0.1,
            )
            logger.info("Initialized OpenAI LLM")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI LLM: {e}")
            raise

    return _llm_client


# ── Token Estimation ──────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def estimate_cost(tokens: int, provider: str = "gemini") -> float:
    """
    Estimate cost in USD.
    Gemini 1.5 Flash: free up to 1M tokens/day (May 2025).
    OpenAI GPT-3.5: ~$0.002 per 1K tokens.
    """
    if provider == "gemini":
        return 0.0  # Free tier
    elif provider == "openai":
        return (tokens / 1000) * 0.002
    return 0.0


# ── Main Generation ───────────────────────────────────────────────────────────

def generate_answer(
    question: str,
    retrieved_chunks: List[dict],
) -> dict:
    """
    Generate an answer using the LLM with retrieved context.

    Returns:
        {
            "answer": str,
            "tokens_used": int,
            "estimated_cost_usd": float,
            "latency_ms": float,
        }
    """
    t0 = time.perf_counter()

    # Build the prompt
    context = build_context(retrieved_chunks)
    prompt = RAG_TEMPLATE.format(
        system_prompt=SYSTEM_PROMPT,
        context=context,
        question=question,
    )

    tokens_used = estimate_tokens(prompt)

    # Generate response
    llm = _get_llm()
    try:
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        answer = response.content.strip()
        # Add output tokens
        tokens_used += estimate_tokens(answer)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        answer = f"⚠️ LLM Error: {str(e)}"

    latency_ms = (time.perf_counter() - t0) * 1000
    cost = estimate_cost(tokens_used, settings.llm_provider)

    logger.info(
        f"Generated answer | tokens={tokens_used} | "
        f"latency={latency_ms:.1f}ms | cost=${cost:.5f}"
    )

    return {
        "answer": answer,
        "tokens_used": tokens_used,
        "estimated_cost_usd": cost,
        "latency_ms": latency_ms,
    }
