import os
import logging
from dotenv import load_dotenv
load_dotenv("credentials.env")
from datetime import datetime, timedelta

import pandas as pd
from flask import Flask, render_template, jsonify
from src.live_data import get_city_vehicles_live
from src.utils.trips_info import get_city_stops, get_trip_df

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from models import db, StopMeanDelay, RouteMeanDelay, AgencyMeanDelay

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("POSTGRESQL_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

cities = {
    "Phoenix": {
        "coordinates": [33.4484, -112.0740],
        "db": 0,
        "agency": "ValleyMetro"
    },
    "Boston": {
        "coordinates": [42.3601, -71.0589],
        "db": 1,
        "agency": "MassachusettsBayTransportationAuthority"
    }
}

@app.route("/")
def home():
    return render_template("map.html", cities=cities)

@app.route("/positions/<city>")
def positions(city):
    result = get_city_vehicles_live(city, cities[city]["db"])
    return jsonify(result)

@app.route("/stop_delays/<city>/<date>")
def stop_delays(city, date):
    end_date = datetime.strptime(date, "%Y-%m-%d").date()
    start_date = end_date - timedelta(days=6)
    stop_delays = StopMeanDelay.query.filter(
        StopMeanDelay.agency == cities[city]["agency"],
        StopMeanDelay.date >= start_date,
        StopMeanDelay.date <= end_date
    ).statement
    df = pd.read_sql(stop_delays, db.engine)
    df = df.groupby(['agency','stop_id'], as_index=False).agg(
        mean_delay=('mean_delay', 'mean'),
        total_trips=('total_trips', 'sum')
    )
    # Drop outliers based on mean_delay using IQR
    logging.info(f"Initial stop delays shape: {df.shape}")
    df = remove_outliers(df, 'mean_delay')
    logging.info(f"Filtered stop delays shape: {df.shape}")

    stops_df = get_city_stops(city)
    df = pd.merge(df, stops_df, on='stop_id', how='left')


    df['norm_delay'] = df['mean_delay'].clip(lower=-df['mean_delay'].abs().max(), upper=df['mean_delay'].abs().max()) / df['mean_delay'].abs().max()
    df["scaled_delay"] = 0.5 + df["norm_delay"] / (2 * max(abs(df["norm_delay"].max()), abs(df["norm_delay"].min()), 1))
    df["scaled_delay"] = df["scaled_delay"].clip(0, 1)
    
    top_5_stops = df.nlargest(5, 'mean_delay')
    bottom_5_stops = df.nsmallest(5, 'mean_delay')

    # Send both dataframes as JSON
    return jsonify({
        "delays": df.to_dict(orient='records'),
        "top_5_stops": top_5_stops.to_dict(orient='records'),
        "bottom_5_stops": bottom_5_stops.to_dict(orient='records')
    })

@app.route("/route_delays/<city>/<date>")
def route_delays(city, date):
    end_date = datetime.strptime(date, "%Y-%m-%d").date()
    start_date = end_date - timedelta(days=6)
    route_delays = RouteMeanDelay.query.filter(
        RouteMeanDelay.agency == cities[city]["agency"],
        RouteMeanDelay.date >= start_date,
        RouteMeanDelay.date <= end_date
    ).statement
    df = pd.read_sql(route_delays, db.engine)
    df = df.groupby(['agency','route_id'], as_index=False).agg(
        mean_delay=('mean_delay', 'mean'),
        total_trips=('total_trips', 'sum')
    )

    trip_df = get_trip_df(city)
    trip_df.drop_duplicates(subset=['route_id'], inplace=True)
    df = pd.merge(df, trip_df, on='route_id', how='left')
    df["route_color"] = df["route_color"].apply(lambda x: f"#{x}")

    top_5_routes = df.nlargest(5, 'mean_delay')
    bottom_5_routes = df.nsmallest(5, 'mean_delay')

    return jsonify({
        "top_5_routes": top_5_routes.to_dict(orient='records'),
        "bottom_5_routes": bottom_5_routes.to_dict(orient='records')
    })

@app.route("/agency_delays/<agency>/<date>")
def agency_delays(agency, date):

    end_date = datetime.strptime(date, "%Y-%m-%d").date()
    start_date = end_date - timedelta(days=6)
    agency_delays = AgencyMeanDelay.query.filter(
        AgencyMeanDelay.agency == agency,
        AgencyMeanDelay.date >= start_date,
        AgencyMeanDelay.date <= end_date
    ).statement
    df = pd.read_sql(agency_delays, db.engine) \
        .sort_values(by='date', ascending=False)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%d %b")

    return jsonify(df.to_dict(orient='records'))

@app.route("/oldest_date/<agency>")
def oldest_date(agency):
    oldest_date = db.session.query(func.min(AgencyMeanDelay.date)) \
        .filter_by(agency=agency).scalar()
    return jsonify({"oldest_date": oldest_date.strftime("%Y-%m-%d") if oldest_date else None})


def remove_outliers(df, column):
    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]