from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.templates import service
from app.templates.models import WeeklyTemplate, WorkoutTemplate
from app.templates.schemas import TemplateIn, TemplateOut, TodayOut, WeekItem
from app.time import local_today, utc_now
from app.today import TodayExtras, build_today

router = APIRouter(tags=["templates"])


def _get_or_404(db: Session, template_id: int) -> WorkoutTemplate:
    """Load a template or raise 404."""
    template = service.get_template(db, template_id)
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return template


def _save(db: Session, template: WorkoutTemplate, data: TemplateIn) -> TemplateOut:
    """Save and serialize, mapping validation problems to HTTP 422."""
    try:
        return service.to_out(db, service.save_template(db, template, data))
    except service.TemplateError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    """List active templates."""
    return [service.to_out(db, t) for t in service.list_templates(db)]


@router.get("/templates/{template_id}", response_model=TemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get one template."""
    return service.to_out(db, _get_or_404(db, template_id))


@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(data: TemplateIn, db: Session = Depends(get_db)):
    """Create a template."""
    return _save(db, WorkoutTemplate(), data)


@router.put("/templates/{template_id}", response_model=TemplateOut)
def update_template(template_id: int, data: TemplateIn, db: Session = Depends(get_db)):
    """Replace a template's fields and slots."""
    return _save(db, _get_or_404(db, template_id), data)


@router.post("/templates/{template_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_template(template_id: int, db: Session = Depends(get_db)) -> None:
    """Archive a template and clear it from the week."""
    service.archive_template(db, _get_or_404(db, template_id))


@router.get("/week", response_model=list[WeekItem])
def get_week(db: Session = Depends(get_db)):
    """Weekly template plan, Monday first."""
    return service.get_week(db)


@router.put("/week", response_model=list[WeekItem])
def put_week(items: list[WeekItem], db: Session = Depends(get_db)):
    """Update weekday assignments."""
    service.set_week(db, items)
    return service.get_week(db)


class TodayFull(TodayOut, TodayExtras):
    """Today: strength template plus plan, routines and recovery."""


@router.get("/today", response_model=TodayFull)
def today(db: Session = Depends(get_db)):
    """Today's date (Europe/Warsaw) and the template planned for it."""
    day = local_today(utc_now())
    row = db.get(WeeklyTemplate, day.weekday())
    template = None
    if row and row.template_id:
        loaded = service.get_template(db, row.template_id)
        template = service.to_out(db, loaded) if loaded else None
    extras = build_today(db, day)
    return TodayFull(date=day, weekday=day.weekday(), template=template, **dict(extras))
