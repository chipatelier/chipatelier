"""
AI feature endpoints — scaffolded in Phase 1, implemented in Phase 3.

Routes:
  POST /ai/explain/log      — explain ORFS log errors in plain language
  POST /ai/explain/timing   — explain timing path violations
  POST /ai/explain/drc      — explain DRC violations
  POST /ai/advisor/config   — suggest config parameter improvements
  POST /ai/chat             — context-aware multi-turn chat

Privacy constraint (CLAUDE.md):
  NEVER send GDS/DEF file contents, PDK files, or student PII to cloud LLMs.
  context_builder.py enforces this by only including log_tail, ppa, and config.

Phase 1: All endpoints return 501 Not Implemented with a clear Phase 3 message.
Phase 3: Replace 501 stubs with actual Ollama calls via llm_client.py.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])

_NOT_IMPLEMENTED_MSG = "AI features available in Phase 3 — configure Ollama to enable"


class ExplainLogRequest(BaseModel):
    run_id: UUID
    log_lines: int = 100   # how many tail lines to include in prompt


class ConfigAdvisorRequest(BaseModel):
    run_id: UUID


class ChatRequest(BaseModel):
    run_id: UUID
    message: str
    history: list[dict] = []   # [{role: "user"|"assistant", content: str}]


@router.post("/explain/log")
async def explain_log(body: ExplainLogRequest, _=Depends(get_current_user)):
    """Explain ORFS log errors in plain language. (Phase 3 — returns 501 now)"""
    raise HTTPException(status_code=501, detail=_NOT_IMPLEMENTED_MSG)


@router.post("/explain/timing")
async def explain_timing(body: ExplainLogRequest, _=Depends(get_current_user)):
    """Explain timing path violations. (Phase 3 — returns 501 now)"""
    raise HTTPException(status_code=501, detail=_NOT_IMPLEMENTED_MSG)


@router.post("/explain/drc")
async def explain_drc(body: ExplainLogRequest, _=Depends(get_current_user)):
    """Explain DRC violations. (Phase 3 — returns 501 now)"""
    raise HTTPException(status_code=501, detail=_NOT_IMPLEMENTED_MSG)


@router.post("/advisor/config")
async def advisor_config(body: ConfigAdvisorRequest, _=Depends(get_current_user)):
    """Suggest config parameter improvements. (Phase 3 — returns 501 now)"""
    raise HTTPException(status_code=501, detail=_NOT_IMPLEMENTED_MSG)


@router.post("/chat")
async def chat(body: ChatRequest, _=Depends(get_current_user)):
    """Context-aware multi-turn chat. (Phase 3 — returns 501 now)"""
    raise HTTPException(status_code=501, detail=_NOT_IMPLEMENTED_MSG)
