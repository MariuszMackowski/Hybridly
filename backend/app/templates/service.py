from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.exercises.models import Exercise
from app.templates.models import TemplateSlot, WeeklyTemplate, WorkoutTemplate
from app.templates.schemas import ExerciseRef, SlotOut, TemplateIn, TemplateOut, WeekItem


class TemplateError(Exception):
    """Invalid template payload (unknown exercise or duplicate name)."""


def get_template(db: Session, template_id: int) -> WorkoutTemplate | None:
    """Load a template with its slots."""
    return db.scalar(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.id == template_id)
        .options(selectinload(WorkoutTemplate.slots).selectinload(TemplateSlot.exercise))
    )


def list_templates(db: Session) -> list[WorkoutTemplate]:
    """Active templates sorted by name."""
    return list(
        db.scalars(
            select(WorkoutTemplate)
            .where(WorkoutTemplate.archived.is_(False))
            .order_by(WorkoutTemplate.name)
            .options(selectinload(WorkoutTemplate.slots).selectinload(TemplateSlot.exercise))
        )
    )


def save_template(db: Session, template: WorkoutTemplate, data: TemplateIn) -> WorkoutTemplate:
    """Write fields and replace all slots (positions follow list order)."""
    ids = {s.exercise_id for s in data.slots}
    ids |= {a for s in data.slots for a in s.alternative_exercise_ids}
    known = set(db.scalars(select(Exercise.id).where(Exercise.id.in_(ids))))
    if missing := ids - known:
        raise TemplateError(f"Unknown exercise ids: {sorted(missing)}")
    clash = db.scalar(
        select(WorkoutTemplate.id).where(
            WorkoutTemplate.name == data.name, WorkoutTemplate.id != template.id
        )
    )
    if clash is not None:
        raise TemplateError(f"Template name already used: {data.name}")
    template.name = data.name
    template.note = data.note
    template.warmup_items = data.warmup_items
    template.cooldown_items = data.cooldown_items
    template.slots = [
        TemplateSlot(position=i, **slot.model_dump()) for i, slot in enumerate(data.slots)
    ]
    db.add(template)
    db.commit()
    return get_template(db, template.id)


def archive_template(db: Session, template: WorkoutTemplate) -> None:
    """Hide a template and remove it from the weekly plan."""
    template.archived = True
    for item in db.scalars(select(WeeklyTemplate).where(WeeklyTemplate.template_id == template.id)):
        item.template_id = None
    db.commit()


def to_out(db: Session, template: WorkoutTemplate) -> TemplateOut:
    """Serialize a template, resolving exercise names for slots and alternatives."""
    alt_ids = {a for s in template.slots for a in s.alternative_exercise_ids}
    names = dict(
        db.execute(select(Exercise.id, Exercise.name).where(Exercise.id.in_(alt_ids))).all()
    )
    return TemplateOut(
        id=template.id,
        name=template.name,
        note=template.note,
        archived=template.archived,
        warmup_items=template.warmup_items,
        cooldown_items=template.cooldown_items,
        slots=[
            SlotOut(
                block=s.block,
                exercise_id=s.exercise_id,
                alternative_exercise_ids=s.alternative_exercise_ids,
                warmup_sets=s.warmup_sets,
                sets=s.sets,
                rep_min=s.rep_min,
                rep_max=s.rep_max,
                superset_group=s.superset_group,
                note=s.note,
                position=s.position,
                exercise_name=s.exercise.name,
                alternatives=[
                    ExerciseRef(id=a, name=names[a])
                    for a in s.alternative_exercise_ids
                    if a in names
                ],
            )
            for s in template.slots
        ],
    )


def get_week(db: Session) -> list[WeekItem]:
    """All seven weekdays with their suggested template (if any)."""
    rows = {
        w.weekday: w
        for w in db.scalars(select(WeeklyTemplate).options(selectinload(WeeklyTemplate.template)))
    }
    items = []
    for day in range(7):
        row = rows.get(day)
        template = row.template if row and row.template_id else None
        items.append(
            WeekItem(
                weekday=day,
                template_id=template.id if template else None,
                template_name=template.name if template else None,
            )
        )
    return items


def set_week(db: Session, items: list[WeekItem]) -> None:
    """Upsert weekday assignments."""
    for item in items:
        row = db.get(WeeklyTemplate, item.weekday) or WeeklyTemplate(weekday=item.weekday)
        row.template_id = item.template_id
        db.add(row)
    db.commit()
