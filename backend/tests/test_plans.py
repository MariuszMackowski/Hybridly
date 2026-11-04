from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from app.plans.compare import compare
from app.plans.matching import match_activity
from app.plans.models import PlanSession
from app.plans.service import import_plan, sessions_on, week_of
from tests.factories import make_activity
from tests.plan_fixtures import plan_yaml

MON = date(2026, 1, 5)


def _at(d: date, hour: int = 17) -> datetime:
    return datetime(d.year, d.month, d.day, hour, tzinfo=UTC)


def test_import_creates_weeks_and_sessions(db_session):
    plan = import_plan(db_session, plan_yaml("A", MON), today=MON)
    assert len(plan.weeks) == 2
    assert sum(len(w.sessions) for w in plan.weeks) == 6
    assert plan.effective_from == MON


def test_new_plan_does_not_rewrite_past_days(db_session):
    import_plan(db_session, plan_yaml("A", MON, weeks=3), today=MON)
    run = make_activity(db_session, _at(date(2026, 1, 12)))
    match_activity(db_session, run)
    import_plan(db_session, plan_yaml("B", date(2026, 1, 12), weeks=2), today=date(2026, 1, 14))
    old_day = sessions_on(db_session, date(2026, 1, 12))
    assert [s.week.plan.name for s in old_day] == ["A"]
    assert old_day[0].activity_id == run.id
    assert [s.week.plan.name for s in sessions_on(db_session, date(2026, 1, 16))] == ["B"]


def test_sessions_on_uses_active_plan(db_session):
    import_plan(db_session, plan_yaml("A", MON), today=MON)
    assert [s.title for s in sessions_on(db_session, MON)] == ["Easy 8 km"]
    assert sessions_on(db_session, date(2026, 1, 6)) == []
    assert week_of(db_session, date(2026, 1, 7)).week == 1


def test_import_endpoint_returns_422_with_path(client):
    response = client.post("/api/plans/import", content="version: 1\nname: X\nweeks: []\n")
    assert response.status_code == 422
    assert "weeks" in response.json()["detail"]


def test_import_endpoint_and_active(client):
    response = client.post("/api/plans/import", content=plan_yaml("A", MON))
    assert response.status_code == 201
    body = client.get("/api/plans/active").json()
    assert body["name"] == "A" and len(body["weeks"]) == 2


def test_match_prefers_same_day(db_session):
    import_plan(db_session, plan_yaml("A", MON), today=MON)
    run = make_activity(db_session, _at(MON))
    match_activity(db_session, run)
    assert sessions_on(db_session, MON)[0].activity_id == run.id


def test_match_next_day_when_planned_day_empty(db_session):
    import_plan(db_session, plan_yaml("A", MON), today=MON)
    run = make_activity(db_session, _at(date(2026, 1, 10)))  # Saturday after Friday intervals
    match_activity(db_session, run)
    assert sessions_on(db_session, date(2026, 1, 9))[0].activity_id == run.id


def test_activity_matched_once(db_session):
    import_plan(db_session, plan_yaml("A", MON), today=MON)
    first = make_activity(db_session, _at(MON, 7))
    second = make_activity(db_session, _at(MON, 18))
    match_activity(db_session, first)
    match_activity(db_session, second)
    linked = db_session.query(PlanSession).filter(PlanSession.activity_id.is_not(None)).all()
    assert [s.activity_id for s in linked] == [first.id]


def test_walks_not_matched(db_session):
    import_plan(db_session, plan_yaml("A", MON), today=MON)
    match_activity(db_session, make_activity(db_session, _at(MON), sport="walk"))
    assert sessions_on(db_session, MON)[0].activity_id is None


def _session(**kw):
    base = dict(
        type="easy",
        distance_km=8,
        pace_min_s=340,
        pace_max_s=380,
        hr_min=133,
        hr_max=146,
        intervals=None,
    )
    return SimpleNamespace(**{**base, **kw})


def _activity(**kw):
    base = dict(
        distance_m=8000,
        duration_s=2960,
        streams={"t": [0, 5, 10, 15], "hr": [130, 140, 145, 150]},
        laps=[],
    )
    return SimpleNamespace(**{**base, **kw})


def test_compare_distance_and_pace_status():
    result = compare(_session(), _activity())
    assert result.distance_pct == 100
    assert result.pace_s == 370
    assert result.pace_status == "in"
    assert compare(_session(), _activity(duration_s=2600)).pace_status == "faster"


def test_compare_hr_zone_split():
    result = compare(_session(), _activity())
    assert (result.hr_below_pct, result.hr_in_pct, result.hr_above_pct) == (25, 50, 25)


def test_compare_without_hr_stream():
    result = compare(_session(), _activity(streams={"t": [0, 5]}))
    assert result.hr_in_pct is None
    assert result.distance_pct == 100


def test_compare_interval_laps():
    laps = [
        SimpleNamespace(index=0, distance_m=2000, duration_s=720),
        SimpleNamespace(index=1, distance_m=1000, duration_s=262),
        SimpleNamespace(index=2, distance_m=400, duration_s=150),
        SimpleNamespace(index=3, distance_m=980, duration_s=270),
    ]
    session = _session(
        type="intervals",
        intervals={"reps": 5, "distance_m": 1000, "pace": {"min": "4:15", "max": "4:25"}},
    )
    rows = compare(session, _activity(laps=laps)).interval_laps
    assert [(r.index, r.in_range) for r in rows] == [(1, True), (3, False)]
    assert rows[0].pace_s == 262


@pytest.fixture
def fit_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.activities.service.get_settings", lambda: type("S", (), {"fit_dir": str(tmp_path)})()
    )


def test_uploaded_run_is_matched_and_compared(client, db_session, fit_dir):
    from tests.fitgen import make_fit

    import_plan(db_session, plan_yaml("A", MON), today=MON)
    data = make_fit(seconds=600, start=_at(MON, 7))
    activity_id = client.post(
        "/api/activities/upload", files=[("files", ("r.fit", data, "application/octet-stream"))]
    ).json()[0]["id"]
    body = client.get(f"/api/activities/{activity_id}").json()
    assert body["plan"]["title"] == "Easy 8 km"
    assert body["plan"]["comparison"]["distance_pct"] == 22


def test_manual_link_moves_activity(client, db_session):
    import_plan(db_session, plan_yaml("A", MON), today=MON)
    run = make_activity(db_session, _at(MON))
    match_activity(db_session, run)
    db_session.commit()
    friday = sessions_on(db_session, date(2026, 1, 9))[0]
    response = client.post(f"/api/plans/sessions/{friday.id}/link", json={"activity_id": run.id})
    assert response.json()["activity_id"] == run.id
    assert sessions_on(db_session, MON)[0].activity_id is None
