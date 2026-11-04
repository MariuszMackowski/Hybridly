from datetime import UTC, datetime

import app.templates.router as templates_router
from tests.factories import make_exercise


def _template(name, *exercise_ids, **extra):
    return {
        "name": name,
        "slots": [
            {"exercise_id": eid, "sets": 3, "rep_min": 8, "rep_max": 10} for eid in exercise_ids
        ],
        **extra,
    }


def test_create_template_with_slots_in_order(client, db_session):
    bench = make_exercise(db_session, "Bench Press")
    row = make_exercise(db_session, "Barbell Row")
    body = {
        "name": "Upper A",
        "slots": [
            {
                "exercise_id": bench.id,
                "alternative_exercise_ids": [row.id],
                "warmup_sets": 2,
                "sets": 4,
                "rep_min": 6,
                "rep_max": 8,
            },
            {"exercise_id": row.id, "sets": 3, "rep_min": 10, "rep_max": 12},
        ],
    }
    created = client.post("/api/templates", json=body)
    assert created.status_code == 201
    slots = created.json()["slots"]
    assert [s["exercise_name"] for s in slots] == ["Bench Press", "Barbell Row"]
    assert [s["position"] for s in slots] == [0, 1]
    assert slots[0]["alternatives"] == [{"id": row.id, "name": "Barbell Row"}]
    assert slots[0]["warmup_sets"] == 2


def test_put_replaces_slots(client, db_session):
    bench = make_exercise(db_session, "Bench Press")
    row = make_exercise(db_session, "Barbell Row")
    template_id = client.post("/api/templates", json=_template("Upper A", bench.id)).json()["id"]
    response = client.put(f"/api/templates/{template_id}", json=_template("Upper A", row.id))
    assert [s["exercise_name"] for s in response.json()["slots"]] == ["Barbell Row"]


def test_rep_max_below_min_returns_422(client, db_session):
    bench = make_exercise(db_session)
    body = {
        "name": "X",
        "slots": [{"exercise_id": bench.id, "sets": 3, "rep_min": 10, "rep_max": 8}],
    }
    assert client.post("/api/templates", json=body).status_code == 422


def test_archive_removes_from_week(client, db_session):
    bench = make_exercise(db_session)
    template_id = client.post("/api/templates", json=_template("Upper A", bench.id)).json()["id"]
    client.put("/api/week", json=[{"weekday": 0, "template_id": template_id}])
    client.post(f"/api/templates/{template_id}/archive")
    assert client.get("/api/week").json()[0]["template_id"] is None
    assert client.get("/api/templates").json() == []


def test_week_roundtrip(client, db_session):
    bench = make_exercise(db_session)
    template_id = client.post("/api/templates", json=_template("Lower", bench.id)).json()["id"]
    client.put("/api/week", json=[{"weekday": 1, "template_id": template_id}])
    week = client.get("/api/week").json()
    assert len(week) == 7
    assert week[1] == {"weekday": 1, "template_id": template_id, "template_name": "Lower"}
    assert week[0]["template_id"] is None


def test_today_uses_warsaw_date(client, db_session, monkeypatch):
    bench = make_exercise(db_session)
    template_id = client.post("/api/templates", json=_template("Lower", bench.id)).json()["id"]
    client.put("/api/week", json=[{"weekday": 1, "template_id": template_id}])
    monkeypatch.setattr(
        templates_router, "utc_now", lambda: datetime(2026, 11, 9, 23, 30, tzinfo=UTC)
    )
    body = client.get("/api/today").json()
    assert body["date"] == "2026-11-10"
    assert body["weekday"] == 1
    assert body["template"]["name"] == "Lower"
