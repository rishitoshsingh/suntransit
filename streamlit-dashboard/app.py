# app.py
import logging

import pydeck as pdk
import streamlit as st
from src.utils.redis_utils import (
    connect_redis,
    fetch_trail,
    get_latest_bearing,
    get_trip_route,
    get_vehicle_ids,
)
from src.utils.trips_info import get_trip_df
from streamlit_autorefresh import st_autorefresh

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit-trails")

# Streamlit page setup
st.set_page_config(layout="wide")
st_autorefresh(interval=10_000, key="refresh")
st.sidebar.title("SunTransit Dashboard")
st.sidebar.markdown("### Creator\nRishitosh Singh")
city = st.sidebar.selectbox("Select City", options=["Phoenix", "Boston"], index=0)

# Track the selected city and trip_df in session_state
if "last_selected_city" not in st.session_state:
    st.session_state.last_selected_city = None
if "trips_df" not in st.session_state:
    st.session_state.trips_df = None

# Only reload DataFrame if city has changed
if city != st.session_state.last_selected_city:
    st.session_state.last_selected_city = city
    st.session_state.trips_df = get_trip_df(city.lower())

# Use the cached trips_df
trips_df = st.session_state.trips_df

# Connect to Redis
db = {"Phoenix": 0, "Boston": 1}.get(city)
city_coords = {
    "Phoenix": {"latitude": 33.4484, "longitude": -112.0740},
    "Boston": {"latitude": 42.3554, "longitude": -71.0605},
}
r = connect_redis(db)
st.sidebar.success("Connected to RedisTimeSeries")

# Read data from Redis and build trails
vehicle_ids = get_vehicle_ids(r)
trails, dot_data = [], []
vehicles_info = []

for vid in vehicle_ids:
    path = fetch_trail(r, vid)
    if not path:
        continue

    bearing = get_latest_bearing(r, vid)
    trip_id, route_id = get_trip_route(r, vid)
    
    if trips_df is None:
        st.error("Trip data not loaded. Please refresh the page.")
        continue

    trip_info = trips_df[trips_df["trip_id"] == trip_id].iloc[0] if trip_id in trips_df["trip_id"].values else None
    if trip_info is None:
        continue

    route_color = trip_info.get("route_color")
    trip_headsign = trip_info.get("trip_headsign")
    route_short_name = trip_info.get("route_short_name")
    if route_short_name is None or trip_headsign is None:
        continue

    vehicles_info.append({
        "vehicle_id": vid,
        "path": path,
        "position": path[0],
        "bearing": (bearing + 180) % 360,
        "trip_id": trip_id,
        "route_id": route_id,
        "route_color": route_color,
        "trip_headsign": trip_headsign,
        "route_short_name": route_short_name
    })
# Path layer
path_layer = pdk.Layer(
    "PathLayer",
    vehicles_info,
    get_path="path",
    get_color="route_color",
    width_scale=20,
    width_min_pixels=2,
    pickable=True,
)

# Dot layer
dot_layer = pdk.Layer(
    "ScatterplotLayer",
    vehicles_info,
    get_position="position",
    get_fill_color="route_color",
    get_radius=20,
    radius_scale=3,
    radius_min_pixels=10,
    radius_max_pixels=20,
    pickable=True,
    stroked=True
)

# View state
coords = city_coords.get(city, {"latitude": 0, "longitude": 0})
view_state = pdk.ViewState(
    latitude=coords["latitude"],
    longitude=coords["longitude"],
    zoom=11,
    pitch=0
)
# Custom CSS for full-screen
st.markdown("""
<style>
.block-container {
    padding: 0rem 1rem 0rem 1rem;
    max-width: 100vw;
}
#deckgl-wrapper {
    height: 100vh !important;
    width: 100vw !important;
    margin: 0;
    padding: 0;
}
</style>
""", unsafe_allow_html=True)

# Render the map
st.pydeck_chart(
    pdk.Deck(
        layers=[path_layer, dot_layer],
        initial_view_state=view_state,
        tooltip={"text": "{route_short_name}: {trip_headsign}"},
        map_provider="carto",
        map_style="dark",
        height=1000
    ),
    use_container_width=True
)