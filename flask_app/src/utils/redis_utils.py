import logging

import redis

logger = logging.getLogger("streamlit-trails")

def connect_redis(db):
    from os import getenv
    return redis.Redis(
        host=getenv("REDIS_HOST"),
        port=int(getenv("REDIS_PORT", 6379)),
        db=db,
        password=getenv("REDIS_PASSWORD"),
        decode_responses=True
    )

def get_vehicle_ids(r):
    keys = r.keys("ts:vehicle:*:lat")
    return [key.split(":")[2] for key in keys]

def get_trip_route(r, vehicle_id):
    return (r.get(f"vehicle:{vehicle_id}:trip_id"),
            r.get(f"vehicle:{vehicle_id}:route_id"))

def fetch_trail(r, vehicle_id, count=5):
    try:
        lat_key = f"ts:vehicle:{vehicle_id}:lat"
        lon_key = f"ts:vehicle:{vehicle_id}:lon"
        if not (r.exists(lat_key) and r.exists(lon_key)):
            return []

        lat_series = r.execute_command("TS.REVRANGE", lat_key, "-", "+", "COUNT", count)
        lon_series = r.execute_command("TS.REVRANGE", lon_key, "-", "+", "COUNT", count)
        if len(lat_series) != len(lon_series):
            return []

        return [[float(lon[1]), float(lat[1]), int(lat[0])] for lat, lon in zip(lat_series, lon_series)]
    except Exception as e:
        logger.warning(f"Vehicle {vehicle_id} error: {e}")
        return []

def get_latest_bearing(r, vehicle_id):
    try:
        series = r.execute_command("TS.REVRANGE", f"ts:vehicle:{vehicle_id}:bearing", "-", "+", "COUNT", 1)
        return float(series[-1][1]) if series else 0.0
    except:
        return 0.0
