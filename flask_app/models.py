from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class StopMeanDelay(db.Model):
    __tablename__ = "stop_mean_delay"

    agency = db.Column(db.String, primary_key=True)
    stop_id = db.Column(db.String, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    total_trips = db.Column(db.Integer)
    mean_delay = db.Column(db.Float)


class RouteMeanDelay(db.Model):
    __tablename__ = "route_mean_delay"

    agency = db.Column(db.String, primary_key=True)
    route_id = db.Column(db.String, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    total_trips = db.Column(db.Integer)
    mean_delay = db.Column(db.Float)


class AgencyMeanDelay(db.Model):
    __tablename__ = "agency_mean_delay"

    agency = db.Column(db.String, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    total_trips = db.Column(db.Integer)
    mean_delay = db.Column(db.Float)
    std_delay = db.Column(db.Float)