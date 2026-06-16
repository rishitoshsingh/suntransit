"""Shared `stop_id -> H3 cell` lookup, imported by both batch jobs.

The delay parquet has no lat/lon (see batch/delay_calculator.py:241), so to bin
delays onto Uber's H3 hexagonal grid we join each event's stop_id to the static
GTFS stop coordinates. Stops are static and few (~18k across both agencies), so
we read stops.txt with pandas on the Spark *driver*, compute the H3 cell per
stop per resolution once, and return a small Spark DataFrame meant to be
`broadcast`-joined onto delay events on (agency, stop_id).

Only the driver imports h3 / reads /data; executors just receive the broadcast
map, so workers need no extra deps and only spark-master needs the data mount.

Submit the owning job with `--py-files /app/h3_lookup.py` so this module is
importable by the driver.
"""
import os
import pandas as pd
import h3
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

# Resolutions precomputed for the website's zoom levels. Edge lengths:
# res 7 ~1.22 km (city), res 8 ~461 m (neighborhood), res 9 ~174 m (street).
# Kept in sync with the web-app's app.config.H3_RESOLUTIONS.
H3_RESOLUTIONS = [7, 8, 9]

# GTFS static stop directory -> the `agency` value written into the delay tables
# (matches CITIES in web-app/backend/app/config.py and lit(GTFS_AGENCY) in the
# delay_calculator output).
DIR_TO_AGENCY = {
    "valley_metro": "ValleyMetro",
    "mbta": "MassachusettsBayTransportationAuthority",
}

_SCHEMA = StructType([
    StructField("agency", StringType()),
    StructField("stop_id", StringType()),
    StructField("resolution", IntegerType()),
    StructField("h3_index", StringType()),
])


def _stop_h3_pandas(data_dir: str, resolutions) -> pd.DataFrame:
    """(agency, stop_id, resolution, h3_index) for every stop, every resolution."""
    frames = []
    for sub, agency in DIR_TO_AGENCY.items():
        path = os.path.join(data_dir, sub, "stops.txt")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, usecols=["stop_id", "stop_lat", "stop_lon"])
        df = df.dropna(subset=["stop_lat", "stop_lon"]).copy()
        df["stop_id"] = df["stop_id"].astype(str)
        lats, lons = df["stop_lat"].tolist(), df["stop_lon"].tolist()
        for res in resolutions:
            cells = [h3.latlng_to_cell(la, lo, res) for la, lo in zip(lats, lons)]
            frames.append(pd.DataFrame({
                "agency": agency,
                "stop_id": df["stop_id"].values,
                "resolution": int(res),
                "h3_index": cells,
            }))
    if not frames:
        return pd.DataFrame(columns=["agency", "stop_id", "resolution", "h3_index"])
    return pd.concat(frames, ignore_index=True)


def build_stop_h3(spark, data_dir: str = None, resolutions=None):
    """Small Spark DataFrame (agency, stop_id, resolution, h3_index).

    `broadcast`-join this onto deduped delay events on (agency, stop_id), then
    group by (agency, resolution, h3_index[, hour]).
    """
    data_dir = data_dir or os.getenv("DATA_DIR", "/data")
    resolutions = list(resolutions or H3_RESOLUTIONS)
    pdf = _stop_h3_pandas(data_dir, resolutions)
    rows = list(pdf.itertuples(index=False, name=None))
    return spark.createDataFrame(rows, schema=_SCHEMA)
