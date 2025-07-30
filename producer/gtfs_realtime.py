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

    # vehicles = []
    # for entity in feed.entity:
    #     if entity.HasField("vehicle"):
    #         v = entity.vehicle
    #         vehicles.append({
    #             "vehicle_id": v.vehicle.id,
    #             "label": v.vehicle.label if v.vehicle.HasField("label") else None,
    #             "lat": v.position.latitude,
    #             "lon": v.position.longitude,
    #             "bearing": v.position.bearing if v.position.HasField("bearing") else None,
    #             "speed": v.position.speed if v.position.HasField("speed") else None,
    #             "route_id": v.trip.route_id,
    #             "trip_id": v.trip.trip_id,
    #             "timestamp": v.timestamp,
    #             "stop_id": v.stop_id if v.HasField("stop_id") else None,
    #             "current_status": v.current_status if v.HasField("current_status") else None,
    #             "current_stop_sequence": v.current_stop_sequence if v.HasField("current_stop_sequence") else None,
    #             "odometer": v.position.odometer if v.position.HasField("odometer") else None,
    #             "vehicle_label": v.vehicle.label if v.vehicle.HasField("label") else None,
    #         })
    
    # return vehicles
    vehicle_data = []
    for entity in feed.entity:
        if entity.HasField("vehicle"):
            v = entity.vehicle
            data = {
                "id": entity.id,
                "vehicle": {
                    "trip": {
                        "tripId": v.trip.trip_id if v.trip.HasField("trip_id") else None,
                        "routeId": v.trip.route_id if v.trip.HasField("route_id") else None,
                        "directionId": v.trip.direction_id if v.trip.HasField("direction_id") else None,
                    },
                    "position": {
                        "latitude": v.position.latitude if v.position.HasField("latitude") else None,
                        "longitude": v.position.longitude if v.position.HasField("longitude") else None,
                        "bearing": v.position.bearing if v.position.HasField("bearing") else None,
                        "odometer": v.position.odometer if v.position.HasField("odometer") else None,
                        "speed": v.position.speed if v.position.HasField("speed") else None,
                    },
                    "currentStopSequence": v.current_stop_sequence if v.HasField("current_stop_sequence") else None,
                    "currentStatus": v.current_status if v.HasField("current_status") else None,
                    "timestamp": str(v.timestamp) if v.HasField("timestamp") else None,
                    "stopId": v.stop_id if v.HasField("stop_id") else None,
                    "vehicle": {
                        "id": v.vehicle.id if v.vehicle.HasField("id") else None,
                        "label": v.vehicle.label if v.vehicle.HasField("label") else None,
                    }
                }
            }
            vehicle_data.append(data)
    
    return vehicle_data