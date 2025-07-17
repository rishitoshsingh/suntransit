# app.py
import logging

import pydeck as pdk
import streamlit as st
from src.utils.redis_utils import (
    connect_redis,
    fetch_trail,
    get_latest_bearing,
    get_vehicle_ids,
)
from streamlit_autorefresh import st_autorefresh

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit-trails")

# Streamlit page setup
st.set_page_config(layout="wide")
st_autorefresh(interval=1_000, key="refresh")
st.sidebar.title("SunTransit Dashboard")
st.sidebar.markdown("### Creator\nRishitosh Singh")
city = st.sidebar.selectbox("Select City", options=["Phoenix", "San Francisco", "New York"], index=0)
st.sidebar.markdown(f"**Selected city:** {city}")

# Connect to Redis
r = connect_redis()
st.sidebar.success("Connected to RedisTimeSeries")

# Read data from Redis and build trails
vehicle_ids = get_vehicle_ids(r)
trails, dot_data = [], []

for vid in vehicle_ids:
    path = fetch_trail(r, vid)
    if not path:
        continue

    bearing = get_latest_bearing(r, vid)

    trails.append({"vehicle_id": vid, "path": path})
    dot_data.append({
        "position": path[0],
        "vehicle_id": vid,
        "bearing": (bearing + 180) % 360,
    })

# Path layer
path_layer = pdk.Layer(
    "PathLayer",
    [{"vehicle_id": t["vehicle_id"], "path": t["path"]} for t in trails],
    get_path="path",
    get_color=[0, 128, 255],
    width_scale=20,
    width_min_pixels=2,
    pickable=True,
)

# Dot layer
dot_layer = pdk.Layer(
    "ScatterplotLayer",
    dot_data,
    get_position="position",
    get_fill_color=[0, 128, 255],
    get_radius=20,
    radius_scale=3,
    radius_min_pixels=10,
    radius_max_pixels=20,
    pickable=True,
    stroked=True
)

# View state
view_state = pdk.ViewState(latitude=33.4484, longitude=-112.0740, zoom=11, pitch=0)

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
        tooltip={"text": "Vehicle {vehicle_id}"},
        height=1000
    ),
    use_container_width=True
)