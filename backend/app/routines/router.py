from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.routines import service
from app.routines.models import Routine, RoutineLog, RoutineWeekday, Video

router = APIRouter(tags=["routines"])


class VideoIn(BaseModel):
    """New library video."""

    url: str = Field(min_length=8)
    note: str | None = None


class VideoOut(BaseModel):
    """Library video."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    youtube_id: str | None
    title: str
    thumbnail_url: str | None
    note: str | None


class RoutineIn(BaseModel):
    """Routine fields; video order is the display order."""

    name: str = Field(min_length=1)
    note: str | None = None
    video_ids: list[int] = []


class RoutineOut(BaseModel):
    """Routine with resolved videos."""

    id: int
    name: str
    note: str | None
    video_ids: list[int]
    videos: list[VideoOut]


class WeekdayRoutines(BaseModel):
    """Routines suggested on one weekday."""

    weekday: int = Field(ge=0, le=6)
    routine_ids: list[int]


def routine_out(db: Session, routine: Routine) -> RoutineOut:
    """Routine with its videos in the stored order."""
    videos = {v.id: v for v in db.scalars(select(Video).where(Video.id.in_(routine.video_ids)))}
    return RoutineOut(
        id=routine.id,
        name=routine.name,
        note=routine.note,
        video_ids=routine.video_ids,
        videos=[VideoOut.model_validate(videos[i]) for i in routine.video_ids if i in videos],
    )


def routines_for_weekday(db: Session, weekday: int) -> list[Routine]:
    """Active routines assigned to a weekday."""
    return list(
        db.scalars(
            select(Routine)
            .join(RoutineWeekday, RoutineWeekday.routine_id == Routine.id)
            .where(RoutineWeekday.weekday == weekday, Routine.archived.is_(False))
            .order_by(Routine.name)
        )
    )


def done_on(db: Session, day: date) -> set[int]:
    """Ids of routines ticked on a day."""
    return set(db.scalars(select(RoutineLog.routine_id).where(RoutineLog.day == day)))


@router.get("/videos", response_model=list[VideoOut])
def list_videos(db: Session = Depends(get_db)):
    """Video library."""
    return list(db.scalars(select(Video).order_by(Video.title)))


@router.post("/videos", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
def add_video(data: VideoIn, db: Session = Depends(get_db)):
    """Add a YouTube link; title and thumbnail come from oEmbed when available."""
    title, thumbnail = service.fetch_oembed(data.url)
    video = Video(
        url=data.url.strip(),
        youtube_id=service.youtube_id(data.url),
        title=title,
        thumbnail_url=thumbnail,
        note=data.note,
    )
    db.add(video)
    db.commit()
    return video


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: int, db: Session = Depends(get_db)) -> None:
    """Remove a video (and from every routine)."""
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    for routine in db.scalars(select(Routine)):
        if video_id in routine.video_ids:
            routine.video_ids = [i for i in routine.video_ids if i != video_id]
    db.delete(video)
    db.commit()


@router.get("/routines", response_model=list[RoutineOut])
def list_routines(db: Session = Depends(get_db)):
    """Active routines."""
    routines = db.scalars(select(Routine).where(Routine.archived.is_(False)).order_by(Routine.name))
    return [routine_out(db, r) for r in routines]


def _save(db: Session, routine: Routine, data: RoutineIn) -> RoutineOut:
    """Write fields and return the serialized routine."""
    routine.name, routine.note, routine.video_ids = data.name, data.note, data.video_ids
    db.add(routine)
    db.commit()
    return routine_out(db, routine)


@router.post("/routines", response_model=RoutineOut, status_code=status.HTTP_201_CREATED)
def create_routine(data: RoutineIn, db: Session = Depends(get_db)):
    """Create a routine."""
    return _save(db, Routine(), data)


@router.get("/routines/week", response_model=list[WeekdayRoutines])
def get_week(db: Session = Depends(get_db)):
    """Routine ids per weekday, Monday first."""
    rows = db.scalars(select(RoutineWeekday)).all()
    return [
        WeekdayRoutines(weekday=d, routine_ids=sorted(r.routine_id for r in rows if r.weekday == d))
        for d in range(7)
    ]


@router.put("/routines/week", response_model=list[WeekdayRoutines])
def put_week(items: list[WeekdayRoutines], db: Session = Depends(get_db)):
    """Replace assignments for the given weekdays."""
    for item in items:
        db.execute(delete(RoutineWeekday).where(RoutineWeekday.weekday == item.weekday))
        for routine_id in dict.fromkeys(item.routine_ids):
            db.add(RoutineWeekday(weekday=item.weekday, routine_id=routine_id))
    db.commit()
    return get_week(db)


@router.get("/routines/done", response_model=list[int])
def get_done(day: date, db: Session = Depends(get_db)):
    """Routines ticked on a day."""
    return sorted(done_on(db, day))


@router.put("/routines/{routine_id}", response_model=RoutineOut)
def update_routine(routine_id: int, data: RoutineIn, db: Session = Depends(get_db)):
    """Update a routine."""
    routine = db.get(Routine, routine_id)
    if routine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routine not found")
    return _save(db, routine, data)


@router.post("/routines/{routine_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_routine(routine_id: int, db: Session = Depends(get_db)) -> None:
    """Hide a routine and drop it from the week."""
    routine = db.get(Routine, routine_id)
    if routine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routine not found")
    routine.archived = True
    db.execute(delete(RoutineWeekday).where(RoutineWeekday.routine_id == routine_id))
    db.commit()


@router.put("/routines/{routine_id}/done/{day}", status_code=status.HTTP_204_NO_CONTENT)
def mark_done(routine_id: int, day: date, db: Session = Depends(get_db)) -> Response:
    """Tick a routine as done on a day."""
    if db.get(RoutineLog, (day, routine_id)) is None:
        db.add(RoutineLog(day=day, routine_id=routine_id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/routines/{routine_id}/done/{day}", status_code=status.HTTP_204_NO_CONTENT)
def unmark_done(routine_id: int, day: date, db: Session = Depends(get_db)) -> None:
    """Untick a routine."""
    db.execute(delete(RoutineLog).where(RoutineLog.day == day, RoutineLog.routine_id == routine_id))
    db.commit()
