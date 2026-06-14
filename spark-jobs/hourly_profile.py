"""Hour-of-day delay profile (parquet -> PostgreSQL).

Sibling to spark-jobs/analyze_daily_records.py. Where the daily job collapses one
day of parquet into daily means, this job keeps the *hour of day* and averages it
over a rolling window (default last 30 days) to answer "when is transit late?".

Writes two small tables, OVERWRITING them each run (rolling profile, ~<1MB):
  agency_hourly_delay(agency, hour, total_trips, mean_delay, std_delay)
  route_hourly_delay (agency, route_id, hour, total_trips, mean_delay, std_delay)

Scheduled as its own cron job (hourly_profile_job.sh, daily 02:30 — just after
analysis_job.sh at 02:00), following the same launcher pattern as the other
spark jobs. Reuses the same env vars (PARQUET_PATH, POSTGRESQL_URL, COMPUTE_TIMEZONE).
"""
import os
import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, hour, to_timestamp, countDistinct, mean, stddev, row_number, lit,
)
from pyspark.sql.window import Window

PARQUET_PATH = os.getenv("PARQUET_PATH")
POSTGRESQL_URL = os.getenv("POSTGRESQL_URL")
COMPUTE_TIMEZONE = os.getenv("COMPUTE_TIMEZONE", "America/Phoenix")
WINDOW_DAYS = int(os.getenv("HOURLY_WINDOW_DAYS", 30))

_today = datetime.datetime.now(ZoneInfo(COMPUTE_TIMEZONE)).date()
WINDOW_START = (_today - datetime.timedelta(days=WINDOW_DAYS)).isoformat()

print(f"PARQUET_PATH={PARQUET_PATH}")
print(f"WINDOW_DAYS={WINDOW_DAYS} (from {WINDOW_START})")


def write_pg(df, table):
    (df.write.format("jdbc")
        .option("url", POSTGRESQL_URL)
        .option("dbtable", table)
        .option("driver", "org.postgresql.Driver")
        .option("truncate", "true")      # keep table/grants, just replace rows
        .mode("overwrite")               # rolling profile -> replace every run
        .save())
    print(f"✅ wrote {table}")


if __name__ == "__main__":
    spark = (SparkSession.builder
             .appName(f"Hourly-Profile-{_today.isoformat()}")
             .config("spark.sql.session.timeZone", COMPUTE_TIMEZONE)
             .getOrCreate())

    # Rolling window of parquet. `day` is a partition column -> cheap filter.
    df = (spark.read.parquet(PARQUET_PATH)
          .filter(col("day") >= WINDOW_START)
          .withColumn("hour", hour(to_timestamp(col("timestamp_ts")))))

    # Same dedup intent as the daily job: one (earliest) event per trip-stop,
    # but kept per day so the same trip on different days isn't collapsed.
    w = Window.partitionBy("agency", "day", "trip_id", "stop_id", "stop_sequence") \
              .orderBy(col("timestamp").asc())
    df = df.withColumn("rn", row_number().over(w)).filter(col("rn") == 1).drop("rn")

    agency_hourly = (df.groupBy("agency", "hour")
                     .agg(countDistinct("trip_id").alias("total_trips"),
                          mean("delay_seconds").alias("mean_delay"),
                          stddev("delay_seconds").alias("std_delay")))

    route_hourly = (df.groupBy("agency", "route_id", "hour")
                    .agg(countDistinct("trip_id").alias("total_trips"),
                         mean("delay_seconds").alias("mean_delay"),
                         stddev("delay_seconds").alias("std_delay")))

    write_pg(agency_hourly.select("agency", "hour", "total_trips", "mean_delay", "std_delay"),
             "agency_hourly_delay")
    write_pg(route_hourly.select("agency", "route_id", "hour", "total_trips", "mean_delay", "std_delay"),
             "route_hourly_delay")

    print("✅ Hourly profile complete")
    spark.stop()
