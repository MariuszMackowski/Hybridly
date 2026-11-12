from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.workouts import service
from app.workouts.insights import WorkoutInsights, workout_insights
from app.workouts.models import Workout
from app.workouts.schemas import WorkoutCreate, WorkoutOut, WorkoutSummary

router = APIRouter(tags=["workouts"])


def _get_or_404(db: Session, workout_id: int) -> Workout:
    """Load a workout or raise 404."""
    workout = service.get_workout(db, workout_id)
    if workout is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workout not found")
    return workout


@router.post("/workouts", response_model=WorkoutOut, status_code=status.HTTP_201_CREATED)
def create_workout(data: WorkoutCreate, response: Response, db: Session = Depends(get_db)):
    """Save a finished workout (idempotent by client_id)."""
    try:
        workout, created = service.create_workout(db, data)
    except service.UnknownExerciseError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown exercise ids: {error}"
        ) from error
    if not created:
        response.status_code = status.HTTP_200_OK
    return service.to_out(workout)


@router.get("/workouts", response_model=list[WorkoutSummary])
def list_workouts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List workouts, newest first."""
    return service.list_summaries(db, limit, offset)


@router.get("/workouts/{workout_id}", response_model=WorkoutOut)
def get_workout(workout_id: int, db: Session = Depends(get_db)):
    """Get one workout with all sets."""
    return service.to_out(_get_or_404(db, workout_id))


@router.get("/workouts/{workout_id}/insights", response_model=WorkoutInsights)
def get_workout_insights(workout_id: int, db: Session = Depends(get_db)):
    """Volume per muscle and each exercise compared with ~4 weeks earlier."""
    return workout_insights(db, _get_or_404(db, workout_id))


@router.delete("/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a workout."""
    service.delete_workout(db, _get_or_404(db, workout_id))
