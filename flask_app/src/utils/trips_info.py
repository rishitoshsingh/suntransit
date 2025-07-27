import os

import pandas as pd

DATA_FOLDER = {
    "phoenix": "src/data/valley_metro",
    "boston": "src/data/mbta",
}
gtfs_columns = {
    "trips.txt": ["route_id", "trip_id", "trip_headsign", "shape_id"],
    "routes.txt": ["route_id", "route_short_name", "route_color"],
    "shapes.txt": None  # Load all columns
}

def get_shape_paths(shapes_df):
    return (
        shapes_df.sort_values(by=["shape_id", "shape_pt_sequence"])
        .groupby("shape_id")
        .apply(lambda g: [[lon, lat] for lon, lat in zip(g["shape_pt_lon"], g["shape_pt_lat"])])
        .reset_index(name="route_path")
    )

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

def get_trip_df(city):

    data_path = DATA_FOLDER[city]
    trips_df = pd.read_csv(os.path.join(data_path, "trips.txt"), usecols=gtfs_columns["trips.txt"])
    routes_df = pd.read_csv(os.path.join(data_path, "routes.txt"), usecols=gtfs_columns["routes.txt"])
    shapes_df = pd.read_csv(os.path.join(data_path, "shapes.txt"))
    shapes_df = get_shape_paths(shapes_df)

    routes_df["route_id"] = routes_df["route_id"].astype(str)
    trips_df["route_id"] = trips_df["route_id"].astype(str)
    trips_df["trip_id"] = trips_df["trip_id"].astype(str)
    trips_df = pd.merge(trips_df, routes_df, on='route_id')
    # trips_df["route_color"] = trips_df["route_color"].apply(hex_to_rgb)

    return pd.merge(trips_df, shapes_df, on='shape_id', how='left').fillna("")