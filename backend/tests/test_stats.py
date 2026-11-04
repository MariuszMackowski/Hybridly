from datetime import UTC, date, datetime
from decimal import Decimal

from app.bodyweight.models import BodyweightEntry
from app.progression.e1rm import estimate_1rm
from app.workouts.stats import recompute_stats
from tests.factories import make_exercise, make_workout

DAY1 = datetime(2026, 10, 1, 7, 0, tzinfo=UTC)
DAY2 = datetime(2026, 10, 3, 7, 0, tzinfo=UTC)


def _sets(workout):
    return workout.exercises[0].sets


def test_e1rm_computed_for_reps_sets(db_session):
    workout = make_workout(db_session, make_exercise(db_session), [(40, 10)])
    recompute_stats(db_session)
    assert _sets(workout)[0].e1rm_kg == Decimal("53.33")


def test_first_set_is_not_pr_later_better_is_pr(db_session):
    exercise = make_exercise(db_session)
    first = make_workout(db_session, exercise, [(40, 8)], started_at=DAY1)
    second = make_workout(db_session, exercise, [(42.5, 8)], started_at=DAY2)
    recompute_stats(db_session)
    assert _sets(first)[0].is_pr is False
    assert _sets(second)[0].is_pr is True


def test_equal_e1rm_is_not_pr(db_session):
    exercise = make_exercise(db_session)
    make_workout(db_session, exercise, [(40, 8)], started_at=DAY1)
    second = make_workout(db_session, exercise, [(40, 8)], started_at=DAY2)
    recompute_stats(db_session)
    assert _sets(second)[0].is_pr is False


def test_bodyweight_exercise_uses_bodyweight_plus_added(db_session):
    db_session.add(BodyweightEntry(day=date(2026, 9, 1), kg=80))
    exercise = make_exercise(db_session, "Pull-Up", is_bodyweight=True)
    workout = make_workout(db_session, exercise, [(10, 5)])
    recompute_stats(db_session)
    assert float(_sets(workout)[0].e1rm_kg) == estimate_1rm(90, 5)


def test_bodyweight_exercise_without_entry_has_null_e1rm(db_session):
    exercise = make_exercise(db_session, "Pull-Up", is_bodyweight=True)
    workout = make_workout(db_session, exercise, [(0, 5)])
    recompute_stats(db_session)
    assert _sets(workout)[0].e1rm_kg is None


def test_time_set_has_null_e1rm(db_session):
    exercise = make_exercise(db_session, "Dead Hang", measure="time")
    workout = make_workout(db_session, exercise, [(None, None, 45)])
    recompute_stats(db_session)
    assert _sets(workout)[0].e1rm_kg is None


def test_warmup_set_has_null_e1rm_and_no_pr(db_session):
    exercise = make_exercise(db_session)
    make_workout(db_session, exercise, [(40, 8)], started_at=DAY1)
    second = make_workout(db_session, exercise, [(100, 5, None, True)], started_at=DAY2)
    recompute_stats(db_session)
    assert _sets(second)[0].e1rm_kg is None
    assert _sets(second)[0].is_pr is False


def test_toggling_bodyweight_flag_recomputes(client, db_session):
    db_session.add(BodyweightEntry(day=date(2026, 9, 1), kg=80))
    exercise = make_exercise(db_session, "Dip")
    workout = make_workout(db_session, exercise, [(0, 8)])
    recompute_stats(db_session)
    body = {"name": "Dip", "primary_muscles": ["chest"], "is_bodyweight": True}
    assert client.put(f"/api/exercises/{exercise.id}", json=body).status_code == 200
    db_session.refresh(_sets(workout)[0])
    assert float(_sets(workout)[0].e1rm_kg) == estimate_1rm(80, 8)


def test_put_bodyweight_recomputes(client, db_session):
    exercise = make_exercise(db_session, "Pull-Up", is_bodyweight=True)
    workout = make_workout(db_session, exercise, [(0, 5)])
    response = client.put("/api/bodyweight/2026-10-01", json={"kg": 80})
    assert response.status_code == 200
    db_session.refresh(_sets(workout)[0])
    assert float(_sets(workout)[0].e1rm_kg) == estimate_1rm(80, 5)
