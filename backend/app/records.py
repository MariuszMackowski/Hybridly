"""Running records: best efforts across runs and the latest COROS race predictor."""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, load_only

from app.activities.best_efforts import EFFORTS
from app.activities.models import Activity
from app.coros.models import CorosDaily
from app.db import get_db
from app.time import local_date

router = APIRouter(tags=["records"])


class BestEffort(BaseModel):
    """Fastest segment of one distance and the run it came from."""

    key: str
    distance_m: float
    seconds: int | None
    activity_id: int | None
    day: date | None


class Predictor(BaseModel):
    """COROS fitness assessment snapshot."""

    day: date
    vo2max: int | None
    running_level: int | None
    threshold_pace_s: int | None
    predictions: dict[str, int]


class RecordsOut(BaseModel):
    """Records page payload."""

    bests: list[BestEffort]
    predictor: Predictor | None


def _bests(db: Session) -> list[BestEffort]:
    """Fastest stored effort per standard distance among runs."""
    runs = db.scalars(
        select(Activity)
        .where(Activity.sport == "run")
        .options(load_only(Activity.id, Activity.started_at, Activity.best_efforts))
    ).all()
    out = []
    for key, distance in EFFORTS.items():
        best = min(
            (r for r in runs if key in (r.best_efforts or {})),
            key=lambda r: r.best_efforts[key],
            default=None,
        )
        out.append(
            BestEffort(
                key=key,
                distance_m=distance,
                seconds=best.best_efforts[key] if best else None,
                activity_id=best.id if best else None,
                day=local_date(best.started_at) if best else None,
            )
        )
    return out


def _predictor(db: Session) -> Predictor | None:
    """Latest fitness snapshot synced from COROS."""
    row = db.scalar(
        select(CorosDaily)
        .where(CorosDaily.kind == "fitness", CorosDaily.data.has_key("predictions"))
        .order_by(CorosDaily.day.desc())
        .limit(1)
    )
    if row is None:
        return None
    data = row.data or {}
    return Predictor(
        day=row.day,
        vo2max=data.get("vo2max"),
        running_level=data.get("running_level"),
        threshold_pace_s=data.get("threshold_pace_s"),
        predictions=data.get("predictions") or {},
    )


@router.get("/records", response_model=RecordsOut)
def get_records(db: Session = Depends(get_db)):
    """Best efforts and race predictions."""
    return RecordsOut(bests=_bests(db), predictor=_predictor(db))
