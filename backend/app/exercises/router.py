from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.exercises import service
from app.exercises.models import Exercise
from app.exercises.schemas import ExerciseIn, ExerciseOut
from app.muscles import Muscle
from app.progression.context import ExerciseContext, build_context

router = APIRouter(tags=["exercises"])


def get_exercise_or_404(db: Session, exercise_id: int) -> Exercise:
    """Load an exercise or raise 404."""
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercise not found")
    return exercise


def _conflict(error: service.DuplicateExerciseError) -> HTTPException:
    """Translate a duplicate-name error into HTTP 409."""
    return HTTPException(status.HTTP_409_CONFLICT, f"Name already used: {error}")


@router.get("/muscles")
def list_muscles() -> list[str]:
    """List all muscle identifiers."""
    return [m.value for m in Muscle]


@router.get("/exercises", response_model=list[ExerciseOut])
def list_exercises(include_archived: bool = False, db: Session = Depends(get_db)):
    """List exercises, archived ones only on request."""
    return service.list_exercises(db, include_archived)


@router.post("/exercises", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
def create_exercise(data: ExerciseIn, db: Session = Depends(get_db)):
    """Create an exercise."""
    try:
        return service.create_exercise(db, data)
    except service.DuplicateExerciseError as error:
        raise _conflict(error) from error


@router.put("/exercises/{exercise_id}", response_model=ExerciseOut)
def update_exercise(exercise_id: int, data: ExerciseIn, db: Session = Depends(get_db)):
    """Replace an exercise's fields."""
    exercise = get_exercise_or_404(db, exercise_id)
    try:
        return service.update_exercise(db, exercise, data)
    except service.DuplicateExerciseError as error:
        raise _conflict(error) from error


@router.get("/exercises/{exercise_id}/context", response_model=ExerciseContext)
def exercise_context(
    exercise_id: int,
    sets: int = Query(3, ge=1, le=20),
    rep_min: int = Query(8, ge=1, le=100),
    rep_max: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Previous session and suggestions for the workout logger."""
    exercise = get_exercise_or_404(db, exercise_id)
    return build_context(db, exercise, sets, rep_min, max(rep_min, rep_max))


@router.post("/exercises/{exercise_id}/archive", response_model=ExerciseOut)
def archive_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """Hide an exercise from pickers without deleting its history."""
    exercise = get_exercise_or_404(db, exercise_id)
    exercise.archived = True
    db.commit()
    return exercise
