"""Shared live snapshot hub (hardening B1).

Instead of every WebSocket client (and every /positions call) independently
hammering Redis, ONE background task per city computes the snapshot every
LIVE_PUSH_INTERVAL and fans it out to all subscribers. So N viewers cost the
same as 1 — the key protection for limited hardware.

The refresher runs only while a city has at least one subscriber, and stops
itself when the last one leaves (no wasted work on an idle city).
"""
import time
import asyncio
import logging
from app.config import LIVE_PUSH_INTERVAL
from app.data.live_service import build_snapshot

log = logging.getLogger("live_hub")


class LiveHub:
    def __init__(self):
        self._snap: dict[str, tuple[dict, float]] = {}   # city -> (snapshot, monotonic ts)
        self._queues: dict[str, set[asyncio.Queue]] = {}  # city -> subscriber queues
        self._tasks: dict[str, asyncio.Task] = {}

    def _cached(self, city: str, max_age: float | None = None):
        item = self._snap.get(city)
        if not item:
            return None
        snap, ts = item
        if max_age is not None and (time.monotonic() - ts) > max_age:
            return None
        return snap

    async def get_or_build(self, city: str, max_age: float = LIVE_PUSH_INTERVAL) -> dict:
        """For the REST fallback: serve the cache, or build once if stale/absent."""
        snap = self._cached(city, max_age)
        if snap is None:
            snap = await asyncio.to_thread(build_snapshot, city)
            self._snap[city] = (snap, time.monotonic())
        return snap

    async def subscribe(self, city: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._queues.setdefault(city, set()).add(q)
        if city not in self._tasks or self._tasks[city].done():
            self._tasks[city] = asyncio.create_task(self._loop(city))
        seed = self._cached(city)            # hand over the latest frame immediately
        if seed is not None:
            q.put_nowait(seed)
        return q

    def unsubscribe(self, city: str, q: asyncio.Queue):
        subs = self._queues.get(city)
        if subs:
            subs.discard(q)

    async def _loop(self, city: str):
        log.info("live refresher started for %s", city)
        try:
            while self._queues.get(city):
                try:
                    snap = await asyncio.to_thread(build_snapshot, city)
                    self._snap[city] = (snap, time.monotonic())
                    for q in list(self._queues.get(city, ())):
                        if q.full():                 # drop stale frame, keep newest
                            try: q.get_nowait()
                            except asyncio.QueueEmpty: pass
                        try: q.put_nowait(snap)
                        except asyncio.QueueFull: pass
                except Exception:
                    log.exception("snapshot build failed for %s", city)
                await asyncio.sleep(LIVE_PUSH_INTERVAL)
        finally:
            self._tasks.pop(city, None)
            log.info("live refresher stopped for %s", city)


hub = LiveHub()
