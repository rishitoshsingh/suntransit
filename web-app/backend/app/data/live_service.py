"""Assembles the full live snapshot for a city: vehicles + derived speed,
bunching, and a network-pulse summary. Used by both the WebSocket loop and a
REST fallback endpoint.
"""
from app.config import CITIES
from app.data import redis_client as rc
from app.data import metrics
from app.data.gtfs import get_trip_df
from app.data.postgres import latest_agency_delay


def build_snapshot(city: str) -> dict:
    cfg = CITIES[city]
    r = rc.get_client(cfg["db"])
    trip_df = get_trip_df(city).fillna("")
    # index trips by id once for fast lookup
    trip_lookup = trip_df.set_index("trip_id")

    vehicles = []
    for vid in rc.get_vehicle_ids(r):
        trail = rc.fetch_trail(r, vid)
        if not trail:
            continue
        trip_id, route_id = rc.get_trip_route(r, vid)
        if trip_id not in trip_lookup.index:
            continue
        info = trip_lookup.loc[trip_id]
        if hasattr(info, "iloc") and getattr(info, "ndim", 1) > 1:
            info = info.iloc[0]

        mph = metrics.speed_mph(trail)
        vehicles.append({
            "vehicle_id": vid,
            "lat": trail[0][1],
            "lon": trail[0][0],
            "trail": [[p[1], p[0]] for p in trail[:6]],  # [lat, lon] for the map
            "bearing": rc.fetch_bearing(r, vid) % 360,
            "last_timestamp": trail[0][2],
            "speed_mph": mph,
            "speed_class": metrics.speed_class(mph),
            "route_id": str(info["route_id"]),
            "direction_id": str(info["direction_id"]),  # 0/1 — used to avoid false bunching on opposite directions
            "route_color": f"#{info['route_color']}" if info["route_color"] else "#888888",
            "route_short_name": str(info["route_short_name"]),
            "trip_headsign": str(info["trip_headsign"]),
        })

    bunching = metrics.find_bunching(vehicles)
    return {
        "city": city,
        "vehicles": vehicles,
        "bunching": bunching,
        "pulse": _pulse(city, vehicles, bunching),
    }


def _pulse(city: str, vehicles: list[dict], bunching: list[dict]) -> dict:
    """Network-pulse stat cards. Live counts from Redis; on-time from Postgres."""
    speeds = [v["speed_mph"] for v in vehicles if v["speed_mph"] is not None]
    stopped = sum(1 for v in vehicles if v["speed_class"] == "stopped")

    # busiest routes by active vehicle count
    counts: dict[str, dict] = {}
    for v in vehicles:
        rid = v["route_id"]
        c = counts.setdefault(rid, {"route_id": rid, "route_short_name": v["route_short_name"],
                                    "route_color": v["route_color"], "count": 0})
        c["count"] += 1
    busiest = sorted(counts.values(), key=lambda c: c["count"], reverse=True)[:5]

    bunched_ids = {vid for p in bunching for vid in (p["a"], p["b"])}

    return {
        "active_vehicles": len(vehicles),
        "avg_speed_mph": round(sum(speeds) / len(speeds), 1) if speeds else None,
        "moving": len(vehicles) - stopped,
        "stopped": stopped,
        "bunched_pairs": len(bunching),
        "bunched_vehicles": len(bunched_ids),
        "busiest_routes": busiest,
        "on_time": latest_agency_delay(CITIES[city]["agency"]),  # labeled "as of date" in UI
    }
