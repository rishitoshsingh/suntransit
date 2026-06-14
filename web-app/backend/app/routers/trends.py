"""Reliability trends over the FULL history (not the 7-day window)."""
import pandas as pd
from fastapi import APIRouter, HTTPException
from app.config import CITIES
from app.data import postgres as pg
from app.data.gtfs import get_route_meta
from app.data.util import clean_records
from app.data.cache import ttl_cache

router = APIRouter(prefix="/api", tags=["trends"])


def _agency(city: str) -> str:
    if city not in CITIES:
        raise HTTPException(400, f"Unknown city: {city}")
    return CITIES[city]["agency"]


def _trend_badge(series: list[float]) -> str:
    """Compare the recent half of the series to the older half. Lower delay = better."""
    s = [x for x in series if x is not None]
    if len(s) < 4:
        return "flat"
    mid = len(s) // 2
    older, recent = sum(s[:mid]) / mid, sum(s[mid:]) / (len(s) - mid)
    diff = recent - older
    if abs(diff) < 15:  # < 15s change is noise
        return "flat"
    return "worsening" if diff > 0 else "improving"


@router.get("/trends/agency/{city}")
@ttl_cache()
def agency_trend(city: str):
    agency = _agency(city)
    df = pg.agency_history(agency)
    if df.empty:
        return {"series": [], "badge": "flat"}
    df["date"] = df["date"].apply(lambda d: d.strftime("%Y-%m-%d"))
    return {
        "series": clean_records(df.to_dict("records")),
        "badge": _trend_badge(df["mean_delay"].tolist()),
    }


@router.get("/trends/routes/{city}")
@ttl_cache()
def route_trends(city: str):
    """Per-route sparkline series + improving/worsening badge, ranked worst-first."""
    agency = _agency(city)
    df = pg.route_history(agency)
    if df.empty:
        return []
    df["route_id"] = df["route_id"].astype(str)
    meta = get_route_meta(city)

    out = []
    for rid, g in df.groupby("route_id"):
        g = g.sort_values("date")
        spark = [None if pd.isna(x) else round(float(x), 1) for x in g["mean_delay"]]
        valid = [x for x in spark if x is not None]
        if not valid:
            continue
        out.append({
            "route_id": rid,
            "route_short_name": meta.get(rid, {}).get("route_short_name", ""),
            "route_color": meta.get(rid, {}).get("route_color", "#888888"),
            "spark": spark,
            "recent_mean": round(sum(valid[-7:]) / len(valid[-7:]), 1),
            "total_trips": int(g["total_trips"].sum()),
            "badge": _trend_badge(spark),
        })
    out.sort(key=lambda r: r["recent_mean"], reverse=True)
    return out
