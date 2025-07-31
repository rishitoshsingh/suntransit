import json
import logging
import os
from math import asin, cos, radians, sin, sqrt

import redis
# from upstash_redis import Redis
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import DoubleType, LongType, StringType, StructField, StructType

GTFS_AGENCY = os.getenv("GTFS_AGENCY")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB"))
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BROKER")


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(f"SunTransitKafkaToRedis-{GTFS_AGENCY}")

# Define schema matching your vehicle JSON structure
# vehicle_schema = StructType() \
#     .add("vehicle_id", StringType()) \
#     .add("label", StringType()) \
#     .add("lat", DoubleType()) \
#     .add("lon", DoubleType()) \
#     .add("bearing", DoubleType()) \
#     .add("speed", DoubleType()) \
#     .add("route_id", StringType()) \
#     .add("trip_id", StringType()) \
#     .add("timestamp", LongType())
vehicle_schema = StructType([
    StructField("id", StringType()),  # Entity ID
    StructField("vehicle", StructType([
        StructField("trip", StructType([
            StructField("tripId", StringType()),
            StructField("routeId", StringType()),
            StructField("directionId", StringType()),
        ])),
        StructField("position", StructType([
            StructField("latitude", DoubleType()),
            StructField("longitude", DoubleType()),
            StructField("bearing", DoubleType()),
            StructField("odometer", DoubleType()),
            StructField("speed", DoubleType()),
        ])),
        StructField("currentStopSequence", StringType()),
        StructField("currentStatus", StringType()),
        StructField("timestamp", StringType()),  # UNIX epoch as string
        StructField("stopId", StringType()),
        StructField("vehicle", StructType([
            StructField("id", StringType()),
            StructField("label", StringType()),
        ])),
    ]))
])

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
                    "RETENTION", 300000,
                    "LABELS", "vehicle_id", row.vehicle_id, "metric", metric
                )
                redis_client.expire(key, 300)
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
        # logger.warning(f"Unrealistic jump detected for vehicle {row.vehicle_id}: {distance:.2f} meters")
        return False

    return True

    

def save_to_redis(df, epoch_id):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, decode_responses=True)
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
                    pass
            
            if row.trip_id:
                try:
                    r.set(f"vehicle:{vehicle_id}:trip_id", row.trip_id)
                except Exception as e:
                    pass

            if row.route_id:
                try:
                    r.set(f"vehicle:{vehicle_id}:route_id", row.route_id)
                except Exception as e:
                    pass

    except Exception as e:
        logger.error(f"[Batch {epoch_id}] Failed to save to RedisTimeSeries: {e}")

if __name__ == "__main__":
    logger.info("🚀 Starting SunTransit Spark Job (Kafka → Redis)...")

    spark = SparkSession.builder \
        .appName(f"SunTransitKafkaToRedis-{GTFS_AGENCY}") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    kafka_topic = os.getenv("KAFKA_TOPIC")

    logger.info(f"Reading from Kafka topic '{kafka_topic}' at broker '{KAFKA_BOOTSTRAP}'")

    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
        .option("subscribe", kafka_topic) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()

    # value_df = kafka_df.selectExpr("CAST(value AS STRING) as json_str")

    # vehicles_df = value_df.select(
    #     from_json(col("json_str"), vehicle_schema).alias("data")
    # ).select("data.*")

    value_df = kafka_df.selectExpr("CAST(value AS STRING) as json_str")

    vehicles_df = value_df.select(
        from_json(col("json_str"), vehicle_schema).alias("data")
    ).select(
        col("data.id").alias("entity_id"),
        col("data.vehicle.trip.tripId").alias("trip_id"),
        col("data.vehicle.trip.routeId").alias("route_id"),
        col("data.vehicle.trip.directionId").alias("direction_id"),
        col("data.vehicle.position.latitude").alias("lat"),
        col("data.vehicle.position.longitude").alias("lon"),
        col("data.vehicle.position.bearing").alias("bearing"),
        col("data.vehicle.position.odometer").alias("odometer"),
        col("data.vehicle.position.speed").alias("speed"),
        col("data.vehicle.timestamp").cast("long").alias("timestamp"),
        col("data.vehicle.stopId").alias("stop_id"),
        col("data.vehicle.currentStatus").alias("current_status"),
        col("data.vehicle.currentStopSequence").alias("current_stop_sequence"),
        col("data.vehicle.vehicle.id").alias("vehicle_id"),
        col("data.vehicle.vehicle.label").alias("label")
    )

    query = vehicles_df.writeStream \
        .foreachBatch(save_to_redis) \
        .outputMode("update") \
        .start()
        # .option("checkpointLocation", "/app/checkpoints/kafka_to_redis") \

    logger.info("✅ Spark streaming query started. Awaiting termination...")
    query.awaitTermination()