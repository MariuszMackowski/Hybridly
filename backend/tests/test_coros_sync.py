from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.activities.models import Activity
from app.coros.models import CorosAccount, CorosDaily
from app.coros.sync import run_sync
from tests.fitgen import make_fit

TODAY = date(2026, 1, 31)


class FakeClient:
    """Serves a fixed list of (label, sport_type, day, sport) activities."""

    def __init__(self, items, broken=()):
        self.items = items
        self.broken = set(broken)
        self.downloads = 0

    def list_records(self, start, end):
        blocks = [
            f"{i + 1}. Activity — {day.isoformat()}\n   Location: Name {label}\n"
            f"   LabelId: {label} | SportType: {sport_type}\n"
            for i, (label, sport_type, day, _) in enumerate(self.items)
            if start <= day <= end
        ]
        return "Sport Records\n====\n\n" + "\n".join(blocks)

    def download_fit(self, label_id, sport_type):
        self.downloads += 1
        if label_id in self.broken:
            return b"garbage"
        label, _, day, sport = next(i for i in self.items if i[0] == label_id)
        start = datetime(day.year, day.month, day.day, 7, tzinfo=UTC)
        return make_fit(seconds=120, laps=1, sport=sport, start=start)

    def activity_detail(self, label_id, sport_type):
        return f"Training Load: {int(label_id) % 100}\nAerobic TE: 2.5\nAnaerobic TE: 0.5"

    def recovery(self):
        return "Recovery: 90%\nLevel: Fresh\nEstimated Full Recovery: 3h"

    def training_load(self, days):
        return (
            "2026-01-31\nComment: Performance\n"
            "Short-Term Load: 30\nLong-Term Load: 40\nLoad Ratio: 0.75"
        )


ITEMS = [
    ("1001", 100, TODAY - timedelta(days=1), "running"),
    ("1002", 402, TODAY - timedelta(days=2), "running"),
    ("1003", 900, TODAY - timedelta(days=3), "walking"),
]


@pytest.fixture(autouse=True)
def fit_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.activities.service.get_settings", lambda: type("S", (), {"fit_dir": str(tmp_path)})()
    )
    return tmp_path


@pytest.fixture
def account(db_session):
    db_session.add(CorosAccount(id=1, server_url="x", status="connected"))
    db_session.flush()


def _count(db):
    return db.scalar(select(func.count()).select_from(Activity))


def test_sync_imports_new_runs_and_walks(db_session, account):
    report = run_sync(db_session, FakeClient(ITEMS), TODAY)
    sports = sorted(db_session.scalars(select(Activity.sport)))
    assert sports == ["run", "walk"]
    assert report.imported == 2


def test_sync_skips_strength(db_session, account):
    report = run_sync(db_session, FakeClient(ITEMS), TODAY)
    assert report.skipped_strength == 1


def test_sync_twice_creates_nothing_new(db_session, account):
    client = FakeClient(ITEMS)
    run_sync(db_session, client, TODAY)
    report = run_sync(db_session, client, TODAY)
    assert report.imported == 0
    assert _count(db_session) == 2
    assert client.downloads == 2


def test_sync_stops_at_download_cap(db_session, account):
    items = [(str(2000 + i), 100, TODAY - timedelta(days=i), "running") for i in range(5)]
    report = run_sync(db_session, FakeClient(items), TODAY, cap=3)
    assert report.imported == 3
    assert report.deferred == 2
    assert _count(db_session) == 3


def test_sync_stores_training_load(db_session, account):
    run_sync(db_session, FakeClient(ITEMS), TODAY)
    run = db_session.scalar(select(Activity).where(Activity.external_id == "1001"))
    assert (run.training_load, run.aerobic_te, run.source, run.name) == (
        1,
        2.5,
        "coros",
        "Name 1001",
    )


def test_sync_records_daily_snapshots(db_session, account):
    run_sync(db_session, FakeClient(ITEMS), TODAY)
    recovery = db_session.get(CorosDaily, (TODAY, "recovery"))
    assert recovery.data["recovery_pct"] == 90
    load = db_session.get(CorosDaily, (TODAY, "training_load"))
    assert load.data[0]["short_term"] == 30
    status = db_session.get(CorosAccount, 1).last_sync_status
    assert status["imported"] == 2


def test_one_bad_fit_does_not_abort_sync(db_session, account):
    report = run_sync(db_session, FakeClient(ITEMS, broken={"1001"}), TODAY)
    assert report.imported == 1
    assert any("1001" in e for e in report.errors)
