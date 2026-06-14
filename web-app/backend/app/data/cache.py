"""Tiny in-process TTL cache (hardening B3).

The historical endpoints (delays / trends / hourly) hit Postgres + pandas on
every request, but the underlying data only changes once a day after the batch
job. Caching each result for a few minutes means repeated/hammered requests are
served from memory and never touch the database.
"""
import time
import functools
from app.config import HISTORICAL_CACHE_TTL


def ttl_cache(ttl: float = HISTORICAL_CACHE_TTL):
    def decorator(fn):
        store: dict[tuple, tuple] = {}

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            hit = store.get(key)
            if hit and (now - hit[1]) < ttl:
                return hit[0]
            value = fn(*args, **kwargs)
            store[key] = (value, now)
            if len(store) > 512:  # bound memory: drop expired entries
                for k, (_, ts) in list(store.items()):
                    if (now - ts) >= ttl:
                        store.pop(k, None)
            return value

        return wrapper

    return decorator
