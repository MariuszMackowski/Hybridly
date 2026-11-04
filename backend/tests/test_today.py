from datetime import UTC, date, datetime

import pytest

import app.templates.router as templates_router
from app.coros.models import CorosDaily
from app.plans.service import import_plan
from app.routines.models import Routine, RoutineLog, RoutineWeekday
from tests.factories import make_activity
from tests.plan_fixtures import plan_yaml

MON = date(2026, 1, 5)


@pytest.fixture
def on_day(monkeypatch):
    def set_day(d: date, hour: int = 10):
        monkeypatch.setattr(
            templates_router, "utc_now", lambda: datetime(d.year, d.month, d.day, hour, tzinfo=UTC)
        )

    return set_day


def test_today_includes_planned_run(client, db_session, on_day):
    import_plan(db_session, plan_yaml("A", MON), today=MON)
    on_day(MON)
    body = client.get("/api/today").json()
    assert [r["title"] for r in body["runs"]] == ["Easy 8 km"]
    assert body["week"]["phase"] == "Base"


def test_today_week_done_km(client, db_session, on_day):
    import_plan(db_session, plan_yaml("A", MON), today=MON)
    make_activity(db_session, datetime(2026, 1, 5, 17, tzinfo=UTC), distance_m=8200)
    make_activity(db_session, datetime(2026, 1, 4, 17, tzinfo=UTC), distance_m=5000)  # last week
    db_session.commit()
    on_day(date(2026, 1, 7))
    week = client.get("/api/today").json()["week"]
    assert week["done_km"] == 8.2
    assert week["target_km"] == 30


def test_today_cutback_hint(client, db_session, on_day):
    import_plan(db_session, plan_yaml("A", MON, flags_week1="[cutback]"), today=MON)
    on_day(MON)
    assert "drop 1 set" in client.get("/api/today").json()["strength_hint"]
    on_day(date(2026, 1, 12))
    assert client.get("/api/today").json()["strength_hint"] is None


def test_today_day_notes(client, db_session, on_day):
    import_plan(db_session, plan_yaml("A", MON), today=MON)
    on_day(date(2026, 1, 6))
    assert client.get("/api/today").json()["day_notes"] == ["Gym lighter"]


def test_today_routines_with_done_flag(client, db_session, on_day):
    core = Routine(name="Core", video_ids=[])
    db_session.add(core)
    db_session.flush()
    db_session.add(RoutineWeekday(weekday=0, routine_id=core.id))
    db_session.add(RoutineLog(day=MON, routine_id=core.id))
    db_session.commit()
    on_day(MON)
    routines = client.get("/api/today").json()["routines"]
    assert [(r["routine"]["name"], r["done"]) for r in routines] == [("Core", True)]


def test_today_recovery_from_latest_snapshot(client, db_session, on_day):
    db_session.add(
        CorosDaily(
            day=date(2026, 1, 4),
            kind="recovery",
            raw_text="",
            data={"recovery_pct": 80, "level": "Fresh"},
        )
    )
    db_session.commit()
    on_day(MON)
    assert client.get("/api/today").json()["recovery"]["recovery_pct"] == 80


def test_today_without_plan_is_empty(client, on_day):
    on_day(MON)
    body = client.get("/api/today").json()
    assert body["runs"] == [] and body["week"] is None and body["strength_hint"] is None
