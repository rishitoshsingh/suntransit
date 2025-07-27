import os

from offset import OffsetManager
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    abs,
    col,
    concat_ws,
    date_add,
    from_json,
    from_unixtime,
    lit,
    lpad,
    row_number,
    to_date,
    to_timestamp,
    unix_timestamp,
    when,
)
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
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
        .config("spark.sql.session.timeZone", TIMEZONE) \
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
def adjust_arrival_time(df, arrival_time_col="arrival_time"):
    return df \
        .withColumn("hour", col(arrival_time_col).substr(0, 2).cast("int")) \
        .withColumn("hour", when(col("hour")>=24, col("hour")-24).otherwise(col("hour")).cast("string")) \
        .withColumn(arrival_time_col, concat_ws("", lpad(col("hour"),2, "0"), col(arrival_time_col).substr(3,6))) \
        .drop("hour")

def add_arrival_delay_seconds(df, timestamp_col="timestamp", timestamp_str_col="timestamp_ts", arrival_col="arrival_time"):
    return df \
        .withColumn("date-1", date_add(to_date(timestamp_str_col), -1)) \
        .withColumn("date-0", to_date(timestamp_str_col)) \
        .withColumn("date+1", date_add(to_date(timestamp_str_col), 1)) \
        .withColumn(
            "arrival_time-1",
            unix_timestamp(
                concat_ws(" ", col("date-1").cast("string"), col(arrival_col)),
                "yyyy-MM-dd HH:mm:ss"
            ).cast("timestamp")
        ) \
        .withColumn(
            "arrival_time-0",
            unix_timestamp(
                concat_ws(" ", col("date-0").cast("string"), col(arrival_col)),
                "yyyy-MM-dd HH:mm:ss"
            ).cast("timestamp")
        ) \
        .withColumn(
            "arrival_time+1",
            unix_timestamp(
                concat_ws(" ", col("date+1").cast("string"), col(arrival_col)),
                "yyyy-MM-dd HH:mm:ss"
            ).cast("timestamp")
        ) \
        .withColumn(
            "delay_seconds-1",
            (col(timestamp_col) - col("arrival_time-1").cast("long")).cast("double")) \
        .withColumn(
            "delay_seconds-0",
            (col(timestamp_col) - col("arrival_time-0").cast("long")).cast("double")) \
        .withColumn(
            "delay_seconds+1",
            (col(timestamp_col) - col("arrival_time+1").cast("long")).cast("double")) \
        .withColumn (
            "delay_seconds",
            when((abs(col("delay_seconds-1")) <= abs(col("delay_seconds-0"))) & (abs(col("delay_seconds-1")) <= abs(col("delay_seconds+1"))), col("delay_seconds-1"))
            .when((abs(col("delay_seconds-0")) <= abs(col("delay_seconds-1"))) & (abs(col("delay_seconds-0")) <= abs(col("delay_seconds+1"))), col("delay_seconds-0"))
            .otherwise(col("delay_seconds+1")) ) \
        .drop("date-1", "date-0", "date+1", "arrival_time-1", "arrival_time-0", "arrival_time+1", "delay_seconds-1", "delay_seconds-0", "delay_seconds+1")

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
            .option("failOnDataLoss", "false") \
            .load()

        value_df = kafka_df.selectExpr("CAST(value AS STRING) as json_str")
        logger.info("✅ Kafka messages loaded")

        vehicles_df = value_df.select(from_json(col("json_str"), schema).alias("data")) \
            .select(
                col("data.id").alias("entity_id"),
                col("data.vehicle.trip.tripId").alias("trip_id"),
                col("data.vehicle.trip.routeId").alias("route_id"),
                col("data.vehicle.trip.directionId").alias("direction_id"),
                # col("data.vehicle.position.latitude").alias("lat"),
                # col("data.vehicle.position.longitude").alias("lon"),
                # col("data.vehicle.position.bearing").alias("bearing"),
                # col("data.vehicle.position.odometer").alias("odometer"),
                # col("data.vehicle.position.speed").alias("speed"),
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
        ).drop("current_status")
        logger.info("📉 Filtered for STOPPED_AT vehicles")

        window_spec = Window.partitionBy("trip_id", "stop_id", "current_stop_sequence").orderBy(col("timestamp").asc())
        filtered_df = filtered_df.withColumn("rn", row_number().over(window_spec)) \
            .filter(col("rn") == 1).drop("rn")
        logger.info("✅ Deduplicated to earliest stop event per trip_id-stop_id")

        logger.info(f"📂 Reading GTFS static stop_times from {STOP_TIMES_PATH}")
        stop_times_df = spark.read \
            .option("header", True) \
            .csv(STOP_TIMES_PATH) \
            .withColumn("trip_id", col("trip_id").cast("string")) \
            .withColumn("stop_sequence", col("stop_sequence").cast("int")) \
            .withColumnRenamed("stop_id", "static_stop_id") \
            .withColumnRenamed("trip_id", "static_trip_id")
        
        stop_times_df = adjust_arrival_time(stop_times_df, arrival_time_col="arrival_time")

        joined_df = filtered_df.join(
            stop_times_df,
            (filtered_df.stop_id == stop_times_df.static_stop_id) &
            (filtered_df.trip_id == stop_times_df.static_trip_id) & 
            (filtered_df.current_stop_sequence == stop_times_df.stop_sequence),
            how="inner"
        ).dropna(subset=["arrival_time"])
        logger.info("🔗 Joined with static GTFS stop_times")

        result_df = add_arrival_delay_seconds(joined_df, \
                                              timestamp_col="timestamp", \
                                              timestamp_str_col="timestamp_ts", \
                                              arrival_col="arrival_time")

        # Finding Null Delay Rows
        logger.info("🔍 Checking for null delay_seconds")
        null_delay_rows = result_df.filter(col("delay_seconds").isNull())
        count_nulls = null_delay_rows.count()
        if count_nulls > 0:
            logger.warning(f"Found {count_nulls} rows with null delay_seconds:")
            for row in null_delay_rows.collect():
                logger.warning(row)
        logger.info("⏱️ Calculated delay_seconds")

        final_df = result_df.select(
            "trip_id", "stop_id", "route_id", "direction_id", "stop_sequence", 
            "vehicle_id", "timestamp", "timestamp_ts", "arrival_time", "delay_seconds"
        )

        logger.info("💾 Writing to Parquet at %s", PARQUET_PATH)
        final_df.withColumn("day", to_date("timestamp_ts")) \
            .withColumn("agency", lit(GTFS_AGENCY)) \
            .coalesce(1) \
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