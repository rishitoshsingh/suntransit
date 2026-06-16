import os
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, countDistinct, mean, stddev, sum as _sum, expr, lit, to_date, hour, to_timestamp, broadcast,
)
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number

from h3_lookup import build_stop_h3, H3_RESOLUTIONS


PARQUET_PATH = os.getenv("PARQUET_PATH")
COMPUTE_DELAY = int(os.getenv("COMPUTE_DELAY"))
COMPUTE_TIMEZONE = os.getenv("COMPUTE_TIMEZONE")
AGENCY_LIST = os.getenv("AGENCY_LIST").split(",")
POSTGRESQL_URL = os.getenv("POSTGRESQL_URL")
# S3 append-history datasets (full time-series, never overwritten) for records +
# model training. Paths come from env, derived from S3_BUCKET in env/.env.
STOP_HOURLY_PATH = os.getenv("STOP_HOURLY_PATH")
ROUTE_HOURLY_PATH = os.getenv("ROUTE_HOURLY_PATH")
H3_HOURLY_PATH = os.getenv("H3_HOURLY_PATH")
DATA_DIR = os.getenv("DATA_DIR", "/data")
PROCESS_DATE_STR = (datetime.datetime.now(ZoneInfo(COMPUTE_TIMEZONE)) - datetime.timedelta(days=COMPUTE_DELAY)) \
    .date().isoformat()

print(f"PARQUET_PATH={PARQUET_PATH}")
print(f"COMPUTE_DELAY={COMPUTE_DELAY}")
print(f"COMPUTE_TIMEZONE={COMPUTE_TIMEZONE}")
print(f"AGENCY_LIST={AGENCY_LIST}")
print(f"POSTGRESQL_URL={POSTGRESQL_URL}")
print(f"PROCESS_DATE_STR={PROCESS_DATE_STR}")

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(f"Analyzing-Job-{PROCESS_DATE_STR}")

def create_spark_session(app_name:str):
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.session.timeZone", COMPUTE_TIMEZONE) \
        .getOrCreate()


def write_s3_history(df, path):
    """Append one day's hour-of-day rollup to S3, partitioned by agency/day.

    Mirrors the raw lake convention (batch/delay_calculator.py): append-only, so
    the full time-series is preserved for records and model training.
    """
    df.withColumn("day", lit(PROCESS_DATE_STR)) \
        .coalesce(1) \
        .write \
        .mode("append") \
        .partitionBy("agency", "day") \
        .parquet(path)
    logger.info("✅ appended hourly history to %s", path)


if __name__ == "__main__":
    logger.info(f"🚀 Starting Analyzing data for {PROCESS_DATE_STR}")
    spark = create_spark_session(app_name=f"Analyzing-Job-{PROCESS_DATE_STR}")
    
    df = spark.read.parquet(PARQUET_PATH) \
        .filter(col("day") == PROCESS_DATE_STR) \
        .drop("day")
    
    window_spec = Window.partitionBy("agency", "trip_id", "stop_id", "stop_sequence").orderBy(col("timestamp").asc())
    df = df.withColumn("rn", row_number().over(window_spec)) \
        .filter(col("rn") == 1) \
        .drop("rn")

    # --- S3 append history: hour-of-day rollups (stop / route / h3) ----------
    # Keep the hour so the full time-series can train the delay-prediction model.
    df_hourly = df.withColumn("hour", hour(to_timestamp(col("timestamp_ts"))))

    stop_hourly = df_hourly.groupBy("agency", "stop_id", "hour").agg(
        countDistinct("trip_id").alias("total_trips"),
        mean("delay_seconds").alias("mean_delay"),
        stddev("delay_seconds").alias("std_delay"),
    )
    route_hourly = df_hourly.groupBy("agency", "route_id", "hour").agg(
        countDistinct("trip_id").alias("total_trips"),
        mean("delay_seconds").alias("mean_delay"),
        stddev("delay_seconds").alias("std_delay"),
    )
    # H3: broadcast-join each stop's hexagon (one row per resolution) onto events.
    stop_h3 = build_stop_h3(spark, DATA_DIR, H3_RESOLUTIONS)
    h3_hourly = df_hourly.join(broadcast(stop_h3), on=["agency", "stop_id"], how="inner") \
        .groupBy("agency", "resolution", "h3_index", "hour").agg(
            countDistinct("trip_id").alias("total_trips"),
            mean("delay_seconds").alias("mean_delay"),
            stddev("delay_seconds").alias("std_delay"),
        )

    write_s3_history(stop_hourly, STOP_HOURLY_PATH)
    write_s3_history(route_hourly, ROUTE_HOURLY_PATH)
    write_s3_history(h3_hourly, H3_HOURLY_PATH)

    trip_stop_mean_delay_df = df \
        .groupBy("agency","route_id", "stop_id") \
        .agg(
            countDistinct("trip_id").alias("total_trips"),
            mean("delay_seconds").alias("mean"),
            stddev("delay_seconds").alias("std")
        )
    
    stop_mean_delay = trip_stop_mean_delay_df \
        .withColumn("weighted_delay", col("mean") * col("total_trips")) \
        .groupBy(["agency","stop_id"]) \
        .agg(
            _sum("weighted_delay").alias("total_weighted_delay"),
            _sum("total_trips").alias("total_trips"),
        ) \
        .withColumn("mean_delay", col("total_weighted_delay")/col("total_trips")) \
        .drop("total_weighted_delay")

    route_mean_delay = trip_stop_mean_delay_df \
        .withColumn("weighted_delay", col("mean") * col("total_trips")) \
        .groupBy(["agency","route_id"]) \
        .agg(
            _sum("weighted_delay").alias("total_weighted_delay"),
            _sum("total_trips").alias("total_trips"),
        ) \
        .withColumn("mean_delay", col("total_weighted_delay")/col("total_trips")) \
        .drop("total_weighted_delay")

    agency_mean_delay = df \
        .groupby(["agency"]) \
        .agg(
            countDistinct("trip_id").alias("total_trips"),
            mean("delay_seconds").alias("mean_delay"),
            stddev("delay_seconds").alias("std_delay")
        )

    stop_mean_delay \
        .withColumn("date",to_date(lit(PROCESS_DATE_STR))) \
        .write \
        .format("jdbc") \
        .option("url", POSTGRESQL_URL) \
        .option("dbtable", "stop_mean_delay") \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()
    logger.info("✅ stop_mean_delay saved to PostgreSQL")

    route_mean_delay \
        .withColumn("date",to_date(lit(PROCESS_DATE_STR))) \
        .write \
        .format("jdbc") \
        .option("url", POSTGRESQL_URL) \
        .option("dbtable", "route_mean_delay") \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()
    logger.info("✅ route_mean_delay saved to PostgreSQL")

    agency_mean_delay \
        .withColumn("date",to_date(lit(PROCESS_DATE_STR))) \
        .write \
        .format("jdbc") \
        .option("url", POSTGRESQL_URL) \
        .option("dbtable", "agency_mean_delay") \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()
    logger.info("✅ agency_mean_delay saved to PostgreSQL")
    logger.info(f"✅ Analyzing data for {PROCESS_DATE_STR} completed successfully.")