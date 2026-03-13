"""
WebSocket endpoint for real-time ORFS job log streaming.

Endpoint: WS /api/v1/ws/jobs/{run_id}/logs/stream?token={access_token}

Protocol:
  1. Validate JWT access token from query param (browsers cannot set custom WS headers).
  2. Replay all buffered lines from Redis list `logbuf:{run_id}` (handles late joiners).
  3. Subscribe to Redis pub/sub channel `logs:{run_id}` for live lines.
  4. Push each published line to the browser.
  5. On disconnect: unsubscribe and close pubsub (no orphaned subscriptions).
"""
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
