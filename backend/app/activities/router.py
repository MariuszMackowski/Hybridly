from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.activities.fit_parser import parse_fit
from app.activities.models import Activity
from app.activities.schemas import ActivityDetail, ActivitySummary, UploadResult
from app.activities.service import store_activity
from app.db import get_db

router = APIRouter(tags=["activities"])
MAX_FIT_BYTES = 20 * 1024 * 1024


def _get_or_404(db: Session, activity_id: int) -> Activity:
    """Load an activity with laps or raise 404."""
    activity = db.scalar(
        select(Activity).where(Activity.id == activity_id).options(selectinload(Activity.laps))
    )
    if activity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found")
    return activity


def _store_upload(db: Session, name: str, data: bytes) -> UploadResult:
    """Parse and store one uploaded file, reporting the outcome instead of raising."""
    if len(data) > MAX_FIT_BYTES:
        return UploadResult(filename=name, status="error", detail="File too large")
    try:
        parsed = parse_fit(data)
        with db.begin_nested():
            activity, created = store_activity(db, parsed, data, "upload")
    except Exception as error:  # noqa: BLE001 — report per file, never fail the whole batch
        return UploadResult(
            filename=name, status="error", detail=str(error) or type(error).__name__
        )
    return UploadResult(filename=name, status="created" if created else "duplicate", id=activity.id)


@router.post("/activities/upload", response_model=list[UploadResult])
async def upload_fit(files: list[UploadFile], db: Session = Depends(get_db)):
    """Import one or more FIT files exported from the watch."""
    results = [_store_upload(db, f.filename or "file.fit", await f.read()) for f in files]
    db.commit()
    return results


@router.get("/activities", response_model=list[ActivitySummary])
def list_activities(
    sport: str | None = None,
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Activities newest first, optionally one sport."""
    query = select(Activity).order_by(Activity.started_at.desc()).limit(limit).offset(offset)
    if sport:
        query = query.where(Activity.sport == sport)
    return list(db.scalars(query))


@router.get("/activities/{activity_id}", response_model=ActivityDetail)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    """One activity with laps and streams."""
    return _get_or_404(db, activity_id)


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: int, db: Session = Depends(get_db)) -> None:
    """Delete an activity and its stored FIT file."""
    activity = _get_or_404(db, activity_id)
    path = Path(activity.fit_path)
    db.delete(activity)
    db.commit()
    path.unlink(missing_ok=True)
