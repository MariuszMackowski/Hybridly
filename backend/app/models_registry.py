"""Import every models module so Base.metadata knows all tables (Alembic, tests)."""

from app.bodyweight.models import BodyweightEntry
from app.exercises.models import Exercise
from app.templates.models import TemplateSlot, WeeklyTemplate, WorkoutTemplate
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet

__all__ = [
    "BodyweightEntry",
    "Exercise",
    "TemplateSlot",
    "WeeklyTemplate",
    "Workout",
    "WorkoutExercise",
    "WorkoutSet",
    "WorkoutTemplate",
]
