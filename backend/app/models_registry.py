"""Import every models module so Base.metadata knows all tables (Alembic, tests)."""

from app.activities.models import Activity, ActivityLap
from app.bodyweight.models import BodyweightEntry
from app.coros.models import CorosAccount, CorosDaily
from app.exercises.models import Exercise
from app.templates.models import TemplateSlot, WeeklyTemplate, WorkoutTemplate
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet

__all__ = [
    "Activity",
    "ActivityLap",
    "CorosAccount",
    "CorosDaily",
    "BodyweightEntry",
    "Exercise",
    "TemplateSlot",
    "WeeklyTemplate",
    "Workout",
    "WorkoutExercise",
    "WorkoutSet",
    "WorkoutTemplate",
]
