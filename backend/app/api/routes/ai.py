"""
AI feature endpoints — explain (log/timing/drc), advisor, and chat.

Routes:
  POST /ai/explain/log      — explain ORFS log errors in plain language
  POST /ai/explain/timing   — explain timing path violations
  POST /ai/explain/drc      — explain DRC violations
  POST /ai/advisor/config   — suggest config parameter improvements
  POST /ai/chat             — context-aware multi-turn chat (Plan 03 — 501 now)

Privacy constraint (CLAUDE.md):
  NEVER send GDS/DEF file contents, PDK files, or student PII to cloud LLMs.
  context_builder.py enforces this by only including log_tail, ppa, and config.

Phase 3 (Plan 02): explain + advisor endpoints wired to Ollama via llm_client.
Phase 3 (Plan 03): chat endpoint wired.
"""
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.run import Run
from app.ai.llm_client import get_llm_client
from app.ai.context_builder import build_run_context
from app.ai.prompts import PROMPT_REGISTRY

router = APIRouter(prefix="/ai", tags=["ai"])

_NOT_IMPLEMENTED_MSG = "AI features available in Phase 3 — configure Ollama to enable"
_UNAVAILABLE_MSG = (
    "AI assistant is currently unavailable. "
    "Contact your instructor if this persists."
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ExplainLogRequest(BaseModel):
    run_id: UUID
    log_lines: int = 100   # how many tail lines to include in prompt


class ConfigAdvisorRequest(BaseModel):
    run_id: UUID


class ChatRequest(BaseModel):
    run_id: UUID
    message: str
    history: list[dict] = []   # [{role: "user"|"assistant", content: str}]


class ExplainResponse(BaseModel):
    explanation: str
    model: str


class AdvisorResponse(BaseModel):
    suggestions: str
    model: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def safe_generate(prompt: str, max_tokens: int = 1024) -> str:
    """Call llm_client.generate with 503 translation on connectivity errors.

    Converts httpx connection/timeout errors and ollama library errors into
    an HTTP 503 with a user-facing message. Other exceptions propagate normally.
    """
    llm = get_llm_client()
    try:
        return await llm.generate(prompt, max_tokens)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise HTTPException(
            status_code=503,
            detail=_UNAVAILABLE_MSG,
        ) from exc
    except Exception as exc:
        # Catch ollama library errors (ResponseError, RequestError etc.)
        module = getattr(type(exc), "__module__", "") or ""
        if "ollama" in module.lower():
            raise HTTPException(
                status_code=503,
                detail=_UNAVAILABLE_MSG,
            ) from exc
        raise


async def _get_run(run_id: UUID, db: AsyncSession) -> Run:
    """Fetch a run from DB; raise 404 if not found."""
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


# ---------------------------------------------------------------------------
# Explain endpoints
# ---------------------------------------------------------------------------

@router.post("/explain/log", response_model=ExplainResponse)
async def explain_log(
    body: ExplainLogRequest,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explain ORFS log errors in plain language via Ollama."""
    from app.core.config import get_settings
    run = await _get_run(body.run_id, db)
    redis = await get_redis()
    ctx = await build_run_context(run, redis, log_lines=body.log_lines)
    prompt = PROMPT_REGISTRY["explain_log"](ctx)
    result = await safe_generate(prompt, max_tokens=1024)
    return ExplainResponse(explanation=result, model=get_settings().OLLAMA_MODEL)


@router.post("/explain/timing", response_model=ExplainResponse)
async def explain_timing(
    body: ExplainLogRequest,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explain timing path violations (WNS/TNS) via Ollama."""
    from app.core.config import get_settings
    run = await _get_run(body.run_id, db)
    redis = await get_redis()
    ctx = await build_run_context(run, redis, log_lines=body.log_lines)
    prompt = PROMPT_REGISTRY["explain_timing"](ctx)
    result = await safe_generate(prompt, max_tokens=1024)
    return ExplainResponse(explanation=result, model=get_settings().OLLAMA_MODEL)


@router.post("/explain/drc", response_model=ExplainResponse)
async def explain_drc(
    body: ExplainLogRequest,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explain DRC routing violations via Ollama."""
    from app.core.config import get_settings
    run = await _get_run(body.run_id, db)
    redis = await get_redis()
    ctx = await build_run_context(run, redis, log_lines=body.log_lines)
    prompt = PROMPT_REGISTRY["explain_drc"](ctx)
    result = await safe_generate(prompt, max_tokens=1024)
    return ExplainResponse(explanation=result, model=get_settings().OLLAMA_MODEL)


# ---------------------------------------------------------------------------
# Advisor endpoint
# ---------------------------------------------------------------------------

@router.post("/advisor/config", response_model=AdvisorResponse)
async def advisor_config(
    body: ConfigAdvisorRequest,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Suggest config parameter improvements grounded in PPA metrics via Ollama."""
    from app.core.config import get_settings
    run = await _get_run(body.run_id, db)
    redis = await get_redis()
    ctx = await build_run_context(run, redis, log_lines=50)
    prompt = PROMPT_REGISTRY["advisor_config"](ctx)
    result = await safe_generate(prompt, max_tokens=1024)
    return AdvisorResponse(suggestions=result, model=get_settings().OLLAMA_MODEL)


# ---------------------------------------------------------------------------
# Chat endpoint (Plan 03 — stub)
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(body: ChatRequest, _=Depends(get_current_user)):
    """Context-aware multi-turn chat. (Plan 03 — returns 501 now)"""
    raise HTTPException(status_code=501, detail=_NOT_IMPLEMENTED_MSG)
