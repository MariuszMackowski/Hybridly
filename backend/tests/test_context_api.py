from datetime import UTC, datetime

from tests.factories import make_exercise, make_workout

DAY1 = datetime(2026, 10, 1, 7, 0, tzinfo=UTC)
DAY2 = datetime(2026, 10, 3, 7, 0, tzinfo=UTC)


def test_context_without_history(client, db_session):
    exercise = make_exercise(db_session)
    body = client.get(f"/api/exercises/{exercise.id}/context").json()
    assert body["previous"] is None
    assert body["suggestions"] == []
    assert body["exercise"]["name"] == "Bench Press"


def test_context_returns_last_session_sets(client, db_session):
    exercise = make_exercise(db_session)
    make_workout(db_session, exercise, [(40, 8)], started_at=DAY1)
    latest = make_workout(db_session, exercise, [(45, 8), (45, 7)], started_at=DAY2)
    body = client.get(f"/api/exercises/{exercise.id}/context").json()
    assert body["previous"]["workout_id"] == latest.id
    assert [(s["weight_kg"], s["reps"]) for s in body["previous"]["sets"]] == [(45, 8), (45, 7)]


def test_context_suggests_increase_when_top_of_range(client, db_session):
    exercise = make_exercise(db_session)
    make_workout(db_session, exercise, [(60, 8)] * 2)
    body = client.get(f"/api/exercises/{exercise.id}/context?sets=2&rep_min=6&rep_max=8").json()
    assert (
        body["suggestions"]
        == [{"weight_kg": 62.5, "reps": 6, "kind": "increase", "reason": None}] * 2
    )


def test_context_for_time_exercise_has_no_suggestions(client, db_session):
    exercise = make_exercise(db_session, "Dead Hang", measure="time")
    make_workout(db_session, exercise, [(None, None, 45)])
    body = client.get(f"/api/exercises/{exercise.id}/context").json()
    assert body["previous"]["sets"][0]["seconds"] == 45
    assert body["suggestions"] == []


def test_context_ignores_warmup_sets_for_suggestions(client, db_session):
    exercise = make_exercise(db_session)
    make_workout(db_session, exercise, [(20, 10, None, True), (60, 8)])
    body = client.get(f"/api/exercises/{exercise.id}/context?sets=1&rep_min=6&rep_max=8").json()
    assert body["previous"]["sets"][0]["is_warmup"] is True
    assert body["suggestions"] == [
        {"weight_kg": 62.5, "reps": 6, "kind": "increase", "reason": None}
    ]


def test_context_404_for_unknown_exercise(client):
    assert client.get("/api/exercises/999999/context").status_code == 404


def test_fatigued_muscle_turns_increase_into_hold(client, db_session, monkeypatch):
    from datetime import timedelta

    import app.load.service as load_service
    from app.workouts.stats import recompute_stats

    now = datetime(2026, 10, 10, 12, tzinfo=UTC)
    monkeypatch.setattr(load_service, "utc_now", lambda: now)
    bench = make_exercise(db_session, "Bench Press")
    flyes = make_exercise(db_session, "Dumbbell Fly")
    make_workout(db_session, bench, [(60, 8)] * 2, started_at=now - timedelta(days=4))
    make_workout(db_session, flyes, [(20, 12)] * 8, started_at=now - timedelta(hours=1))
    recompute_stats(db_session)
    db_session.commit()
    body = client.get(f"/api/exercises/{bench.id}/context?sets=2&rep_min=6&rep_max=8").json()
    assert (
        body["suggestions"]
        == [{"weight_kg": 60, "reps": 8, "kind": "hold", "reason": "fatigued"}] * 2
    )


def test_fresh_muscle_keeps_increase(client, db_session, monkeypatch):
    import app.load.service as load_service

    monkeypatch.setattr(load_service, "utc_now", lambda: datetime(2026, 10, 10, 12, tzinfo=UTC))
    bench = make_exercise(db_session)
    make_workout(db_session, bench, [(60, 8)], started_at=DAY1)
    db_session.commit()
    body = client.get(f"/api/exercises/{bench.id}/context?sets=1&rep_min=6&rep_max=8").json()
    assert body["suggestions"][0]["kind"] == "increase"
    assert body["suggestions"][0]["reason"] is None
