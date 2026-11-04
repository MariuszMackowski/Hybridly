from datetime import UTC, datetime, timedelta

import pytest

import app.load.service as load_service
from app.workouts.stats import recompute_stats
from tests.factories import make_activity, make_exercise, make_workout

NOW = datetime(2026, 1, 10, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    monkeypatch.setattr(load_service, "utc_now", lambda: NOW)


def test_recovery_without_training_is_full(client):
    body = client.get("/api/recovery").json()
    assert body["recovery_pct"] == 100
    assert body["muscles"] == {}
    assert len(body["daily"]) == 14


def test_recent_gym_and_run_lower_recovery_and_color_muscles(client, db_session):
    bench = make_exercise(db_session, "Bench Press", load_factor=1.5, secondary_muscles=["triceps"])
    make_workout(db_session, bench, [(60, 8)] * 5, started_at=NOW - timedelta(hours=2))
    make_activity(db_session, NOW - timedelta(hours=20), distance_m=8000)
    recompute_stats(db_session)
    db_session.commit()
    body = client.get("/api/recovery").json()
    assert body["recovery_pct"] < 80
    assert body["muscles"]["chest"] > body["muscles"]["triceps"] > 0
    assert body["muscles"]["quads"] > 0
    today = body["daily"][-1]
    assert today["strength"] > 0


def test_warmups_do_not_add_load(client, db_session):
    bench = make_exercise(db_session, "Bench Press")
    make_workout(db_session, bench, [(20, 10, None, True)] * 3, started_at=NOW - timedelta(hours=1))
    recompute_stats(db_session)
    db_session.commit()
    assert client.get("/api/recovery").json()["recovery_pct"] == 100
