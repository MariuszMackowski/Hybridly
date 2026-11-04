from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.exercises.catalog import CATALOG
from app.exercises.models import Exercise
from app.exercises.schemas import ExerciseIn


class DuplicateExerciseError(Exception):
    """Raised when a name or alias is already used by another exercise."""


def find_by_name(db: Session, name: str) -> Exercise | None:
    """Find an exercise by name or alias, case-insensitively."""
    needle = name.strip().lower()
    alias_match = func.lower(func.array_to_string(Exercise.aliases, "\x1f")).contains(needle)
    candidates = db.scalars(
        select(Exercise).where(or_(func.lower(Exercise.name) == needle, alias_match))
    ).all()
    for exercise in candidates:
        if exercise.name.lower() == needle or needle in (a.lower() for a in exercise.aliases):
            return exercise
    return None


def _ensure_names_free(db: Session, names: list[str], exclude_id: int | None) -> None:
    """Raise if any of the names belongs to a different exercise."""
    for name in names:
        existing = find_by_name(db, name)
        if existing is not None and existing.id != exclude_id:
            raise DuplicateExerciseError(name)


def _apply(exercise: Exercise, data: ExerciseIn) -> None:
    """Copy validated fields onto the ORM object."""
    for field, value in data.model_dump().items():
        setattr(exercise, field, value)


def list_exercises(db: Session, include_archived: bool = False) -> list[Exercise]:
    """Return exercises sorted by name."""
    query = select(Exercise).order_by(func.lower(Exercise.name))
    if not include_archived:
        query = query.where(Exercise.archived.is_(False))
    return list(db.scalars(query))


def create_exercise(db: Session, data: ExerciseIn) -> Exercise:
    """Create an exercise; name and aliases must be unused."""
    _ensure_names_free(db, [data.name, *data.aliases], exclude_id=None)
    exercise = Exercise()
    _apply(exercise, data)
    db.add(exercise)
    db.commit()
    return exercise


def update_exercise(db: Session, exercise: Exercise, data: ExerciseIn) -> Exercise:
    """Update an exercise; a renamed exercise keeps its old name as an alias."""
    aliases = list(dict.fromkeys(data.aliases))
    if data.name.lower() != exercise.name.lower() and exercise.name not in aliases:
        aliases.append(exercise.name)
    data = data.model_copy(update={"aliases": aliases})
    _ensure_names_free(db, [data.name, *data.aliases], exclude_id=exercise.id)
    _apply(exercise, data)
    db.commit()
    return exercise


def upsert_catalog(db: Session) -> int:
    """Insert catalog exercises that are not present yet; return how many were added."""
    added = 0
    for entry in CATALOG:
        if find_by_name(db, entry.name) is None:
            exercise = Exercise()
            _apply(exercise, entry)
            db.add(exercise)
            db.flush()
            added += 1
    db.commit()
    return added
