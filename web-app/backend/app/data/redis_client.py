"""Thin Redis access layer. One persistent client per city DB index."""
import redis
from app.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

_clients: dict[int, redis.Redis] = {}


def get_client(db: int = 0) -> redis.Redis:
    if db not in _clients:
        _clients[db] = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=db,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=3,
        )
    return _clients[db]


def get_vehicle_ids(r: redis.Redis) -> list[str]:
    """Active vehicles = those with a lat TimeSeries key.

    Uses SCAN, not KEYS: KEYS blocks the whole Redis server while it walks every
    key, and this Redis is shared with the live ingestion pipeline. SCAN walks in
    small non-blocking chunks instead.
    """
    return [key.split(":")[2] for key in r.scan_iter(match="ts:vehicle:*:lat", count=500)]


def fetch_trail(r: redis.Redis, vid: str, count: int = 12) -> list[list[float]]:
    """Most-recent-first list of [lon, lat, ts_ms] points for a vehicle.

    We pull more points than the map strictly draws so speed can be smoothed.
    """
    try:
        lat_key, lon_key = f"ts:vehicle:{vid}:lat", f"ts:vehicle:{vid}:lon"
        if not (r.exists(lat_key) and r.exists(lon_key)):
            return []
        lat_s = r.execute_command("TS.REVRANGE", lat_key, "-", "+", "COUNT", count)
        lon_s = r.execute_command("TS.REVRANGE", lon_key, "-", "+", "COUNT", count)
        if len(lat_s) != len(lon_s):
            return []
        return [[float(lon[1]), float(lat[1]), int(lat[0])] for lat, lon in zip(lat_s, lon_s)]
    except Exception:
        return []


def fetch_bearing(r: redis.Redis, vid: str) -> float:
    try:
        s = r.execute_command("TS.REVRANGE", f"ts:vehicle:{vid}:bearing", "-", "+", "COUNT", 1)
        return float(s[-1][1]) if s else 0.0
    except Exception:
        return 0.0


def get_trip_route(r: redis.Redis, vid: str) -> tuple[str | None, str | None]:
    return r.get(f"vehicle:{vid}:trip_id"), r.get(f"vehicle:{vid}:route_id")
