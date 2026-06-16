"""H3 hexagon delay heatmap — stop delays binned onto Uber's H3 grid."""
from fastapi import APIRouter, HTTPException, Query
from app.config import CITIES, H3_RESOLUTIONS
from app.data import postgres as pg
from app.data.h3util import cell_boundary, cell_center, fill_h3_gaps

router = APIRouter(prefix="/api", tags=["h3"])

FIXED_MAX = 600  # ±10 min fixed colour scale (seconds)


def _agency(city: str) -> str:
    if city not in CITIES:
        raise HTTPException(400, f"Unknown city: {city}")
    return CITIES[city]["agency"]


@router.get("/h3_delays/{city}/{res}")
def h3_delays(city: str, res: int, hour: int | None = Query(default=None, ge=0, le=23)):
    agency = _agency(city)
    if res not in H3_RESOLUTIONS:
        raise HTTPException(400, f"Unsupported resolution {res}; choose one of {H3_RESOLUTIONS}")

    df = pg.h3_delays(agency, res, hour)
    if df.empty:
        return {"resolution": res, "cells": []}

    records = df[["h3_index", "mean_delay", "total_trips"]].to_dict("records")
    filled = fill_h3_gaps(records)

    cells = []
    for cell in filled:
        idx = cell["h3_index"]
        interpolated = cell.get("interpolated", False)
        d = cell["mean_delay"]
        cells.append({
            "h3_index": idx,
            "interpolated": interpolated,
            "mean_delay": round(float(d), 2) if not interpolated else None,
            "total_trips": int(cell["total_trips"]),
            "scaled_delay": max(0.0, min(1.0, 0.5 + d / (2 * FIXED_MAX))) if not interpolated else None,
            "boundary": cell_boundary(idx),
            "center": cell_center(idx),
        })

    return {"resolution": res, "hour": hour, "cells": cells}
