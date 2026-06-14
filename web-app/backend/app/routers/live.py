"""Live vehicle stream.

WebSocket /ws/live/{city} subscribes to the shared LiveHub — one background task
per city feeds every client, so viewer count doesn't multiply the work on Redis.
REST /api/positions/{city} serves the same cached snapshot.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.config import CITIES, MAX_WS_CONNECTIONS
from app.data.live_hub import hub

router = APIRouter(tags=["live"])
log = logging.getLogger("live")

_ws_count = 0  # global live-connection count (cheap DoS ceiling)


@router.get("/api/positions/{city}")
async def positions(city: str):
    if city not in CITIES:
        raise HTTPException(400, f"Unknown city: {city}")
    return await hub.get_or_build(city)


@router.websocket("/ws/live/{city}")
async def ws_live(ws: WebSocket, city: str):
    global _ws_count
    await ws.accept()
    if city not in CITIES:
        await ws.send_json({"error": f"Unknown city: {city}"})
        await ws.close()
        return
    if _ws_count >= MAX_WS_CONNECTIONS:
        await ws.send_json({"error": "Server at capacity, try again shortly."})
        await ws.close(code=1013)  # "try again later"
        return

    _ws_count += 1
    q = await hub.subscribe(city)
    try:
        while True:
            snap = await q.get()
            await ws.send_json(snap)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("ws_live(%s) error: %s", city, e)
    finally:
        hub.unsubscribe(city, q)
        _ws_count -= 1
