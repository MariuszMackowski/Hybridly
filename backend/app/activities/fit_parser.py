"""Parse FIT activity files into summary, laps and downsampled streams (pure)."""

import hashlib
import io
from dataclasses import dataclass, field
from datetime import UTC, datetime

import fitdecode

from app.activities.best_efforts import best_efforts

SEMICIRCLE = 180 / 2**31
STREAM_STEP_S = 5
_SPORTS = {
    "running": "run",
    "trail_running": "run",
    "walking": "walk",
    "hiking": "walk",
    "basketball": "basketball",
}


@dataclass
class ParsedLap:
    """One lap of an activity."""

    index: int
    start_offset_s: int
    duration_s: int
    distance_m: float | None
    avg_hr: int | None
    max_hr: int | None
    avg_speed: float | None
    avg_cadence_spm: int | None
    avg_power_w: int | None = None
    avg_stride_m: float | None = None


@dataclass
class ParsedFit:
    """Activity data extracted from a FIT file."""

    sport: str
    started_at: datetime
    duration_s: int
    distance_m: float | None
    avg_hr: int | None
    max_hr: int | None
    avg_speed: float | None
    ascent_m: float | None
    calories: int | None
    avg_cadence_spm: int | None
    avg_stride_m: float | None = None
    avg_power_w: int | None = None
    avg_gct_ms: float | None = None
    avg_vo_cm: float | None = None
    avg_vr_pct: float | None = None
    laps: list[ParsedLap] = field(default_factory=list)
    streams: dict[str, list] = field(default_factory=dict)
    best_efforts: dict[str, int] = field(default_factory=dict)


def fit_sha256(data: bytes) -> str:
    """Content hash used to detect duplicate uploads."""
    return hashlib.sha256(data).hexdigest()


def _utc(value) -> datetime:
    """FIT timestamps are UTC; make them timezone-aware."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _get(msg, *names):
    """First present, non-None field value among names."""
    for name in names:
        if msg.has_field(name):
            value = msg.get_value(name)
            if value is not None:
                return value
    return None


def _spm(cadence) -> int | None:
    """Running cadence is per leg in FIT; return steps per minute."""
    return int(round(cadence * 2)) if cadence is not None else None


def _scaled(value, factor: float, digits: int = 2):
    """Unit conversion that keeps None (mm → m, mm → cm)."""
    return round(value * factor, digits) if value is not None else None


def _messages(data: bytes) -> dict[str, list]:
    """Group FIT data messages by name."""
    groups: dict[str, list] = {"record": [], "lap": [], "session": []}
    try:
        with fitdecode.FitReader(io.BytesIO(data), check_crc=fitdecode.CrcCheck.DISABLED) as reader:
            for frame in reader:
                if isinstance(frame, fitdecode.FitDataMessage) and frame.name in groups:
                    groups[frame.name].append(frame)
    except (fitdecode.FitError, EOFError, ValueError) as error:
        raise ValueError(f"Not a valid FIT file: {error}") from error
    if not groups["session"]:
        raise ValueError("FIT file has no session")
    return groups


def _streams(records: list, start: datetime) -> dict[str, list]:
    """Downsample 1 Hz records to one point per STREAM_STEP_S; drop channels with no data."""
    names = ("t", "hr", "speed", "alt", "lat", "lon", "cad", "stride", "power", "gct", "vo", "vr")
    channels: dict[str, list] = {name: [] for name in names}
    next_t = 0
    for rec in records:
        ts = _get(rec, "timestamp")
        if ts is None:
            continue
        t = int((_utc(ts) - start).total_seconds())
        if t < next_t:
            continue
        next_t = t + STREAM_STEP_S
        lat, lon = _get(rec, "position_lat"), _get(rec, "position_long")
        channels["t"].append(t)
        channels["hr"].append(_get(rec, "heart_rate"))
        channels["speed"].append(_get(rec, "enhanced_speed", "speed"))
        channels["alt"].append(_get(rec, "enhanced_altitude", "altitude"))
        channels["lat"].append(round(lat * SEMICIRCLE, 6) if lat is not None else None)
        channels["lon"].append(round(lon * SEMICIRCLE, 6) if lon is not None else None)
        channels["cad"].append(_spm(_get(rec, "cadence")))
        channels["stride"].append(_scaled(_get(rec, "step_length"), 0.001))
        channels["power"].append(_get(rec, "power"))
        channels["gct"].append(_get(rec, "stance_time"))
        channels["vo"].append(_scaled(_get(rec, "vertical_oscillation"), 0.1, 1))
        channels["vr"].append(_get(rec, "vertical_ratio"))
    return {k: v for k, v in channels.items() if k == "t" or any(x is not None for x in v)}


def _efforts(records: list, start: datetime) -> dict[str, int]:
    """Best efforts from full-resolution (timestamp, distance) records."""
    times, dists = [], []
    for rec in records:
        ts, dist = _get(rec, "timestamp"), _get(rec, "distance")
        if ts is None or dist is None or (dists and dist < dists[-1]):
            continue
        times.append((_utc(ts) - start).total_seconds())
        dists.append(float(dist))
    return best_efforts(times, dists)


def _laps(laps: list, start: datetime) -> list[ParsedLap]:
    """Convert lap messages in file order."""
    result = []
    for i, lap in enumerate(laps):
        lap_start = _get(lap, "start_time")
        result.append(
            ParsedLap(
                index=i,
                start_offset_s=int((_utc(lap_start) - start).total_seconds()) if lap_start else 0,
                duration_s=int(_get(lap, "total_timer_time", "total_elapsed_time") or 0),
                distance_m=_get(lap, "total_distance"),
                avg_hr=_get(lap, "avg_heart_rate"),
                max_hr=_get(lap, "max_heart_rate"),
                avg_speed=_get(lap, "enhanced_avg_speed", "avg_speed"),
                avg_cadence_spm=_spm(_get(lap, "avg_running_cadence", "avg_cadence")),
                avg_power_w=_get(lap, "avg_power"),
                avg_stride_m=_scaled(_get(lap, "avg_step_length"), 0.001),
            )
        )
    return result


def parse_fit(data: bytes) -> ParsedFit:
    """Parse a FIT activity; raises ValueError for unreadable files."""
    groups = _messages(data)
    session = groups["session"][0]
    start = _utc(_get(session, "start_time"))
    return ParsedFit(
        sport=_SPORTS.get(str(_get(session, "sport")), "other"),
        started_at=start,
        duration_s=int(_get(session, "total_timer_time", "total_elapsed_time") or 0),
        distance_m=_get(session, "total_distance"),
        avg_hr=_get(session, "avg_heart_rate"),
        max_hr=_get(session, "max_heart_rate"),
        avg_speed=_get(session, "enhanced_avg_speed", "avg_speed"),
        ascent_m=_get(session, "total_ascent"),
        calories=_get(session, "total_calories"),
        avg_cadence_spm=_spm(_get(session, "avg_running_cadence", "avg_cadence")),
        avg_stride_m=_scaled(_get(session, "avg_step_length"), 0.001),
        avg_power_w=_get(session, "avg_power"),
        avg_gct_ms=_get(session, "avg_stance_time"),
        avg_vo_cm=_scaled(_get(session, "avg_vertical_oscillation"), 0.1, 1),
        avg_vr_pct=_get(session, "avg_vertical_ratio"),
        laps=_laps(groups["lap"], start),
        streams=_streams(groups["record"], start),
        best_efforts=_efforts(groups["record"], start),
    )
