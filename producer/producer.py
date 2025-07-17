import json
import logging
import os
import time

from gtfs_realtime import fetch_vehicle_positions

from kafka import KafkaAdminClient, KafkaProducer

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Environment variables
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "vehicle_positions")
GTFS_URL = os.getenv("GTFS_URL", "https://mna.mecatran.com/utw/ws/gtfsfeed/vehicles/valleymetro?apiKey=4f22263f69671d7f49726c3011333e527368211f")

# Create Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def topic_exists(bootstrap_servers, topic_name):
    try:
        admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
        topics = admin.list_topics()
        return topic_name in topics
    except Exception as e:
        logger.error(f"Failed to check topic existence: {e}")
        return False

# Wait for topic to exist
while not topic_exists(KAFKA_BROKER, KAFKA_TOPIC):
    logger.warning(f"Kafka topic '{KAFKA_TOPIC}' not found. Retrying in 10 seconds...")
    time.sleep(10)

logger.info(f"✅ Kafka topic '{KAFKA_TOPIC}' found. Starting producer...")

logger.info("Starting producer loop")

while True:
    logger.debug("Loop start")
    try:
        vehicles = fetch_vehicle_positions(GTFS_URL)
        for vehicle in vehicles:
            producer.send(KAFKA_TOPIC, vehicle)
        logger.info(f"Published {len(vehicles)} vehicles to topic '{KAFKA_TOPIC}'")
    except Exception as e:
        logger.error(f"Error while fetching or sending data: {e}")
    time.sleep(10)