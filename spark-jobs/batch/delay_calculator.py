import os

from offset import OffsetManager
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    concat_ws,
    date_add,
    from_json,
    from_unixtime,
    row_number,
    to_date,
    unix_timestamp,
    when,
    to_timestamp,
    date_format,
    lit,
)
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)
from pyspark.sql.window import Window

# --------------- Configuration via Environment Variables ---------------
S3_BUCKET = os.getenv("S3_BUCKET")  # use s3a:// not s3://
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BROKER")
GTFS_AGENCY = os.getenv("GTFS_AGENCY")
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB = os.getenv("MONGODB_DB")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")
TIMEZONE = os.getenv("TIMEZONE")

STOP_TIMES_PATH = f"{S3_BUCKET}/static_gtfs/{GTFS_AGENCY}/stop_times.txt"
PARQUET_PATH = f"{S3_BUCKET}/stop_times_delay/"

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(f"GTFS-Batch-{GTFS_AGENCY}")

logger.info(f"S3_BUCKET: {S3_BUCKET}")
logger.info(f"KAFKA_TOPIC: {KAFKA_TOPIC}")
logger.info(f"KAFKA_BOOTSTRAP: {KAFKA_BOOTSTRAP}")
logger.info(f"GTFS_AGENCY: {GTFS_AGENCY}")
logger.info(f"MONGODB_URL: {MONGODB_URL}")
logger.info(f"MONGODB_DB: {MONGODB_DB}")
logger.info(f"MONGODB_COLLECTION: {MONGODB_COLLECTION}")
logger.info(f"TIMEZONE: {TIMEZONE}")


# --------------- Spark Session ---------------
def create_spark_session(app_name="GTFS-RT-Delay-Batch"):
    return SparkSession.builder \
        .appName(app_name) \
        .getOrCreate()

        # .config("spark.jars.packages", ",".join([
        #     "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0",
        #     "org.apache.hadoop:hadoop-aws:3.3.4"
        # ])) \


# --------------- GTFS Vehicle Schema ---------------
def define_vehicle_schema():
    return StructType([
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
            StructField("currentStopSequence", IntegerType()),
            StructField("currentStatus", StringType()),
            StructField("timestamp", StringType()),  # UNIX epoch as string
            StructField("stopId", StringType()),
            StructField("vehicle", StructType([
                StructField("id", StringType()),
                StructField("label", StringType()),
            ])),
        ]))
    ])


# --------------- Add Delay Column ---------------
def add_arrival_delay_seconds(df, timestamp_col="timestamp_ts", arrival_col="arrival_time"):
    df = df.withColumn("base_date", to_date(col(timestamp_col)))
    df = df.withColumn(
        "adjusted_date",
        when(
            (col(arrival_col) < "03:00:00") &
            (col(timestamp_col).substr(12, 8) > col(arrival_col)),
            date_add(col("base_date"), 1)
        ).otherwise(col("base_date"))
    )
    df = df.withColumn(
        "arrival_time_ts",
        unix_timestamp(
            concat_ws(" ", col("adjusted_date").cast("string"), col(arrival_col)),
            "yyyy-MM-dd HH:mm:ss"
        ).cast("timestamp")
    )
    df = df.withColumn(
        "delay_seconds",
        (to_timestamp(col(timestamp_col), "yyyy-MM-dd HH:mm:ss").cast("long") - col("arrival_time_ts").cast("long"))
    )
    return df.drop("base_date", "adjusted_date")


# --------------- Main Entry Point ---------------
def main():
    logger.info("🚀 Starting GTFS RT Delay Batch Job")
    spark = create_spark_session(app_name=f"GTFS-RT-Delay-Batch-{GTFS_AGENCY}")
    schema = define_vehicle_schema()

    try:
        logger.info("🔁 Initializing OffsetManager")
        offset_manager = OffsetManager(
            mongo_url=MONGODB_URL,
            db_name=MONGODB_DB,
            collection_name=MONGODB_COLLECTION,
            bootstrap_servers=KAFKA_BOOTSTRAP
        )

        logger.info("📌 Reading Kafka Offsets")
        starting_offsets = offset_manager.read_offsets(topic=KAFKA_TOPIC, job_type="batch_job")

        logger.info("📥 Reading from Kafka topic: %s", KAFKA_TOPIC)
        kafka_df = spark.read \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
            .option("subscribe", KAFKA_TOPIC) \
            .option("startingOffsets", starting_offsets) \
            .option("endingOffsets", "latest") \
            .load()

        value_df = kafka_df.selectExpr("CAST(value AS STRING) as json_str")
        logger.info("✅ Kafka messages loaded")

        vehicles_df = value_df.select(from_json(col("json_str"), schema).alias("data")) \
            .select(
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
            ) \
            .withColumn("timestamp_ts", from_unixtime(col("timestamp")))
        logger.info("✅ Decoded vehicle payload")

        filtered_df = vehicles_df.filter(
            (col("current_status") == "STOPPED_AT") | (col("current_status") == "1")
        )
        logger.info("📉 Filtered for STOPPED_AT vehicles")

        window_spec = Window.partitionBy("trip_id", "stop_id").orderBy(col("timestamp_ts").asc())
        filtered_df = filtered_df.withColumn("rn", row_number().over(window_spec))
        filtered_df = filtered_df.filter(col("rn") == 1).drop("rn")
        logger.info("✅ Deduplicated to earliest stop event per trip_id-stop_id")

        logger.info(f"📂 Reading GTFS static stop_times from {STOP_TIMES_PATH}")
        stop_times_df = spark.read \
            .option("header", True) \
            .csv(STOP_TIMES_PATH) \
            .withColumn("trip_id", col("trip_id").cast("string")) \
            .withColumnRenamed("stop_id", "static_stop_id") \
            .withColumnRenamed("trip_id", "static_trip_id")

        joined_df = filtered_df.join(
            stop_times_df,
            (filtered_df.stop_id == stop_times_df.static_stop_id) &
            (filtered_df.trip_id == stop_times_df.static_trip_id),
            how="inner"
        ).dropna(subset=["arrival_time"])
        logger.info("🔗 Joined with static GTFS stop_times")

        result_df = add_arrival_delay_seconds(joined_df)
        logger.info("⏱️ Calculated delay_seconds")

        final_df = result_df.select(
            "trip_id", "stop_id", "route_id", "direction_id", "stop_sequence",
            "vehicle_id", "timestamp_ts", "delay_seconds"
        )

        logger.info("💾 Writing to Parquet at %s", PARQUET_PATH)
        final_df.withColumn("day", date_format("timestamp_ts", "yyyy-MM-dd")) \
            .withColumn("agency", lit(GTFS_AGENCY)) \
            .write \
            .mode("append") \
            .partitionBy("agency", "day") \
            .parquet(PARQUET_PATH)

        offset_manager.save_offsets(
            topic=KAFKA_TOPIC,
            offsets=kafka_df.select("partition", "offset"),
            job_type="batch_job"
        )
        logger.info("✅ Offsets saved to MongoDB")
        logger.info("✅ Job completed successfully")
    except Exception as e:
        logger.exception("🔥 Job failed due to exception: %s", e)
        raise
    finally:
        spark.stop()
        logger.info("🧹 Spark session stopped")

if __name__ == "__main__":
    main()