from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.activities.models import Activity
from app.coros.models import CorosAccount
from app.coros.sync import run_sync
from tests.fitgen import START, make_fit
from tests.test_coros_sync import FakeClient


@pytest.fixture(autouse=True)
def fit_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.activities.service.get_settings", lambda: type("S", (), {"fit_dir": str(tmp_path)})()
    )
    return tmp_path


def _upload(client, *files):
    return client.post(
        "/api/activities/upload",
        files=[("files", (name, data, "application/octet-stream")) for name, data in files],
    )


def test_upload_creates_activity(client, fit_dir):
    response = _upload(client, ("run.fit", make_fit()))
    assert response.status_code == 200
    result = response.json()[0]
    assert result["status"] == "created"
    assert len(list(fit_dir.glob("*.fit"))) == 1


def test_upload_same_file_twice_is_duplicate(client):
    data = make_fit()
    _upload(client, ("a.fit", data))
    assert _upload(client, ("a.fit", data)).json()[0]["status"] == "duplicate"


def test_upload_then_sync_same_run_is_one_activity(client, db_session):
    day = START.date()
    start = datetime(day.year, day.month, day.day, 7, tzinfo=UTC)
    _upload(client, ("run.fit", make_fit(seconds=120, laps=1, start=start)))
    db_session.add(CorosAccount(id=1, server_url="x", status="connected"))
    run_sync(db_session, FakeClient([("5555", 100, day, "running")]), day)
    assert db_session.scalar(select(func.count()).select_from(Activity)) == 1
    activity = db_session.scalar(select(Activity))
    assert activity.external_id == "5555"
    assert activity.training_load == 55


def test_upload_garbage_reports_error(client):
    result = _upload(client, ("bad.fit", b"nope"), ("ok.fit", make_fit())).json()
    assert [r["status"] for r in result] == ["error", "created"]


def test_list_filters_by_sport_newest_first(client):
    _upload(
        client,
        ("r1.fit", make_fit(start=datetime(2026, 1, 1, 7, tzinfo=UTC))),
        ("r2.fit", make_fit(start=datetime(2026, 1, 3, 7, tzinfo=UTC))),
        ("w.fit", make_fit(sport="walking", start=datetime(2026, 1, 2, 7, tzinfo=UTC))),
    )
    runs = client.get("/api/activities?sport=run").json()
    assert [r["started_at"][:10] for r in runs] == ["2026-01-03", "2026-01-01"]
    assert runs[0]["avg_pace_s_per_km"] == pytest.approx(333.3, abs=0.1)
    assert len(client.get("/api/activities").json()) == 3


def test_detail_includes_laps_and_streams(client):
    activity_id = _upload(client, ("r.fit", make_fit(laps=3))).json()[0]["id"]
    body = client.get(f"/api/activities/{activity_id}").json()
    assert len(body["laps"]) == 3
    assert "hr" in body["streams"] and len(body["streams"]["t"]) > 10


def test_delete_removes_activity_and_file(client, fit_dir):
    activity_id = _upload(client, ("r.fit", make_fit())).json()[0]["id"]
    assert client.delete(f"/api/activities/{activity_id}").status_code == 204
    assert client.get(f"/api/activities/{activity_id}").status_code == 404
    assert list(fit_dir.glob("*.fit")) == []


def test_same_start_different_sport_mapping_is_one_activity(client, db_session):
    day = START.date()
    start = datetime(day.year, day.month, day.day, 7, tzinfo=UTC)
    _upload(client, ("hike.fit", make_fit(seconds=120, laps=1, sport="walking", start=start)))
    db_session.add(CorosAccount(id=1, server_url="x", status="connected"))
    run_sync(db_session, FakeClient([("6666", 100, day, "running")]), day)
    assert db_session.scalar(select(func.count()).select_from(Activity)) == 1


def test_upload_unexpected_parse_failure_reports_error(client, monkeypatch):
    def broken(data):
        raise AttributeError("no start_time")

    monkeypatch.setattr("app.activities.router.parse_fit", broken)
    result = _upload(client, ("odd.fit", make_fit())).json()
    assert result[0]["status"] == "error"


def test_detail_includes_running_dynamics(client):
    activity_id = _upload(client, ("r.fit", make_fit())).json()[0]["id"]
    body = client.get(f"/api/activities/{activity_id}").json()
    assert body["avg_stride_m"] == pytest.approx(1.1)
    assert body["avg_power_w"] == 230
    assert body["laps"][0]["avg_power_w"] == 220
    assert "power" in body["streams"]


def test_reparse_refreshes_stored_activity(client, db_session):
    from app.activities.service import reparse_all

    activity_id = _upload(client, ("r.fit", make_fit())).json()[0]["id"]
    activity = db_session.get(Activity, activity_id)
    activity.avg_power_w = None
    activity.streams = {"t": []}
    activity.training_load = 77
    db_session.flush()
    assert reparse_all(db_session) == 1
    db_session.refresh(activity)
    assert activity.avg_power_w == 230
    assert len(activity.streams["t"]) > 10
    assert activity.training_load == 77
