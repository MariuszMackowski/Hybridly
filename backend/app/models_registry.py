"""Import every models module so Base.metadata knows all tables (Alembic, tests)."""

from app.activities.models import Activity, ActivityLap
from app.bodyweight.models import BodyweightEntry
from app.coros.models import CorosAccount, CorosDaily
from app.exercises.models import Exercise
from app.plans.models import PlanSession, PlanWeek, TrainingPlan
from app.routines.models import Routine, RoutineLog, RoutineWeekday, Video
from app.strava.models import StravaAccount
from app.templates.models import TemplateSlot, WeeklyTemplate, WorkoutTemplate
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet

__all__ = [
    "Activity",
    "ActivityLap",
    "CorosAccount",
    "CorosDaily",
    "BodyweightEntry",
    "Exercise",
    "PlanSession",
    "PlanWeek",
    "Routine",
    "RoutineLog",
    "RoutineWeekday",
    "StravaAccount",
    "TrainingPlan",
    "Video",
    "TemplateSlot",
    "WeeklyTemplate",
    "Workout",
    "WorkoutExercise",
    "WorkoutSet",
    "WorkoutTemplate",
]
