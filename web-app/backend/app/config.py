"""Central configuration: cities, credentials, tunables."""
import os
from dotenv import load_dotenv

_here = os.path.dirname(os.path.abspath(__file__))
_repo = os.path.abspath(os.path.join(_here, "..", "..", ".."))

load_dotenv(os.path.join(_repo, "credentials.env"))   # AWS keys for local dev
load_dotenv(os.path.join(_here, "..", ".env"))         # optional local overrides

# One entry per supported city. `db` is the Redis DB index for that city's feed.
CITIES = {
    "Phoenix": {"coordinates": [33.4484, -112.0740], "db": 0, "agency": "ValleyMetro",                              "timezone": "America/Phoenix"},
    "Boston":  {"coordinates": [42.3601, -71.0589],  "db": 1, "agency": "MassachusettsBayTransportationAuthority", "timezone": "America/New_York"},
}

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
POSTGRESQL_URL = os.getenv("POSTGRESQL_URL")
TIMEZONE = os.getenv("TIMEZONE", "America/Phoenix")

# GTFS static CSVs live in the original flask app's data folder.
# In Docker the folder is mounted at /data, overridable via GTFS_ROOT.
GTFS_ROOT = os.getenv("GTFS_ROOT", os.path.join(_repo, "data"))
GTFS_DIRS = {"phoenix": "valley_metro", "boston": "mbta"}

# How often the live WebSocket loop re-reads Redis and pushes to clients (seconds).
LIVE_PUSH_INTERVAL = float(os.getenv("LIVE_PUSH_INTERVAL", 8))

# Bunching: two vehicles on the same route closer than this (metres) are "bunched".
BUNCHING_THRESHOLD_M = float(os.getenv("BUNCHING_THRESHOLD_M", 400))

# Speed colour thresholds (mph) used by the frontend legend too.
SPEED_STOPPED_MPH = 2
SPEED_SLOW_MPH = 12

# --- H3 hexagon heatmap ---
# Resolutions precomputed by the batch job (must match spark-jobs/h3_lookup.py).
# Edge length: res 7 ~1.22 km, res 8 ~461 m, res 9 ~174 m.
H3_RESOLUTIONS = [7, 8, 9]
# Map zoom -> resolution. The frontend mirrors this (map/mapController.js) to
# request the right grain as the user zooms; kept here as the source of truth.
# Each tuple is (max_zoom_exclusive, resolution); the last entry is the default.
ZOOM_TO_RES = [(9.5, 7), (12.0, 8), (99.0, 9)]

# --- hardening knobs ---
# Hard ceiling on simultaneous live WebSocket connections (memory/thread guard).
MAX_WS_CONNECTIONS = int(os.getenv("MAX_WS_CONNECTIONS", 300))
# Historical endpoints (delays/trends/hourly) only change daily -> cache results.
HISTORICAL_CACHE_TTL = float(os.getenv("HISTORICAL_CACHE_TTL", 600))  # 10 min
# Browsers may only call the API from these origins ("*" = any, dev default).
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
