"""Store activities parsed from FIT files, deduplicated across COROS sync and uploads."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activities.fit_parser import ParsedFit, fit_sha256
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


def _find_existing(db: Session, digest: str, parsed: ParsedFit, sport: str) -> Activity | None:
    """Same file, or same start time and sport (COROS vs. manual upload of one activity)."""
    return db.scalar(select(Activity).where(Activity.fit_sha256 == digest)) or db.scalar(
        select(Activity).where(Activity.started_at == parsed.started_at, Activity.sport == sport)
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
    existing = _find_existing(db, digest, parsed, sport)
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
        started_at=parsed.started_at,
        duration_s=parsed.duration_s,
        distance_m=parsed.distance_m,
        avg_hr=parsed.avg_hr,
        max_hr=parsed.max_hr,
        avg_speed=parsed.avg_speed,
        ascent_m=parsed.ascent_m,
        calories=parsed.calories,
        avg_cadence_spm=parsed.avg_cadence_spm,
        fit_sha256=digest,
        fit_path=_save_file(data, digest),
        streams=parsed.streams,
        laps=[ActivityLap(**vars(lap)) for lap in parsed.laps],
        **(extras or {}),
    )
    db.add(activity)
    db.flush()
    return activity, True
