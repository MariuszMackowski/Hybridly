"""Pull new non-strength activities and daily snapshots from COROS."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.activities.fit_parser import parse_fit
from app.activities.models import Activity
from app.activities.service import store_activity
from app.coros.client import CorosClient
from app.coros.models import CorosAccount, CorosDaily
from app.coros.parsing import (
    RecordRef,
    parse_activity_detail,
    parse_recovery,
    parse_sport_records,
    parse_training_load,
)
from app.time import local_date

STRENGTH = 402
FIRST_SYNC_DAYS = 60
OVERLAP_DAYS = 2
DEFAULT_CAP = 45  # COROS allows 50 FIT downloads per 24 h


@dataclass
class SyncReport:
    """Outcome of one sync run (stored as last_sync_status)."""

    imported: int = 0
    skipped_existing: int = 0
    skipped_strength: int = 0
    deferred: int = 0
    unparsable: int = 0
    errors: list[str] = field(default_factory=list)


def _window_start(db: Session, today: date) -> date:
    """Re-check a couple of days before the newest COROS activity, or 60 days on first run."""
    latest = db.scalar(select(func.max(Activity.started_at)).where(Activity.source == "coros"))
    if latest is None:
        return today - timedelta(days=FIRST_SYNC_DAYS)
    return local_date(latest) - timedelta(days=OVERLAP_DAYS)


def _import_one(db: Session, client: CorosClient, ref: RecordRef) -> bool:
    """Download, parse and store one activity; True when newly created."""
    data = client.download_fit(ref.label_id, ref.sport_type)
    parsed = parse_fit(data)
    extras = parse_activity_detail(client.activity_detail(ref.label_id, ref.sport_type))
    _, created = store_activity(
        db, parsed, data, "coros", ref.label_id, ref.sport_type, ref.name, extras
    )
    return created


def _snapshot(db: Session, day: date, kind: str, raw: str, data) -> None:
    """Upsert one daily snapshot."""
    row = db.get(CorosDaily, (day, kind)) or CorosDaily(day=day, kind=kind)
    row.raw_text, row.data = raw, data
    db.add(row)


def _daily_snapshots(db: Session, client: CorosClient, today: date, report: SyncReport) -> None:
    """Store today's recovery and training-load assessment."""
    try:
        raw = client.recovery()
        _snapshot(db, today, "recovery", raw, parse_recovery(raw))
        raw = client.training_load(7)
        _snapshot(db, today, "training_load", raw, parse_training_load(raw))
    except Exception as error:  # noqa: BLE001 — snapshots must not fail the sync
        report.errors.append(f"daily snapshot: {error}")


def run_sync(db: Session, client: CorosClient, today: date, cap: int = DEFAULT_CAP) -> SyncReport:
    """Import activities missing locally (newest first, at most `cap` downloads)."""
    report = SyncReport()
    refs, report.unparsable = parse_sport_records(
        client.list_records(_window_start(db, today), today)
    )
    known = set(db.scalars(select(Activity.external_id).where(Activity.external_id.is_not(None))))
    todo = []
    for ref in refs:
        if ref.sport_type == STRENGTH:
            report.skipped_strength += 1
        elif ref.label_id in known:
            report.skipped_existing += 1
        else:
            todo.append(ref)
    for ref in todo[:cap]:
        try:
            with db.begin_nested():
                if _import_one(db, client, ref):
                    report.imported += 1
                else:
                    report.skipped_existing += 1
        except Exception as error:  # noqa: BLE001 — one bad activity must not abort the sync
            report.errors.append(f"{ref.label_id} ({ref.day}): {error}")
    report.deferred = max(0, len(todo) - cap)
    _daily_snapshots(db, client, today, report)
    account = db.get(CorosAccount, 1)
    if account is not None:
        account.last_sync_at = datetime.now(UTC)
        account.last_sync_status = asdict(report)
    db.commit()
    return report
