"""GTFS static lookups, cached in memory (the files are read once per process)."""
import os
from functools import lru_cache
import pandas as pd
from app.config import GTFS_ROOT, GTFS_DIRS


def _path(city: str) -> str:
    return os.path.join(GTFS_ROOT, GTFS_DIRS[city.lower()])


@lru_cache(maxsize=4)
def get_trip_df(city: str) -> pd.DataFrame:
    """trip_id -> route_id, headsign, route colour/name, and the route shape path."""
    p = _path(city)
    trips = pd.read_csv(f"{p}/trips.txt",
                        usecols=["route_id", "trip_id", "trip_headsign", "shape_id", "direction_id"],
                        dtype={"route_id": str, "trip_id": str})
    routes = pd.read_csv(f"{p}/routes.txt", usecols=["route_id", "route_short_name", "route_color"],
                         dtype={"route_id": str})
    routes[["route_short_name", "route_color"]] = routes[["route_short_name", "route_color"]].fillna("")
    shapes = _shape_paths(pd.read_csv(f"{p}/shapes.txt", dtype={"shape_id": str}))
    trips = trips.merge(routes, on="route_id")
    return trips.merge(shapes, on="shape_id", how="left")


@lru_cache(maxsize=4)
def get_stops_df(city: str) -> pd.DataFrame:
    p = _path(city)
    df = pd.read_csv(f"{p}/stops.txt", usecols=["stop_id", "stop_name", "stop_lat", "stop_lon"])
    df["stop_id"] = df["stop_id"].astype(str)
    return df


@lru_cache(maxsize=4)
def get_route_meta(city: str) -> dict[str, dict]:
    """route_id -> {short_name, color, path} for joining onto delay aggregates."""
    df = get_trip_df(city).drop_duplicates("route_id")
    out = {}
    for _, r in df.iterrows():
        out[str(r["route_id"])] = {
            "route_short_name": str(r["route_short_name"]),
            "route_color": f"#{r['route_color']}" if r["route_color"] else "#888888",
            "route_path": r["route_path"] if isinstance(r["route_path"], list) else [],
        }
    return out


def _shape_paths(shapes: pd.DataFrame) -> pd.DataFrame:
    return (
        shapes.sort_values(["shape_id", "shape_pt_sequence"])
        .groupby("shape_id", group_keys=False)
        .apply(lambda g: [[float(la), float(lo)] for la, lo in zip(g["shape_pt_lat"], g["shape_pt_lon"])],
               include_groups=False)
        .reset_index(name="route_path")
    )
