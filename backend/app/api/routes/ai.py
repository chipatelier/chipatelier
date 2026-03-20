"""
AI feature endpoints — explain (log/timing/drc), advisor, and chat.

Routes:
  POST /ai/explain/log      — explain ORFS log errors in plain language
  POST /ai/explain/timing   — explain timing path violations
  POST /ai/explain/drc      — explain DRC violations
  POST /ai/advisor/config   — suggest config parameter improvements
  POST /ai/chat             — context-aware multi-turn chat (NDJSON streaming)

Privacy constraint (CLAUDE.md):
  NEVER send GDS/DEF file contents, PDK files, or student PII to cloud LLMs.
  context_builder.py enforces this by only including log_tail, ppa, and config.

Phase 3 (Plan 02): explain + advisor endpoints wired to Ollama via llm_client.
Phase 3 (Plan 03): chat endpoint wired with NDJSON streaming.
"""
import asyncio
import json
import logging
import re
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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

_log = logging.getLogger("chipatelier.ai")

_CONNECT_ERRORS = (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError)
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF = 5  # seconds between retries


def _is_ollama_error(exc: Exception) -> bool:
    module = getattr(type(exc), "__module__", "") or ""
    return "ollama" in module.lower()


async def safe_generate(prompt: str, max_tokens: int = 1024) -> str:
    """Call llm_client.generate, retrying if Ollama is still starting up.

    On ConnectError/TimeoutException, retries up to _RETRY_ATTEMPTS times with
    _RETRY_BACKOFF second delays — Ollama may need a moment to start after the
    first request arrives (lazy or post-restart start). Only returns 503 once
    all retries are exhausted.
    """
    llm = get_llm_client()
    last_exc: Exception | None = None

    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            return await llm.generate(prompt, max_tokens)
        except _CONNECT_ERRORS as exc:
            last_exc = exc
            _log.warning(
                "Ollama not reachable (attempt %d/%d), retrying in %ds: %s",
                attempt, _RETRY_ATTEMPTS, _RETRY_BACKOFF, exc,
            )
            if attempt < _RETRY_ATTEMPTS:
                await asyncio.sleep(_RETRY_BACKOFF)
        except Exception as exc:
            if _is_ollama_error(exc):
                last_exc = exc
                _log.warning(
                    "Ollama error (attempt %d/%d), retrying in %ds: %s",
                    attempt, _RETRY_ATTEMPTS, _RETRY_BACKOFF, exc,
                )
                if attempt < _RETRY_ATTEMPTS:
                    await asyncio.sleep(_RETRY_BACKOFF)
            else:
                raise

    raise HTTPException(status_code=503, detail=_UNAVAILABLE_MSG) from last_exc


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
    result = await safe_generate(prompt, max_tokens=2048)
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
    result = await safe_generate(prompt, max_tokens=2048)
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
    result = await safe_generate(prompt, max_tokens=2048)
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
    result = await safe_generate(prompt, max_tokens=2048)
    return AdvisorResponse(suggestions=result, model=get_settings().OLLAMA_MODEL)


# ---------------------------------------------------------------------------
# Chat endpoint (Plan 03 — streaming NDJSON)
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(
    body: ChatRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Context-aware multi-turn chat with NDJSON streaming."""
    run = await _get_run(body.run_id, db)
    redis = await get_redis()
    ctx = await build_run_context(run, redis, log_lines=50)

    # Build system prompt with run context
    system_content = (
        f"You are an expert ASIC design engineer helping a university student "
        f"with their OpenROAD ORFS run.\n"
        f"Design: {ctx['design_name']}, PDK: sky130hd\n"
        f"Stage completed: {ctx.get('stage_completed', 'none')}, "
        f"Status: {ctx['status']}\n"
        f"PPA: WNS={ctx['ppa'].get('worst_negative_slack', 'N/A')}, "
        f"TNS={ctx['ppa'].get('total_negative_slack', 'N/A')}, "
        f"DRC={ctx['ppa'].get('drc_routing_errors', 'N/A')}\n"
        f"Config: {json.dumps(ctx.get('config', {}))}\n\n"
        f"Last {len(ctx['log_tail'])} lines of ORFS log:\n"
        + "\n".join(ctx["log_tail"][-30:])
        + "\n\nBe helpful, concise, and specific. Explain for a university student. "
        "Never mention student names, email addresses, or file system paths."
    )

    # Build messages: system + last 10 turns of history + current message
    messages = [{"role": "system", "content": system_content}]
    history_turns = body.history[-20:]  # 10 turns = 20 messages (user+assistant pairs)
    for msg in history_turns:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": body.message})

    llm = get_llm_client()

    async def generate_stream():
        # Retry on connect errors — Ollama may be starting up on first request.
        stream = None
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            try:
                stream = await llm.chat_stream(messages)
                break
            except _CONNECT_ERRORS as exc:
                _log.warning(
                    "Ollama not reachable for chat (attempt %d/%d): %s",
                    attempt, _RETRY_ATTEMPTS, exc,
                )
                if attempt < _RETRY_ATTEMPTS:
                    await asyncio.sleep(_RETRY_BACKOFF)
            except Exception as exc:
                if _is_ollama_error(exc):
                    _log.warning(
                        "Ollama error for chat (attempt %d/%d): %s",
                        attempt, _RETRY_ATTEMPTS, exc,
                    )
                    if attempt < _RETRY_ATTEMPTS:
                        await asyncio.sleep(_RETRY_BACKOFF)
                else:
                    yield json.dumps({"error": _UNAVAILABLE_MSG}) + "\n"
                    return

        if stream is None:
            yield json.dumps({"error": _UNAVAILABLE_MSG}) + "\n"
            return

        try:
            in_think = False
            think_buf = ""
            async for chunk in stream:
                token = chunk.get("message", {}).get("content", "")
                if not token:
                    continue
                # Strip <think>...</think> tags from streaming output
                # Buffer tokens that might be part of <think> tags
                if "<think>" in token or in_think:
                    in_think = True
                    think_buf += token
                    if "</think>" in think_buf:
                        # Remove the think block and yield remaining
                        cleaned = re.sub(r"<think>.*?</think>", "", think_buf, flags=re.DOTALL)
                        if cleaned.strip():
                            yield json.dumps({"token": cleaned}) + "\n"
                        in_think = False
                        think_buf = ""
                    continue
                yield json.dumps({"token": token}) + "\n"
            # Flush any remaining think buffer (incomplete tag)
            if think_buf:
                cleaned = re.sub(r"<think>.*?</think>", "", think_buf, flags=re.DOTALL)
                if cleaned.strip():
                    yield json.dumps({"token": cleaned}) + "\n"
            yield json.dumps({"done": True}) + "\n"
        except Exception:
            yield json.dumps({"error": "AI assistant is currently unavailable. Contact your instructor if this persists."}) + "\n"

    return StreamingResponse(
        generate_stream(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no"},
    )
