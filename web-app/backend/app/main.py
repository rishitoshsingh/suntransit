import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import ALLOWED_ORIGINS
from app.routers import live, delays, trends, hourly, meta, h3

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SunTransit API")

# Path to the built frontend (populated by `vite build` / the Docker image).
_FRONTEND_DIST = os.getenv(
    "FRONTEND_DIST",
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"),
)

# Which sites may call the API from a browser. Defaults to "*" for dev; set
# ALLOWED_ORIGINS to your real domain in production (hardening B6).
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(meta.router)
app.include_router(live.router)
app.include_router(delays.router)
app.include_router(trends.router)
app.include_router(hourly.router)
app.include_router(h3.router)


@app.get("/api")
def root():
    return {"service": "suntransit", "status": "ok"}


# Serve the built single-page app (if present). API/WS routes are registered
# above, so this only catches everything else and falls back to index.html.
if os.path.isdir(_FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = os.path.join(_FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))
