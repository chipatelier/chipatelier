"""
WebSocket endpoints for real-time streaming.

Endpoints:
  WS /api/v1/ws/jobs/{run_id}/logs/stream?token={access_token}
    — Streams ORFS job log lines (plan 01-03).

  WS /api/v1/ws/runs/{run_id}/grade/stream?token={access_token}
    — Pushes grade result once checkpoint evaluation completes (plan 02-04).

Log stream protocol:
  1. Validate JWT access token from query param (browsers cannot set custom WS headers).
  2. Replay all buffered lines from Redis list `logbuf:{run_id}` (handles late joiners).
  3. Subscribe to Redis pub/sub channel `logs:{run_id}` for live lines.
  4. Push each published line to the browser.
  5. On disconnect: unsubscribe and close pubsub (no orphaned subscriptions).

Grade stream protocol:
  1. Validate JWT access token.
  2. Subscribe to Redis pub/sub channel `grade:{run_id}`.
  3. Push a single JSON message when grade result arrives, then close.
  4. 300s timeout — grade should complete well within this window.
"""
import asyncio
import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.redis import get_redis
from app.core.security import decode_token

router = APIRouter()


@router.websocket("/jobs/{run_id}/logs/stream")
async def log_stream(
    websocket: WebSocket,
    run_id: str,
    token: str = Query(..., description="JWT access token (query param — WS cannot use headers)"),
) -> None:
    """Stream log lines for a run.

    Replays the full buffered log first (so late joiners get full history),
    then streams live lines via Redis pub/sub.

    Auth: JWT access token passed as `?token=` query parameter.
    Close code 4008: invalid or expired token.
    """
    # Step 1: Validate token BEFORE accepting the connection
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4008)
            return
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        await websocket.close(code=4008)
        return

    await websocket.accept()

    r = await get_redis()

    # Step 2: Replay buffered lines (handles late joiners — critical for JOB-03)
    buffered: list[bytes] = await r.lrange(f"logbuf:{run_id}", 0, -1)
    for raw in buffered:
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        await websocket.send_text(line)

    # Step 3: Subscribe to live pub/sub channel
    pubsub = r.pubsub()
    await pubsub.subscribe(f"logs:{run_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                text = (
                    data.decode("utf-8", errors="replace")
                    if isinstance(data, bytes)
                    else data
                )
                await websocket.send_text(text)
    except WebSocketDisconnect:
        pass
    finally:
        # Always clean up — no orphaned subscriptions
        await pubsub.unsubscribe(f"logs:{run_id}")
        await pubsub.aclose()


@router.websocket("/runs/{run_id}/grade/stream")
async def grade_stream(
    websocket: WebSocket,
    run_id: str,
    token: str = Query(..., description="JWT access token (query param — WS cannot use headers)"),
) -> None:
    """Stream grade result for a run after checkpoint evaluation completes.

    Subscribes to Redis channel grade:{run_id}. When the evaluate_submission
    Celery task publishes the grade JSON, this endpoint pushes it to the client
    and closes the connection.

    Auth: JWT access token passed as ?token= query parameter.
    Close code 4008: invalid or expired token.
    Timeout: 300 seconds (grade should complete long before this).
    """
    # Validate token BEFORE accepting the connection
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4008)
            return
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        await websocket.close(code=4008)
        return

    await websocket.accept()

    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"grade:{run_id}")

    try:
        async def _listen():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    text = (
                        data.decode("utf-8", errors="replace")
                        if isinstance(data, bytes)
                        else str(data)
                    )
                    await websocket.send_text(text)
                    return  # Single message then close

        # Wait up to 300 seconds for the grade to arrive
        await asyncio.wait_for(_listen(), timeout=300.0)

    except asyncio.TimeoutError:
        # Grade took too long — client can retry via REST
        pass
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"grade:{run_id}")
        await pubsub.aclose()
