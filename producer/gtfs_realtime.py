import logging
import time

import requests
from google.transit import gtfs_realtime_pb2

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def fetch_vehicle_positions(gtfs_url):
    """Fetch vehicle positions from GTFS Realtime feed."""
    response = requests.get(gtfs_url)
    response.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    vehicles = []
    for entity in feed.entity:
        if entity.HasField("vehicle"):
            v = entity.vehicle
            vehicles.append({
                "vehicle_id": v.vehicle.id,
                "label": v.vehicle.label if v.vehicle.HasField("label") else None,
                "lat": v.position.latitude,
                "lon": v.position.longitude,
                "bearing": v.position.bearing if v.position.HasField("bearing") else None,
                "speed": v.position.speed if v.position.HasField("speed") else None,
                "route_id": v.trip.route_id,
                "trip_id": v.trip.trip_id,
                "timestamp": v.timestamp
            })
    
    return vehicles