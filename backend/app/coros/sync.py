"""Pull new non-strength activities and daily snapshots from COROS."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activities.fit_parser import parse_fit
from app.activities.models import Activity
from app.activities.service import store_activity
from app.coros import oauth
from app.coros.client import CorosAuthError, CorosClient, CorosQuotaError
from app.coros.models import CorosAccount, CorosDaily
from app.coros.parsing import (
    RecordRef,
    parse_activity_detail,
    parse_fitness,
    parse_recovery,
    parse_sport_records,
    parse_training_load,
)

STRENGTH = 402
WINDOW_DAYS = 60  # always re-list this window: deferred/failed items are retried for free
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
    """Store today's recovery, training-load and fitness assessment (each independently)."""
    fetches = {
        "recovery": (client.recovery, parse_recovery),
        "training_load": (lambda: client.training_load(7), parse_training_load),
        "fitness": (client.fitness, parse_fitness),
    }
    for kind, (fetch, parse) in fetches.items():
        try:
            raw = fetch()
            data = parse(raw)
            if data:  # an unparsable reply must not replace the last good snapshot
                _snapshot(db, today, kind, raw, data)
        except Exception as error:  # noqa: BLE001 — snapshots must not fail the sync
            report.errors.append(f"{kind} snapshot: {error}")


def run_sync(db: Session, client: CorosClient, today: date, cap: int = DEFAULT_CAP) -> SyncReport:
    """Import activities missing locally (newest first, at most `cap` downloads)."""
    report = SyncReport()
    raw = client.list_records(today - timedelta(days=WINDOW_DAYS), today)
    refs, report.unparsable = parse_sport_records(raw)
    # Ids the parser could not attribute (e.g. COROS changed the header format) are unparsable too.
    report.unparsable = max(report.unparsable, raw.count("LabelId:") - len(refs))
    known = set(db.scalars(select(Activity.external_id).where(Activity.external_id.is_not(None))))
    todo = []
    for ref in refs:
        if ref.sport_type == STRENGTH:
            report.skipped_strength += 1
        elif ref.label_id in known:
            report.skipped_existing += 1
        else:
            todo.append(ref)
    report.deferred = max(0, len(todo) - cap)
    for index, ref in enumerate(todo[:cap]):
        try:
            with db.begin_nested():
                if _import_one(db, client, ref):
                    report.imported += 1
                else:
                    report.skipped_existing += 1
        except CorosQuotaError as error:
            report.errors.append(f"COROS limit reached, the rest follows next sync: {error}")
            report.deferred = len(todo) - index
            break
        except CorosAuthError:
            raise
        except Exception as error:  # noqa: BLE001 — one bad activity must not abort the sync
            report.errors.append(f"{ref.label_id} ({ref.day}): {error}")
    _daily_snapshots(db, client, today, report)
    account = db.get(CorosAccount, 1)
    if account is not None:
        account.last_sync_at = datetime.now(UTC)
        account.last_sync_status = asdict(report)
    db.commit()
    return report


def sync_account(db: Session, make_client, today: date, token: str | None = None) -> dict | None:
    """Run a sync for the connected account, recording auth and unexpected failures."""
    account = db.get(CorosAccount, 1)
    if account is None or account.status != "connected":
        return None
    try:
        client = make_client(account.server_url, token or oauth.get_access_token(db))
        return asdict(run_sync(db, client, today))
    except (oauth.NeedsReconnect, CorosAuthError) as error:
        db.rollback()
        account = db.get(CorosAccount, 1)
        account.status = "needs_reconnect"
        account.last_sync_status = {"errors": [f"Reconnect COROS: {error}"]}
    except Exception as error:  # noqa: BLE001 — surface any failure in the UI
        db.rollback()
        account = db.get(CorosAccount, 1)
        account.last_sync_status = {"errors": [f"Sync failed: {error}"]}
    account.last_sync_at = datetime.now(UTC)
    db.commit()
    return None
