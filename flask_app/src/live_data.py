from src.utils.redis_utils import (
    connect_redis,
    fetch_trail,
    get_latest_bearing,
    get_trip_route,
    get_vehicle_ids,
)
from src.utils.trips_info import get_trip_df
from datetime import datetime
import pytz
import os
# Set timezone from environment variable or default to UTC
TIMEZONE = os.environ.get("TIMEZONE", "UTC")
tz = pytz.timezone(TIMEZONE)

def get_city_vehicles_live(city, db):
    r = connect_redis(db)
    trip_df = get_trip_df(city.lower())
    vehicle_ids = get_vehicle_ids(r)

    result = []
    for vid in vehicle_ids:
        path = fetch_trail(r, vid)
        if not path:
            continue
        bearing = get_latest_bearing(r, vid)
        trip_id, route_id = get_trip_route(r, vid)
        trip_info = trip_df[trip_df["trip_id"] == trip_id]
        if trip_info.empty:
            continue
        info = trip_info.iloc[0]
        result.append({
            "vehicle_id": vid,
            "trail": [[point[1], point[0]] for point in path],  # lat, lon pairs for Leaflet
            "lat": path[0][1],
            "lon": path[0][0],
            "last_timestamp": datetime.fromtimestamp(path[0][2], tz).strftime('%-I:%M %p' ),
            # "last_timestamp": path[0][2],
            "bearing": (bearing + 180) % 360,
            "route_color": f"#{info['route_color']}",
            "trip_headsign": info["trip_headsign"],
            "route_short_name": info["route_short_name"],
            "trip_id": info["trip_id"],
            "route_id": info["route_id"],
        })
    
    return result