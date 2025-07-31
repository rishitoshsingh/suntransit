import os
import pandas as pd

DATA_FOLDER = {
    "phoenix": "src/data/valley_metro",
    "boston": "src/data/mbta",
}

gtfs_columns = {
    "trips.txt": ["route_id", "trip_id", "trip_headsign", "shape_id"],
    "routes.txt": ["route_id", "route_short_name", "route_color"],
    "shapes.txt": None,  # Load all columns
    "stops.txt": ["stop_id", "stop_name", "stop_lat", "stop_lon"],
}

def get_shape_paths(shapes_df):
    return (
        shapes_df.sort_values(by=["shape_id", "shape_pt_sequence"])
        .groupby("shape_id", group_keys=False)
        .apply(lambda g: [[lat, lon] for lat, lon in zip(g["shape_pt_lat"], g["shape_pt_lon"])], include_groups=False)
        .reset_index(name="route_path")
    )

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

def get_trip_df(city):

    data_path = DATA_FOLDER[city.lower()]
    trips_df = pd.read_csv(os.path.join(data_path, "trips.txt"), 
                           usecols=gtfs_columns["trips.txt"],
                           dtype={"route_id": str, "trip_id": str})
    routes_df = pd.read_csv(os.path.join(data_path, "routes.txt"), 
                            usecols=gtfs_columns["routes.txt"],
                            dtype={"route_id": str})
    shapes_df = pd.read_csv(os.path.join(data_path, "shapes.txt"), 
                            dtype={"shape_id": str})
    shapes_df = get_shape_paths(shapes_df)
    trips_df = pd.merge(trips_df, routes_df, on='route_id')
    return pd.merge(trips_df, shapes_df, on='shape_id', how='left')

def get_city_stops(city):
    data_path = DATA_FOLDER[city.lower()]
    stops_df = pd.read_csv(os.path.join(data_path, "stops.txt"), usecols=gtfs_columns["stops.txt"])
    stops_df["stop_id"] = stops_df["stop_id"].astype(str)
    stops_df["stop_lat"] = stops_df["stop_lat"].astype(float)
    stops_df["stop_lon"] = stops_df["stop_lon"].astype(float)
    return stops_df