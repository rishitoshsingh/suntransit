from fastapi import APIRouter
from app.config import CITIES
from app.data import postgres as pg

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/cities")
def cities():
    return CITIES


@router.get("/oldest_date/{agency}")
def oldest_date(agency: str):
    return {"oldest_date": pg.oldest_date(agency)}


@router.get("/health")
def health():
    return {"ok": True}
