"""H3 cell geometry helpers (boundary polygons + centroids), cached.

The batch job stores only numbers in `h3_hourly_delay`; we turn each `h3_index`
into drawable geometry here at request time. h3-py v4 returns coordinates as
(lat, lng) — GeoJSON wants [lng, lat] — so we swap and close the polygon ring so
the router/frontend can render cells directly. Results are cached: a given cell's
geometry never changes, and there are only a few thousand of them per city.
"""
from functools import lru_cache
import h3


@lru_cache(maxsize=200_000)
def cell_boundary(h3_index: str) -> list[list[float]]:
    """Closed GeoJSON ring [[lng, lat], ...] for one H3 cell."""
    ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(h3_index)]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


@lru_cache(maxsize=200_000)
def cell_center(h3_index: str) -> list[float]:
    """[lng, lat] centroid of one H3 cell."""
    lat, lng = h3.cell_to_latlng(h3_index)
    return [lng, lat]


def fill_h3_gaps(records: list[dict]) -> list[dict]:
    """K=1 neighbor interpolation: fill empty H3 cells adjacent to data cells.

    Each data cell's 6 neighbors that have no data get the trip-weighted average
    delay of their own data-bearing neighbors. This smooths transit corridors
    without fabricating data far from any stops. Areas truly far from transit
    remain empty because none of their 6 neighbors have data.

    Interpolated cells are marked with interpolated=True for frontend styling
    (rendered at reduced opacity to distinguish from measured values).
    """
    data = {r["h3_index"]: r for r in records}
    result: dict[str, dict] = {idx: {**vals, "interpolated": False} for idx, vals in data.items()}

    for idx in list(data.keys()):
        for neighbor in h3.grid_disk(idx, 1):
            if neighbor in result:
                continue
            bearing = [data[n] for n in h3.grid_disk(neighbor, 1) if n in data]
            if not bearing:
                continue
            total_trips = sum(float(d["total_trips"]) for d in bearing)
            if total_trips > 0:
                delay = sum(float(d["mean_delay"]) * float(d["total_trips"]) for d in bearing) / total_trips
            else:
                delay = sum(float(d["mean_delay"]) for d in bearing) / len(bearing)
            result[neighbor] = {
                "h3_index": neighbor,
                "mean_delay": delay,
                "total_trips": 0,
                "interpolated": True,
            }

    return list(result.values())
