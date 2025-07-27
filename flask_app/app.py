from flask import Flask, render_template, jsonify
from src.utils.redis_utils import (
    connect_redis,
    fetch_trail,
    get_latest_bearing,
    get_trip_route,
    get_vehicle_ids,
)
from src.utils.trips_info import get_trip_df

app = Flask(__name__)

city_coords = {
    "Phoenix": {"lat": 33.4484, "lon": -112.0740, "db": 0},
    "Boston": {"lat": 42.3554, "lon": -71.0605, "db": 1}
}

@app.route("/")
def home():
    return render_template("map.html", cities=list(city_coords.keys()))

@app.route("/positions/<city>")
def positions(city):
    if city not in city_coords:
        return jsonify([])

    r = connect_redis(city_coords[city]["db"])
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
            "bearing": (bearing + 180) % 360,
            "route_color": f"#{info['route_color']}",
            "trip_headsign": info["trip_headsign"],
            "route_short_name": info["route_short_name"],
            "trip_id": info["trip_id"],
            "route_id": info["route_id"],
        })

    return jsonify(result)
