import json
import time
import os
from kafka import KafkaProducer
from gtfs_realtime import fetch_vehicle_positions

# Environment variables
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "vehicle_positions")
GTFS_URL = os.getenv("GTFS_URL", "https://gtfs-vm-rt.s3.amazonaws.com/vehicle_positions.pb")

# Create Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# Poll GTFS Realtime feed in a loop
while True:
    try:
        vehicles = fetch_vehicle_positions(GTFS_URL)
        for vehicle in vehicles:
            producer.send(KAFKA_TOPIC, vehicle)
        print(f"Published {len(vehicles)} vehicles to topic {KAFKA_TOPIC}")
    except Exception as e:
        print("Error while fetching/sending:", str(e))
    time.sleep(10)