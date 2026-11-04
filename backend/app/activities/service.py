"""Store activities parsed from FIT files, deduplicated across COROS sync and uploads."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activities.fit_parser import ParsedFit, fit_sha256, parse_fit
from app.activities.models import Activity, ActivityLap
from app.config import get_settings


def sport_from_coros(sport_type: int | None, fallback: str) -> str:
    """Map a COROS sport type code to our sport name."""
    if sport_type is None:
        return fallback
    if 100 <= sport_type < 200:
        return "run"
    return {900: "walk", 1002: "basketball"}.get(sport_type, "other")


def _save_file(data: bytes, digest: str) -> str:
    """Write the original FIT under the configured directory; return its path."""
    directory = Path(get_settings().fit_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{digest}.fit"
    if not path.exists():
        path.write_bytes(data)
    return str(path)


SUMMARY_FIELDS = (
    "started_at",
    "duration_s",
    "distance_m",
    "avg_hr",
    "max_hr",
    "avg_speed",
    "ascent_m",
    "calories",
    "avg_cadence_spm",
    "avg_stride_m",
    "avg_power_w",
    "avg_gct_ms",
    "avg_vo_cm",
    "avg_vr_pct",
    "streams",
)


def _apply_parsed(activity: Activity, parsed: ParsedFit) -> None:
    """Copy FIT-derived summary, streams and laps onto an activity (COROS fields untouched)."""
    for name in SUMMARY_FIELDS:
        setattr(activity, name, getattr(parsed, name))
    activity.laps = [ActivityLap(**vars(lap)) for lap in parsed.laps]


def reparse_all(db: Session) -> int:
    """Re-read every stored FIT file (after the parser learns new fields); returns count."""
    count = 0
    for activity in db.scalars(select(Activity)):
        path = Path(activity.fit_path)
        if path.exists():
            _apply_parsed(activity, parse_fit(path.read_bytes()))
            count += 1
    db.commit()
    return count


def _find_existing(db: Session, digest: str, parsed: ParsedFit) -> Activity | None:
    """Same file, or same start time (one person cannot start two activities at once)."""
    return db.scalar(select(Activity).where(Activity.fit_sha256 == digest)) or db.scalar(
        select(Activity).where(Activity.started_at == parsed.started_at)
    )


def store_activity(
    db: Session,
    parsed: ParsedFit,
    data: bytes,
    source: str,
    external_id: str | None = None,
    sport_type: int | None = None,
    name: str | None = None,
    extras: dict | None = None,
) -> tuple[Activity, bool]:
    """Insert an activity, or return the existing one (COROS data is adopted on a match)."""
    digest = fit_sha256(data)
    sport = sport_from_coros(sport_type, parsed.sport)
    existing = _find_existing(db, digest, parsed)
    if existing is not None:
        if source == "coros" and existing.external_id is None:
            existing.external_id, existing.sport_type = external_id, sport_type
            existing.name = existing.name or name
            for key, value in (extras or {}).items():
                setattr(existing, key, value)
        return existing, False
    activity = Activity(
        source=source,
        external_id=external_id,
        sport=sport,
        sport_type=sport_type,
        name=name,
        fit_sha256=digest,
        fit_path=_save_file(data, digest),
        **(extras or {}),
    )
    _apply_parsed(activity, parsed)
    db.add(activity)
    db.flush()
    return activity, True
