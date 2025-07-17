import json
import logging
import os
from math import asin, cos, radians, sin, sqrt

import redis
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import DoubleType, LongType, StringType, StructType

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("SunTransitKafkaToRedis")

# Redis connection (used inside foreachBatch)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Define schema matching your vehicle JSON structure
vehicle_schema = StructType() \
    .add("vehicle_id", StringType()) \
    .add("label", StringType()) \
    .add("lat", DoubleType()) \
    .add("lon", DoubleType()) \
    .add("bearing", DoubleType()) \
    .add("speed", DoubleType()) \
    .add("route_id", StringType()) \
    .add("trip_id", StringType()) \
    .add("timestamp", LongType())



def haversine(lat1, lon1, lat2, lon2):
    # Earth radius in meters
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def delete_old_keys(redis_client, vehicle_id, metrics):
    for metric in metrics:
        key = f"ts:vehicle:{vehicle_id}:{metric}"
        try:
            redis_client.delete(key)
            logger.info(f"Deleted key {key}")
        except Exception as del_err:
            logger.warning(f"Failed to delete {key}: {del_err}")

def should_save_to_redis(row, metrics, redis_client):
    if row.timestamp is None or row.vehicle_id is None:
        logger.warning(f"Skipping row with missing data: {row}")
        return False
    
    all_keys_exist = all(redis_client.exists(f"ts:vehicle:{row.vehicle_id}:{m}") for m in metrics.keys())
    if not all_keys_exist:
        for metric in metrics.keys():
            key = f"ts:vehicle:{row.vehicle_id}:{metric}"
            if not redis_client.exists(key):
                redis_client.execute_command(
                    "TS.CREATE", key,
                    "RETENTION", 36000,
                    "LABELS", "vehicle_id", row.vehicle_id, "metric", metric
                )
        return True

    timestamp, latest_values = None, {}
    for metric in metrics.keys():
        key = f"ts:vehicle:{row.vehicle_id}:{metric}"
        try:
            result = redis_client.execute_command("TS.GET", key)
            timestamp = result[0] if result else None
            latest_values[metric] = result[1] if result else None
        except redis.exceptions.ResponseError:
            latest_values[metric] = None
            delete_old_keys(redis_client, row.vehicle_id, metrics.keys())
            return True
    
    # If timestamp is older than 10 minutes, delete all time series keys for this vehicle, and save the new data
    if timestamp is not None and (int(row.timestamp) - int(timestamp)) > 60000:
        delete_old_keys(redis_client, row.vehicle_id, metrics.keys())
        return True

    # Check if location has changed (lat/lon)
    distance = haversine(float(latest_values.get("lat")), float(latest_values.get("lon")), row.lat, row.lon)
    if distance > 1_000 or distance < 5:
        logger.warning(f"Unrealistic jump detected for vehicle {row.vehicle_id}: {distance:.2f} meters")
        return False

    return True

    

def save_to_redis(df, epoch_id):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password="myStrongPassword123", decode_responses=True)
    try:
        records = df.collect()
        for row in records:
            # Create a unique RedisTimeSeries key for each vehicle attribute
            metrics = {
                "lat": row.lat,
                "lon": row.lon,
                "speed": row.speed,
                "bearing": row.bearing,
            }
            if not should_save_to_redis(row, metrics, r):
                continue
            
            vehicle_id = row.vehicle_id
            ts = row.timestamp
            for metric, value in metrics.items():
                if value is None:
                    continue
                key = f"ts:vehicle:{vehicle_id}:{metric}"
                try:
                    r.execute_command("TS.ADD", key, ts, value)
                except redis.exceptions.ResponseError as e:
                    continue
                    logger.error(f"Failed to add data for {key} at {ts}: {value} because {e}")

    except Exception as e:
        logger.error(f"[Batch {epoch_id}] Failed to save to RedisTimeSeries: {e}")

if __name__ == "__main__":
    logger.info("🚀 Starting SunTransit Spark Job (Kafka → Redis)...")

    spark = SparkSession.builder \
        .appName("SunTransitKafkaToRedis") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    kafka_bootstrap = os.getenv("KAFKA_BROKER", "kafka:9092")
    kafka_topic = os.getenv("KAFKA_TOPIC", "vehicle_positions")

    logger.info(f"Reading from Kafka topic '{kafka_topic}' at broker '{kafka_bootstrap}'")

    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap) \
        .option("subscribe", kafka_topic) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()

    value_df = kafka_df.selectExpr("CAST(value AS STRING) as json_str")

    vehicles_df = value_df.select(
        from_json(col("json_str"), vehicle_schema).alias("data")
    ).select("data.*")

    query = vehicles_df.writeStream \
        .foreachBatch(save_to_redis) \
        .outputMode("update") \
        .start()
        # .option("checkpointLocation", "/app/checkpoints/kafka_to_redis") \

    logger.info("✅ Spark streaming query started. Awaiting termination...")
    query.awaitTermination()