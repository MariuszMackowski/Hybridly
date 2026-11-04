from sqlalchemy import func, select

from app.exercises.models import Exercise
from app.exercises.service import find_by_name, upsert_catalog


def _payload(name="Bench Press", **extra):
    return {"name": name, "primary_muscles": ["chest"], **extra}


def test_create_and_list_exercise(client):
    created = client.post("/api/exercises", json=_payload(secondary_muscles=["triceps"]))
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Bench Press"
    assert body["secondary_muscles"] == ["triceps"]
    listed = client.get("/api/exercises").json()
    assert [e["name"] for e in listed] == ["Bench Press"]


def test_duplicate_name_case_insensitive_returns_409(client):
    client.post("/api/exercises", json=_payload())
    response = client.post("/api/exercises", json=_payload(name="bench press"))
    assert response.status_code == 409


def test_rename_keeps_old_name_as_alias(client, db_session):
    exercise_id = client.post("/api/exercises", json=_payload(name="Rusian Twist")).json()["id"]
    response = client.put(f"/api/exercises/{exercise_id}", json=_payload(name="Russian Twist"))
    assert response.status_code == 200
    assert "Rusian Twist" in response.json()["aliases"]
    assert find_by_name(db_session, "rusian twist").id == exercise_id


def test_archived_hidden_by_default(client):
    exercise_id = client.post("/api/exercises", json=_payload()).json()["id"]
    client.post(f"/api/exercises/{exercise_id}/archive")
    assert client.get("/api/exercises").json() == []
    assert len(client.get("/api/exercises?include_archived=true").json()) == 1


def test_unknown_muscle_returns_422(client):
    response = client.post("/api/exercises", json=_payload(primary_muscles=["wings"]))
    assert response.status_code == 422


def test_seed_catalog_is_idempotent(db_session):
    assert upsert_catalog(db_session) == 51
    assert upsert_catalog(db_session) == 0
    assert db_session.scalar(select(func.count()).select_from(Exercise)) == 51


def test_muscles_endpoint_lists_all(client):
    muscles = client.get("/api/muscles").json()
    assert "chest" in muscles and "tibialis" in muscles
