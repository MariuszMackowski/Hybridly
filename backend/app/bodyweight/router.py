from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bodyweight.models import BodyweightEntry
from app.bodyweight.schemas import BodyweightIn, BodyweightOut
from app.db import get_db
from app.workouts.stats import recompute_stats

router = APIRouter(tags=["bodyweight"])


@router.get("/bodyweight", response_model=list[BodyweightOut])
def list_bodyweight(db: Session = Depends(get_db)):
    """List bodyweight entries, newest first."""
    return list(db.scalars(select(BodyweightEntry).order_by(BodyweightEntry.day.desc())))


@router.put("/bodyweight/{day}", response_model=BodyweightOut)
def put_bodyweight(day: date, data: BodyweightIn, db: Session = Depends(get_db)):
    """Create or update the bodyweight for a day and refresh bodyweight-exercise stats."""
    entry = db.get(BodyweightEntry, day) or BodyweightEntry(day=day)
    entry.kg = data.kg
    db.add(entry)
    db.flush()
    recompute_stats(db, bodyweight_only=True)
    db.commit()
    return entry
