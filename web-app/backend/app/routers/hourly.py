"""Hour-of-day "late clock" — reads the precomputed *_hourly_delay tables.

Tables are produced by the batch job (../batch/hourly_profile.py). Results are
cached per the TTL in app.data.cache.
"""
from fastapi import APIRouter, HTTPException
from app.config import CITIES
from app.data import postgres as pg
from app.data.gtfs import get_route_meta
from app.data.util import clean_records
from app.data.cache import ttl_cache

router = APIRouter(prefix="/api", tags=["hourly"])


def _agency(city: str) -> str:
    if city not in CITIES:
        raise HTTPException(400, f"Unknown city: {city}")
    return CITIES[city]["agency"]


@router.get("/hourly/agency/{city}")
@ttl_cache()
def agency_hourly(city: str):
    agency = _agency(city)
    df = pg.agency_hourly(agency)
    return {"available": True, "hours": clean_records(df.to_dict("records"))}


@router.get("/hourly/routes/{city}")
@ttl_cache()
def route_hourly(city: str):
    agency = _agency(city)
    df = pg.route_hourly(agency)
    if df.empty:
        return {"available": True, "routes": []}
    df["route_id"] = df["route_id"].astype(str)
    meta = get_route_meta(city)

    routes = []
    for rid, g in df.groupby("route_id"):
        g = g.sort_values("hour")
        routes.append({
            "route_id": rid,
            "route_short_name": meta.get(rid, {}).get("route_short_name", ""),
            "route_color": meta.get(rid, {}).get("route_color", "#888888"),
            "hours": clean_records(g[["hour", "mean_delay", "std_delay", "total_trips"]].to_dict("records")),
        })
    return {"available": True, "routes": routes}
