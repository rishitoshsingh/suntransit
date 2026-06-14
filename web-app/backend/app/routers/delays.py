"""Daily stop/route/agency delay aggregates (the core heatmap + sidebar views)."""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from app.config import CITIES
from app.data import postgres as pg
from app.data.gtfs import get_stops_df, get_route_meta
from app.data.util import clean_records, remove_outliers
from app.data.cache import ttl_cache

router = APIRouter(prefix="/api", tags=["delays"])


def _window(date: str):
    try:
        end = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Expected date as YYYY-MM-DD")
    return end - timedelta(days=6), end


def _agency(city: str) -> str:
    if city not in CITIES:
        raise HTTPException(400, f"Unknown city: {city}")
    return CITIES[city]["agency"]


@router.get("/stop_delays/{city}/{date}")
@ttl_cache()
def stop_delays(city: str, date: str):
    agency = _agency(city)
    start, end = _window(date)
    df = pg.stop_delays(agency, start, end)
    if df.empty:
        return {"delays": [], "top_5_stops": [], "bottom_5_stops": []}

    df = df.groupby("stop_id", as_index=False).agg(
        mean_delay=("mean_delay", "mean"), total_trips=("total_trips", "sum"))
    df = remove_outliers(df, "mean_delay")
    df = df.merge(get_stops_df(city), on="stop_id", how="left").dropna(subset=["stop_lat", "stop_lon"])

    max_abs = df["mean_delay"].abs().max()
    df["scaled_delay"] = (0.5 + df["mean_delay"] / (2 * max_abs)).clip(0, 1) if max_abs > 0 else 0.5

    return {
        "delays": clean_records(df.to_dict("records")),
        "top_5_stops": clean_records(df.nlargest(5, "mean_delay").to_dict("records")),
        "bottom_5_stops": clean_records(df.nsmallest(5, "mean_delay").to_dict("records")),
    }


@router.get("/route_delays/{city}/{date}")
@ttl_cache()
def route_delays(city: str, date: str):
    agency = _agency(city)
    start, end = _window(date)
    df = pg.route_delays(agency, start, end)
    if df.empty:
        return {"routes": [], "top_5_routes": [], "bottom_5_routes": []}

    df = df.groupby("route_id", as_index=False).agg(
        mean_delay=("mean_delay", "mean"), total_trips=("total_trips", "sum"))
    df = remove_outliers(df, "mean_delay")

    meta = get_route_meta(city)
    df["route_id"] = df["route_id"].astype(str)
    df["route_color"] = df["route_id"].map(lambda r: meta.get(r, {}).get("route_color", "#888888"))
    df["route_short_name"] = df["route_id"].map(lambda r: meta.get(r, {}).get("route_short_name", ""))
    df["route_path"] = df["route_id"].map(lambda r: meta.get(r, {}).get("route_path", []))

    # Rank by distance from schedule (reliability): closest to on-time = best,
    # furthest off in either direction (early or late) = worst.
    by_abs = df.reindex(df["mean_delay"].abs().sort_values().index)
    return {
        "routes": clean_records(df.drop(columns=["route_path"]).to_dict("records")),
        "top_5_routes": clean_records(by_abs.tail(5)[::-1].to_dict("records")),
        "bottom_5_routes": clean_records(by_abs.head(5).to_dict("records")),
    }


@router.get("/route_path/{city}/{route_id}")
def route_path(city: str, route_id: str):
    """Shape (list of [lat, lon]) + meta for a single route, fetched on click."""
    _agency(city)
    meta = get_route_meta(city).get(str(route_id), {})
    return {
        "route_id": str(route_id),
        "route_short_name": meta.get("route_short_name", ""),
        "route_color": meta.get("route_color", "#888888"),
        "route_path": meta.get("route_path", []),
    }


@router.get("/agency_delays/{agency}/{date}")
@ttl_cache()
def agency_delays(agency: str, date: str):
    start, end = _window(date)
    df = pg.agency_delays(agency, start, end).sort_values("date", ascending=False)
    df["date"] = df["date"].apply(lambda d: d.strftime("%d %b"))
    return clean_records(df.to_dict("records"))
