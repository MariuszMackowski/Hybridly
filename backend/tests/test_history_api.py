from datetime import UTC, datetime

import pytest

from tests.factories import make_exercise, make_workout
from tests.fitgen import make_fit


@pytest.fixture(autouse=True)
def fit_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.activities.service.get_settings", lambda: type("S", (), {"fit_dir": str(tmp_path)})()
    )


def _day(d):
    return datetime(2026, 1, d, 7, tzinfo=UTC)


@pytest.fixture
def mixed(client, db_session):
    """Workouts on days 1 and 3, a run on day 2, a walk on day 4."""
    bench = make_exercise(db_session)
    make_workout(db_session, bench, [(40, 8)], started_at=_day(1))
    make_workout(db_session, bench, [(45, 8), (45, 7)], started_at=_day(3))
    db_session.commit()
    files = [
        ("run.fit", make_fit(start=_day(2))),
        ("walk.fit", make_fit(sport="walking", start=_day(4))),
    ]
    client.post(
        "/api/activities/upload",
        files=[("files", (n, d, "application/octet-stream")) for n, d in files],
    )


def _days(items):
    return [i["started_at"][8:10] for i in items]


def test_history_merges_newest_first(client, mixed):
    items = client.get("/api/history").json()
    assert _days(items) == ["04", "03", "02", "01"]
    assert [i["kind"] for i in items] == ["activity", "workout", "activity", "workout"]
    assert items[1]["set_count"] == 2
    assert items[2]["sport"] == "run" and items[2]["distance_m"] == pytest.approx(1800)


def test_history_filter_gym(client, mixed):
    assert _days(client.get("/api/history?kind=gym").json()) == ["03", "01"]


def test_history_filter_run(client, mixed):
    items = client.get("/api/history?kind=run").json()
    assert [(i["kind"], i["sport"]) for i in items] == [("activity", "run")]


def test_history_pagination_across_sources(client, mixed):
    first = client.get("/api/history?limit=2&offset=0").json()
    second = client.get("/api/history?limit=2&offset=2").json()
    assert _days(first) + _days(second) == ["04", "03", "02", "01"]


def test_calendar_marks_days_by_kind(client, mixed):
    days = client.get("/api/history/calendar?month=2026-01").json()
    assert days == [
        {"day": "2026-01-01", "kinds": ["gym"]},
        {"day": "2026-01-02", "kinds": ["run"]},
        {"day": "2026-01-03", "kinds": ["gym"]},
        {"day": "2026-01-04", "kinds": ["walk"]},
    ]


def test_calendar_uses_warsaw_date(client, db_session):
    bench = make_exercise(db_session)
    make_workout(db_session, bench, [(40, 8)], started_at=datetime(2026, 1, 31, 23, 30, tzinfo=UTC))
    db_session.commit()
    assert client.get("/api/history/calendar?month=2026-01").json() == []
    assert client.get("/api/history/calendar?month=2026-02").json()[0]["day"] == "2026-02-01"


def test_history_filtered_to_one_day(client, mixed):
    items = client.get("/api/history?day=2026-01-03").json()
    assert [(i["kind"], i["started_at"][:10]) for i in items] == [("workout", "2026-01-03")]
