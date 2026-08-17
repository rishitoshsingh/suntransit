import os
from math import asin, cos, radians, sin, sqrt

import pandas as pd
from fastmcp import FastMCP

mcp = FastMCP("gtfs")

GTFS_ROOT = os.environ.get("GTFS_ROOT", "/data/static_gtfs")

CITIES = {
    "valley-metro": {
        "city": "Phoenix",
        "agency": "Valley Metro",
        "gtfs_dir": "ValleyMetro",
    },
    "mbta": {
        "city": "Boston",
        "agency": "Massachusetts Bay Transportation Authority",
        "gtfs_dir": "MassachusettsBayTransportationAuthority",
    },
}


def _validate_agency(agency: str) -> None:
    if agency not in CITIES:
        raise ValueError(f"Invalid agency '{agency}'. Valid options: {list(CITIES)}")


def _path(agency: str, filename: str) -> str:
    return os.path.join(GTFS_ROOT, CITIES[agency]["gtfs_dir"], filename)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


@mcp.tool
def get_routes(agency: str) -> list:
    """List all routes for an agency. agency: valley-metro or mbta"""
    _validate_agency(agency)
    df = pd.read_csv(
        _path(agency, "routes.txt"),
        dtype=str,
        usecols=["route_id", "route_short_name", "route_long_name"],
    )
    return df.to_dict(orient="records")


@mcp.tool
def search_routes(agency: str, query: str) -> list:
    """Search routes by bus number or name (e.g. query='45' finds route 45).
    agency: valley-metro or mbta
    """
    _validate_agency(agency)
    if not query or len(query) > 100:
        raise ValueError("query must be between 1 and 100 characters")
    df = pd.read_csv(
        _path(agency, "routes.txt"),
        dtype=str,
        usecols=["route_id", "route_short_name", "route_long_name"],
    )
    mask = df["route_short_name"].str.contains(query, case=False, na=False) | \
           df["route_long_name"].str.contains(query, case=False, na=False)
    return df[mask].to_dict(orient="records")


@mcp.tool
def search_stops(agency: str, query: str) -> list:
    """Search stops by stop name keyword. Use this only when the user knows
    the name of a specific stop (e.g. 'Central Station', 'Airport').
    Do NOT use this to find stops near a location or address — use find_stops_near instead.
    agency: valley-metro or mbta
    """
    _validate_agency(agency)
    if not query or len(query) > 100:
        raise ValueError("query must be between 1 and 100 characters")
    df = pd.read_csv(
        _path(agency, "stops.txt"),
        dtype=str,
        usecols=["stop_id", "stop_name", "stop_lat", "stop_lon"],
    )
    mask = df["stop_name"].str.contains(query, case=False, na=False)
    return df[mask].to_dict(orient="records")


@mcp.tool
def get_routes_for_stop(agency: str, stop_id: str) -> list:
    """Find all routes that serve a given stop.
    Use search_stops first to get the stop_id.
    agency: valley-metro or mbta
    """
    _validate_agency(agency)
    # chunk-read stop_times — 900k+ rows
    chunks = pd.read_csv(
        _path(agency, "stop_times.txt"),
        dtype=str,
        usecols=["trip_id", "stop_id"],
        chunksize=50_000,
    )
    serving_trip_ids = pd.concat(
        [chunk[chunk["stop_id"] == stop_id]["trip_id"] for chunk in chunks]
    ).unique()

    trips = pd.read_csv(
        _path(agency, "trips.txt"),
        dtype=str,
        usecols=["trip_id", "route_id"],
    )
    routes = pd.read_csv(
        _path(agency, "routes.txt"),
        dtype=str,
        usecols=["route_id", "route_short_name", "route_long_name"],
    )

    serving_route_ids = trips[trips["trip_id"].isin(serving_trip_ids)]["route_id"].unique()
    result = routes[routes["route_id"].isin(serving_route_ids)]
    return result.to_dict(orient="records")


@mcp.tool
def get_route_stops(agency: str, route_id: str, direction_id: str = "0") -> list:
    """Get the complete ordered stop sequence for a route.
    Uses a representative trip for the given direction.
    direction_id: 0 (outbound) or 1 (inbound)
    agency: valley-metro or mbta
    """
    _validate_agency(agency)
    if direction_id not in ("0", "1"):
        raise ValueError("direction_id must be '0' or '1'")
    trips = pd.read_csv(
        _path(agency, "trips.txt"),
        dtype=str,
        usecols=["trip_id", "route_id", "direction_id"],
    )
    candidate = trips[
        (trips["route_id"] == route_id) & (trips["direction_id"] == direction_id)
    ]
    if candidate.empty:
        return []
    trip_id = candidate.iloc[0]["trip_id"]

    # chunk-read stop_times to keep memory low
    chunks = pd.read_csv(
        _path(agency, "stop_times.txt"),
        dtype=str,
        usecols=["trip_id", "stop_id", "stop_sequence", "arrival_time"],
        chunksize=50_000,
    )
    trip_stop_times = pd.concat(
        [chunk[chunk["trip_id"] == trip_id] for chunk in chunks]
    ).sort_values("stop_sequence", key=lambda s: s.astype(int))

    stops = pd.read_csv(
        _path(agency, "stops.txt"),
        dtype=str,
        usecols=["stop_id", "stop_name", "stop_lat", "stop_lon"],
    )
    result = trip_stop_times.merge(stops, on="stop_id")
    return result[
        ["stop_sequence", "stop_id", "stop_name", "stop_lat", "stop_lon", "arrival_time"]
    ].to_dict(orient="records")


@mcp.tool
def find_stops_near(lat: float, lon: float, radius_meters: int = 500) -> list:
    """Find transit stops near a geographic location. Use this when the user
    asks for stops near a place, address, landmark, or their current location.
    Searches all agencies automatically — do not specify an agency.
    lat/lon can be estimated from a place name if the user did not provide exact coordinates.
    Returns stops within radius_meters sorted by distance, with agency and city tagged.
    """
    if not (-90 <= lat <= 90):
        raise ValueError("lat must be between -90 and 90")
    if not (-180 <= lon <= 180):
        raise ValueError("lon must be between -180 and 180")
    if not (1 <= radius_meters <= 10_000):
        raise ValueError("radius_meters must be between 1 and 10000")
    results = []
    for agency_key, meta in CITIES.items():
        df = pd.read_csv(
            _path(agency_key, "stops.txt"),
            dtype=str,
            usecols=["stop_id", "stop_name", "stop_lat", "stop_lon"],
        )
        df["stop_lat"] = df["stop_lat"].astype(float)
        df["stop_lon"] = df["stop_lon"].astype(float)
        df["distance_m"] = df.apply(
            lambda r: _haversine_m(lat, lon, r["stop_lat"], r["stop_lon"]), axis=1
        )
        nearby = df[df["distance_m"] <= radius_meters].copy()
        nearby["agency"] = meta["agency"]
        nearby["city"] = meta["city"]
        results.append(nearby)

    if not results:
        return []

    combined = pd.concat(results).sort_values("distance_m")
    combined["distance_m"] = combined["distance_m"].round(1)
    return combined[
        ["stop_id", "stop_name", "stop_lat", "stop_lon", "distance_m", "agency", "city"]
    ].to_dict(orient="records")
