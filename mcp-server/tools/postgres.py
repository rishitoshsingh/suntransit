import os
from datetime import date, timedelta

import pandas as pd
from fastmcp import FastMCP
from sqlalchemy import create_engine, text

GTFS_ROOT = os.environ.get("GTFS_ROOT", "/data/static_gtfs")

mcp = FastMCP("postgres")

POSTGRESQL_URL = os.environ.get(
    "POSTGRESQL_URL",
    "postgresql+psycopg2://suntransit:suntransit@suntransit-postgres:5432/average_delays",
)

# Maps user-facing agency key → DB agency string
AGENCY_DB = {
    "valley-metro": "ValleyMetro",
    "mbta": "MassachusettsBayTransportationAuthority",
}

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(POSTGRESQL_URL, pool_pre_ping=True, pool_size=3)
    return _engine


def _q(sql: str, **params) -> pd.DataFrame:
    return pd.read_sql(text(sql), _get_engine(), params=params)


def _routes_lookup(agency: str) -> pd.DataFrame:
    path = os.path.join(GTFS_ROOT, AGENCY_DB[agency], "routes.txt")
    return pd.read_csv(path, dtype=str, usecols=["route_id", "route_short_name"])


def _db(agency: str) -> str:
    if agency not in AGENCY_DB:
        raise ValueError(f"Invalid agency '{agency}'. Valid options: {list(AGENCY_DB)}")
    return AGENCY_DB[agency]


def _date_range(end_date: str | None, days: int = 7):
    if days < 1 or days > 365:
        raise ValueError("days must be between 1 and 365")
    try:
        end = date.fromisoformat(end_date) if end_date else date.today() - timedelta(days=1)
    except ValueError:
        raise ValueError(f"Invalid date '{end_date}'. Use YYYY-MM-DD format")
    if end > date.today():
        raise ValueError("end_date cannot be in the future")
    start = end - timedelta(days=days - 1)
    return str(start), str(end)


# ---------------------------------------------------------------------------
# Agency-level
# ---------------------------------------------------------------------------

@mcp.tool
def get_latest_agency_delay(agency: str) -> dict:
    """Get the most recent day's delay stats for an agency.
    agency: valley-metro or mbta
    """
    df = _q(
        "SELECT date, mean_delay, std_delay, total_trips FROM agency_mean_delay "
        "WHERE agency = :a ORDER BY date DESC LIMIT 1",
        a=_db(agency),
    )
    if df.empty:
        return {}
    row = df.iloc[0]
    return {
        "date": str(row["date"]),
        "mean_delay_seconds": round(float(row["mean_delay"]), 1) if pd.notna(row["mean_delay"]) else None,
        "std_delay_seconds": round(float(row["std_delay"]), 1) if pd.notna(row["std_delay"]) else None,
        "total_trips": int(row["total_trips"]) if pd.notna(row["total_trips"]) else None,
    }


@mcp.tool
def get_agency_delays(agency: str, end_date: str | None = None, days: int = 7) -> list:
    """Get daily agency-level delay stats for the past N days.
    Returns one row per day sorted by date.
    agency: valley-metro or mbta
    end_date: YYYY-MM-DD (defaults to today)
    days: how many days back to look (default 7)
    """
    start, end = _date_range(end_date, days)
    df = _q(
        "SELECT date, mean_delay, std_delay, total_trips FROM agency_mean_delay "
        "WHERE agency = :a AND date BETWEEN :s AND :e ORDER BY date",
        a=_db(agency), s=start, e=end,
    )
    df["date"] = df["date"].astype(str)
    df["mean_delay"] = df["mean_delay"].round(1)
    df["std_delay"] = df["std_delay"].round(1)
    return df.to_dict(orient="records")


@mcp.tool
def get_agency_trend(agency: str) -> list:
    """Get average delay per week for the last 4 weeks (current week + 3 prior weeks).
    Use this to answer questions like 'has service gotten better over time?'
    agency: valley-metro or mbta
    """
    df = _q(
        """
        SELECT
            DATE_TRUNC('week', date)::date                          AS week_start,
            FLOOR(EXTRACT(DAY FROM (CURRENT_DATE - date)) / 7)::int AS weeks_ago,
            AVG(mean_delay)                                         AS mean_delay,
            SUM(total_trips)                                        AS total_trips
        FROM agency_mean_delay
        WHERE agency = :a
          AND date >= CURRENT_DATE - INTERVAL '28 days'
        GROUP BY week_start, weeks_ago
        ORDER BY week_start
        """,
        a=_db(agency),
    )
    df["week_start"] = df["week_start"].astype(str)
    df["mean_delay"] = df["mean_delay"].round(1)
    df["total_trips"] = df["total_trips"].astype(int)
    return df.to_dict(orient="records")


# ---------------------------------------------------------------------------
# Route-level
# ---------------------------------------------------------------------------

@mcp.tool
def get_route_delays(agency: str, end_date: str | None = None, days: int = 7) -> list:
    """Get average delay per route over the past N days, sorted worst-first.
    agency: valley-metro or mbta
    end_date: YYYY-MM-DD (defaults to today)
    days: how many days back to look (default 7)
    """
    start, end = _date_range(end_date, days)
    df = _q(
        "SELECT route_id, AVG(mean_delay) AS mean_delay, SUM(total_trips) AS total_trips "
        "FROM route_mean_delay WHERE agency = :a AND date BETWEEN :s AND :e "
        "GROUP BY route_id ORDER BY mean_delay DESC",
        a=_db(agency), s=start, e=end,
    )
    df["mean_delay"] = df["mean_delay"].round(1)
    df["total_trips"] = df["total_trips"].astype(int)
    df = df.merge(_routes_lookup(agency), on="route_id", how="left")
    return df[["route_id", "route_short_name", "mean_delay", "total_trips"]].to_dict(orient="records")


@mcp.tool
def get_route_trends(agency: str) -> list:
    """Get full historical delay per route over time.
    Use this to compare which routes improved or worsened.
    agency: valley-metro or mbta
    """
    df = _q(
        "SELECT route_id, date, mean_delay, total_trips FROM route_mean_delay "
        "WHERE agency = :a ORDER BY route_id, date",
        a=_db(agency),
    )
    df["date"] = df["date"].astype(str)
    df["mean_delay"] = df["mean_delay"].round(1)
    df = df.merge(_routes_lookup(agency), on="route_id", how="left")
    return df[["route_id", "route_short_name", "date", "mean_delay", "total_trips"]].to_dict(orient="records")


# ---------------------------------------------------------------------------
# Stop-level
# ---------------------------------------------------------------------------

@mcp.tool
def get_stop_delays(agency: str, end_date: str | None = None, days: int = 7) -> list:
    """Get average delay per stop over the past N days, sorted worst-first.
    Returns top 50 most delayed stops with stop names.
    agency: valley-metro or mbta
    end_date: YYYY-MM-DD (defaults to today)
    """
    start, end = _date_range(end_date, days)
    df = _q(
        "SELECT stop_id, AVG(mean_delay) AS mean_delay, SUM(total_trips) AS total_trips "
        "FROM stop_mean_delay WHERE agency = :a AND date BETWEEN :s AND :e "
        "GROUP BY stop_id ORDER BY mean_delay DESC LIMIT 50",
        a=_db(agency), s=start, e=end,
    )
    df["mean_delay"] = df["mean_delay"].round(1)
    df["total_trips"] = df["total_trips"].astype(int)

    stops_path = os.path.join(GTFS_ROOT, AGENCY_DB[agency], "stops.txt")
    stops = pd.read_csv(stops_path, dtype=str, usecols=["stop_id", "stop_name"])
    df = df.merge(stops, on="stop_id", how="left")

    return df[["stop_id", "stop_name", "mean_delay", "total_trips"]].to_dict(orient="records")


# ---------------------------------------------------------------------------
# Hourly profiles
# ---------------------------------------------------------------------------

@mcp.tool
def get_hourly_agency(agency: str) -> list:
    """Get average delay by hour of day for an agency.
    Use this to answer 'when is rush hour worst?' or 'what time has best on-time performance?'
    agency: valley-metro or mbta
    """
    df = _q(
        "SELECT hour, mean_delay, total_trips FROM agency_hourly_delay "
        "WHERE agency = :a ORDER BY hour",
        a=_db(agency),
    )
    df["mean_delay"] = df["mean_delay"].round(1)
    return df.to_dict(orient="records")


@mcp.tool
def get_hourly_routes(agency: str) -> list:
    """Get delay by hour of day broken down per route.
    Use this to find which route is worst during morning or evening rush.
    agency: valley-metro or mbta
    """
    df = _q(
        "SELECT route_id, hour, mean_delay, total_trips FROM route_hourly_delay "
        "WHERE agency = :a ORDER BY route_id, hour",
        a=_db(agency),
    )
    df["mean_delay"] = df["mean_delay"].round(1)
    df = df.merge(_routes_lookup(agency), on="route_id", how="left")
    return df[["route_id", "route_short_name", "hour", "mean_delay", "total_trips"]].to_dict(orient="records")
