"""Central configuration: cities, credentials, tunables.

Credentials are loaded from the existing flask_app/credentials.env so we don't
duplicate secrets. Everything else has a sensible default.
"""
import os
from dotenv import load_dotenv

_here = os.path.dirname(os.path.abspath(__file__))
_repo = os.path.abspath(os.path.join(_here, "..", "..", ".."))

# Reuse the credentials the other apps already use (REDIS_*, POSTGRESQL_URL).
load_dotenv(os.path.join(_repo, "flask_app", "credentials.env"))
load_dotenv(os.path.join(_here, "..", ".env"))  # optional local overrides

# One entry per supported city. `db` is the Redis DB index for that city's feed.
CITIES = {
    "Phoenix": {"coordinates": [33.4484, -112.0740], "db": 0, "agency": "ValleyMetro"},
    "Boston":  {"coordinates": [42.3601, -71.0589],  "db": 1, "agency": "MassachusettsBayTransportationAuthority"},
}

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
POSTGRESQL_URL = os.getenv("POSTGRESQL_URL")
TIMEZONE = os.getenv("TIMEZONE", "America/Phoenix")

# GTFS static CSVs live in the original flask app's data folder.
# In Docker the folder is mounted at /data, overridable via GTFS_ROOT.
GTFS_ROOT = os.getenv("GTFS_ROOT", os.path.join(_repo, "flask_app", "src", "data"))
GTFS_DIRS = {"phoenix": "valley_metro", "boston": "mbta"}

# How often the live WebSocket loop re-reads Redis and pushes to clients (seconds).
LIVE_PUSH_INTERVAL = float(os.getenv("LIVE_PUSH_INTERVAL", 8))

# Bunching: two vehicles on the same route closer than this (metres) are "bunched".
BUNCHING_THRESHOLD_M = float(os.getenv("BUNCHING_THRESHOLD_M", 400))

# Speed colour thresholds (mph) used by the frontend legend too.
SPEED_STOPPED_MPH = 2
SPEED_SLOW_MPH = 12

# --- hardening knobs ---
# Hard ceiling on simultaneous live WebSocket connections (memory/thread guard).
MAX_WS_CONNECTIONS = int(os.getenv("MAX_WS_CONNECTIONS", 300))
# Historical endpoints (delays/trends/hourly) only change daily -> cache results.
HISTORICAL_CACHE_TTL = float(os.getenv("HISTORICAL_CACHE_TTL", 600))  # 10 min
# Browsers may only call the API from these origins ("*" = any, dev default).
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
