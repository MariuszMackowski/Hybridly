from pathlib import Path

from sqlalchemy import func, select

from app.exercises.service import find_by_name
from app.imports.gravitus.importer import import_gravitus
from app.templates.models import WorkoutTemplate
from app.workouts.models import Workout, WorkoutSet
from tests.factories import make_exercise, make_workout

SAMPLE = (Path(__file__).parent / "fixtures" / "gravitus_sample.csv").read_text()


def _count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def _gravitus_workout(db, external_id):
    return db.scalar(select(Workout).where(Workout.external_id == external_id))


def test_import_creates_workouts_sets_in_kg(db_session):
    report = import_gravitus(db_session, SAMPLE)
    assert report.workouts_created == 3
    workout = _gravitus_workout(db_session, "2026-01-03 08:00:00+00:00")
    bench = workout.exercises[0]
    assert bench.exercise.name == "Bench Press"
    assert [float(s.weight_kg) for s in bench.sets] == [20.0, 40.0, 45.0, 20.0]
    assert [s.is_warmup for s in bench.sets] == [True, False, False, False]
    assert workout.ended_at is not None
    assert (workout.ended_at - workout.started_at).total_seconds() == 3000


def test_reimport_skips_existing_workouts(db_session):
    app_workout = make_workout(db_session, make_exercise(db_session, "Leg Extension"), [(30, 10)])
    import_gravitus(db_session, SAMPLE)
    sets_before = _count(db_session, WorkoutSet)
    report = import_gravitus(db_session, SAMPLE)
    assert report.workouts_created == 0
    assert report.workouts_skipped == 3
    assert _count(db_session, WorkoutSet) == sets_before
    db_session.refresh(app_workout)
    assert float(app_workout.exercises[0].sets[0].weight_kg) == 30


def test_unknown_exercise_created_and_reported(db_session):
    text = SAMPLE.replace("Squat,2026-01-07", "Zercher Squat,2026-01-07")
    report = import_gravitus(db_session, text)
    assert report.exercises_created == ["Zercher Squat"]
    assert find_by_name(db_session, "Zercher Squat").primary_muscles == []


def test_existing_template_name_not_duplicated(db_session):
    import_gravitus(db_session, SAMPLE)
    report = import_gravitus(db_session, SAMPLE)
    assert report.templates_created == 0
    assert _count(db_session, WorkoutTemplate) == 1


def test_imported_template_has_default_targets_and_superset(db_session):
    import_gravitus(db_session, SAMPLE)
    template = db_session.scalar(select(WorkoutTemplate))
    assert [(s.sets, s.rep_min, s.rep_max) for s in template.slots] == [(3, 8, 10)] * 3
    assert [s.superset_group for s in template.slots] == [None, 1, 1]


def test_import_marks_prs_chronologically(db_session):
    import_gravitus(db_session, SAMPLE)
    bench = _gravitus_workout(db_session, "2026-01-03 08:00:00+00:00").exercises[0]
    assert [s.is_pr for s in bench.sets] == [False, False, True, False]
