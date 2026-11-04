import uuid

from sqlalchemy import func, select

from app.workouts.models import Workout
from tests.factories import make_exercise


def _payload(exercise_id, sets, started_at="2026-11-02T07:00:00Z", client_id=None):
    return {
        "client_id": str(client_id or uuid.uuid4()),
        "started_at": started_at,
        "ended_at": None,
        "exercises": [{"exercise_id": exercise_id, "sets": sets}],
    }


def test_create_workout_returns_sets_with_e1rm(client, db_session):
    exercise = make_exercise(db_session)
    response = client.post(
        "/api/workouts",
        json=_payload(
            exercise.id,
            [{"weight_kg": 20, "reps": 10, "is_warmup": True}, {"weight_kg": 40, "reps": 10}],
        ),
    )
    assert response.status_code == 201
    sets = response.json()["exercises"][0]["sets"]
    assert sets[0]["e1rm_kg"] is None and sets[0]["is_warmup"] is True
    assert sets[1]["e1rm_kg"] == 53.33
    assert response.json()["exercises"][0]["exercise_name"] == "Bench Press"


def test_create_workout_is_idempotent_by_client_id(client, db_session):
    exercise = make_exercise(db_session)
    payload = _payload(exercise.id, [{"weight_kg": 40, "reps": 8}])
    first = client.post("/api/workouts", json=payload)
    second = client.post("/api/workouts", json=payload)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert db_session.scalar(select(func.count()).select_from(Workout)) == 1


def test_set_needs_reps_or_seconds(client, db_session):
    exercise = make_exercise(db_session)
    response = client.post("/api/workouts", json=_payload(exercise.id, [{"weight_kg": 40}]))
    assert response.status_code == 422


def test_unknown_exercise_returns_422(client):
    response = client.post("/api/workouts", json=_payload(999999, [{"weight_kg": 40, "reps": 5}]))
    assert response.status_code == 422


def test_list_is_newest_first_with_counts(client, db_session):
    exercise = make_exercise(db_session)
    client.post(
        "/api/workouts",
        json=_payload(
            exercise.id, [{"weight_kg": 40, "reps": 8}], started_at="2026-11-01T07:00:00Z"
        ),
    )
    client.post(
        "/api/workouts",
        json=_payload(
            exercise.id,
            [{"weight_kg": 45, "reps": 8}, {"weight_kg": 45, "reps": 7}],
            started_at="2026-11-03T07:00:00Z",
        ),
    )
    items = client.get("/api/workouts").json()
    assert [i["set_count"] for i in items] == [2, 1]
    assert items[0]["exercise_count"] == 1
    assert items[0]["pr_count"] == 1


def test_delete_recomputes_pr(client, db_session):
    exercise = make_exercise(db_session)
    client.post(
        "/api/workouts",
        json=_payload(
            exercise.id, [{"weight_kg": 40, "reps": 8}], started_at="2026-11-01T07:00:00Z"
        ),
    )
    middle = client.post(
        "/api/workouts",
        json=_payload(
            exercise.id, [{"weight_kg": 50, "reps": 8}], started_at="2026-11-02T07:00:00Z"
        ),
    ).json()
    last = client.post(
        "/api/workouts",
        json=_payload(
            exercise.id, [{"weight_kg": 45, "reps": 8}], started_at="2026-11-03T07:00:00Z"
        ),
    ).json()
    assert last["exercises"][0]["sets"][0]["is_pr"] is False
    assert client.delete(f"/api/workouts/{middle['id']}").status_code == 204
    refreshed = client.get(f"/api/workouts/{last['id']}").json()
    assert refreshed["exercises"][0]["sets"][0]["is_pr"] is True
