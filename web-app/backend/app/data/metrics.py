"""Derived live metrics computed from Redis TimeSeries points.

Speed and bunching are not stored anywhere — they're calculated here from the
sequence of (lon, lat, timestamp_ms) points each vehicle reports.
"""
import math
from app.config import BUNCHING_THRESHOLD_M, SPEED_STOPPED_MPH, SPEED_SLOW_MPH

_MS_PER_MPH = 0.44704  # metres/sec per mph

# Sanity bounds for the GPS-derived speed. The trail timestamps are whole
# seconds (GTFS) so a fresh vehicle can have two points only ~1s apart; pair
# that with a GPS jump and the naive distance/time blows up to hundreds of mph,
# which then poisons the network-average card. We require a minimum observation
# window and discard physically impossible readings (treated as "unknown").
_MIN_DT_S = 5.0            # need a few seconds of travel for a stable estimate
_MAX_PLAUSIBLE_MPH = 90.0  # transit vehicles don't exceed this; above => glitch


def haversine_m(lon1, lat1, lon2, lat2) -> float:
    """Great-circle distance in metres."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def speed_mph(trail: list[list[float]]) -> float | None:
    """Smoothed speed from the trail (points are most-recent-first).

    Sums distance and time across the recent points and divides — this averages
    out GPS jitter better than a single point-to-point delta.
    """
    if len(trail) < 2:
        return None
    pts = trail[:5]  # last ~40s
    dist = 0.0
    dt = 0.0
    for (lon_a, lat_a, t_a), (lon_b, lat_b, t_b) in zip(pts, pts[1:]):
        dist += haversine_m(lon_a, lat_a, lon_b, lat_b)
        dt += abs(t_a - t_b) / 1000.0  # ms -> s
    if dt < _MIN_DT_S:  # window too short to trust (single fresh point pair)
        return None
    mph = round((dist / dt) / _MS_PER_MPH, 1)
    if mph > _MAX_PLAUSIBLE_MPH:  # GPS jump / bad timestamp, not a real speed
        return None
    return mph


def speed_class(mph: float | None) -> str:
    if mph is None:
        return "unknown"
    if mph <= SPEED_STOPPED_MPH:
        return "stopped"
    if mph <= SPEED_SLOW_MPH:
        return "slow"
    return "moving"


def _bearing_diff(a: float, b: float) -> float:
    """Smallest angle between two compass bearings (0..180)."""
    return abs((a - b + 180) % 360 - 180)


def find_bunching(vehicles: list[dict]) -> list[dict]:
    """Pairs of vehicles on the same route AND same direction, closer than the
    threshold.

    Grouping by (route_id, direction_id) is what stops opposite-direction buses
    (inbound vs outbound, which naturally pass close on a two-way street) from
    being flagged. As a fallback for loop routes (where both directions share a
    direction_id), we also require the two buses to be heading roughly the same
    way (bearing within 90 deg).
    """
    by_dir: dict[tuple, list[dict]] = {}
    for v in vehicles:
        rid = v.get("route_id")
        if rid:
            by_dir.setdefault((rid, v.get("direction_id")), []).append(v)

    pairs = []
    for (rid, _dir), group in by_dir.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if _bearing_diff(a.get("bearing", 0), b.get("bearing", 0)) > 90:
                    continue  # heading opposite ways on a loop -> not bunched
                d = haversine_m(a["lon"], a["lat"], b["lon"], b["lat"])
                if d <= BUNCHING_THRESHOLD_M:
                    pairs.append({
                        "route_id": rid,
                        "route_short_name": a.get("route_short_name", ""),
                        "a": a["vehicle_id"],
                        "b": b["vehicle_id"],
                        "distance_m": round(d),
                        "line": [[a["lon"], a["lat"]], [b["lon"], b["lat"]]],
                    })
    return pairs
