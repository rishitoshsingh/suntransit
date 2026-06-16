"""PostgreSQL access via a shared SQLAlchemy engine + pandas.

All tables here are small precomputed aggregates, so plain SELECTs are cheap.
The hourly tables are produced by ../batch/hourly_profile.py.
"""
import pandas as pd
from sqlalchemy import create_engine, text
from app.config import POSTGRESQL_URL

_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(POSTGRESQL_URL, pool_pre_ping=True, pool_size=5)
    return _engine


def _q(sql: str, **params) -> pd.DataFrame:
    return pd.read_sql(text(sql), engine(), params=params)


# --- daily aggregates ------------------------------------------------------

def stop_delays(agency: str, start, end) -> pd.DataFrame:
    return _q(
        "SELECT stop_id, mean_delay, total_trips FROM stop_mean_delay "
        "WHERE agency = :a AND date BETWEEN :s AND :e",
        a=agency, s=start, e=end,
    )


def route_delays(agency: str, start, end) -> pd.DataFrame:
    return _q(
        "SELECT route_id, mean_delay, total_trips FROM route_mean_delay "
        "WHERE agency = :a AND date BETWEEN :s AND :e",
        a=agency, s=start, e=end,
    )


def agency_delays(agency: str, start, end) -> pd.DataFrame:
    return _q(
        "SELECT date, total_trips, mean_delay, std_delay FROM agency_mean_delay "
        "WHERE agency = :a AND date BETWEEN :s AND :e ORDER BY date",
        a=agency, s=start, e=end,
    )


def agency_history(agency: str) -> pd.DataFrame:
    """Full history for the trends view."""
    return _q(
        "SELECT date, total_trips, mean_delay, std_delay FROM agency_mean_delay "
        "WHERE agency = :a ORDER BY date",
        a=agency,
    )


def route_history(agency: str) -> pd.DataFrame:
    return _q(
        "SELECT route_id, date, mean_delay, total_trips FROM route_mean_delay "
        "WHERE agency = :a ORDER BY date",
        a=agency,
    )


def latest_agency_delay(agency: str) -> dict | None:
    df = _q(
        "SELECT date, mean_delay, std_delay, total_trips FROM agency_mean_delay "
        "WHERE agency = :a ORDER BY date DESC LIMIT 1",
        a=agency,
    )
    if df.empty:
        return None
    row = df.iloc[0]
    return {
        "date": row["date"].strftime("%Y-%m-%d"),
        "mean_delay": float(row["mean_delay"]) if pd.notna(row["mean_delay"]) else None,
        "std_delay": float(row["std_delay"]) if pd.notna(row["std_delay"]) else None,
        "total_trips": int(row["total_trips"]) if pd.notna(row["total_trips"]) else None,
    }


def oldest_date(agency: str):
    df = _q("SELECT MIN(date) AS d FROM agency_mean_delay WHERE agency = :a", a=agency)
    d = df.iloc[0]["d"]
    return d.strftime("%Y-%m-%d") if pd.notna(d) else None


# --- hourly profile (new) --------------------------------------------------

def agency_hourly(agency: str) -> pd.DataFrame:
    return _q(
        "SELECT hour, total_trips, mean_delay, std_delay FROM agency_hourly_delay "
        "WHERE agency = :a ORDER BY hour",
        a=agency,
    )


def route_hourly(agency: str) -> pd.DataFrame:
    return _q(
        "SELECT route_id, hour, total_trips, mean_delay, std_delay FROM route_hourly_delay "
        "WHERE agency = :a ORDER BY route_id, hour",
        a=agency,
    )


# --- H3 hexagon heatmap (new) ----------------------------------------------

def h3_delays(agency: str, resolution: int, hour: int | None = None) -> pd.DataFrame:
    """Per-cell delay for one resolution.

    `h3_hourly_delay` keeps the hour-of-day grain; for the all-day heatmap we
    trip-weight the 24 hours back into one mean per cell. Pass `hour` for a
    single hour-of-day slice (the optional time filter).
    """
    if hour is None:
        return _q(
            "SELECT h3_index, "
            "       SUM(mean_delay * total_trips) / NULLIF(SUM(total_trips), 0) AS mean_delay, "
            "       SUM(total_trips) AS total_trips "
            "FROM h3_hourly_delay WHERE agency = :a AND resolution = :r "
            "GROUP BY h3_index",
            a=agency, r=resolution,
        )
    return _q(
        "SELECT h3_index, mean_delay, total_trips FROM h3_hourly_delay "
        "WHERE agency = :a AND resolution = :r AND hour = :h",
        a=agency, r=resolution, h=hour,
    )
