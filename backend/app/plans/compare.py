"""Planned session vs. performed activity (pure; works on any objects with the attributes)."""

from dataclasses import dataclass, field

from app.plans.format import pace_to_s

LAP_DISTANCE_TOLERANCE = 0.15


@dataclass
class IntervalLap:
    """A lap that looks like one interval repetition."""

    index: int
    distance_m: float
    pace_s: int
    in_range: bool | None


@dataclass
class Comparison:
    """How the activity matched the plan."""

    distance_pct: int | None = None
    pace_s: int | None = None
    pace_status: str | None = None  # in | faster | slower
    hr_below_pct: int | None = None
    hr_in_pct: int | None = None
    hr_above_pct: int | None = None
    interval_laps: list[IntervalLap] = field(default_factory=list)


def _pace_status(pace: int | None, fast: int | None, slow: int | None) -> str | None:
    """Pace relative to a [fast, slow] range in s/km."""
    if pace is None or fast is None or slow is None:
        return None
    if pace < fast:
        return "faster"
    return "slower" if pace > slow else "in"


def _hr_split(hr: list | None, low: int | None, high: int | None) -> tuple:
    """Percent of HR samples below / inside / above the range (5-s samples ≈ time)."""
    samples = [v for v in (hr or []) if v is not None]
    if not samples or low is None or high is None:
        return None, None, None
    below = sum(v < low for v in samples)
    above = sum(v > high for v in samples)
    total = len(samples)
    pct = [round(100 * n / total) for n in (below, total - below - above, above)]
    return tuple(pct)


def _interval_laps(intervals: dict, laps) -> list[IntervalLap]:
    """Laps whose distance is within ±15 % of the interval distance."""
    target = intervals.get("distance_m")
    if not target:
        return []
    pace = intervals.get("pace") or {}
    fast = pace_to_s(pace["min"]) if pace.get("min") else None
    slow = pace_to_s(pace["max"]) if pace.get("max") else None
    rows = []
    for lap in laps:
        if not lap.distance_m or abs(lap.distance_m - target) > target * LAP_DISTANCE_TOLERANCE:
            continue
        lap_pace = round(lap.duration_s / (lap.distance_m / 1000))
        status = _pace_status(lap_pace, fast, slow)
        rows.append(
            IntervalLap(
                lap.index, lap.distance_m, lap_pace, None if status is None else status == "in"
            )
        )
    return rows


def compare(session, activity) -> Comparison:
    """Distance, pace and HR-zone adherence, plus interval laps for interval sessions."""
    result = Comparison()
    if session.distance_km and activity.distance_m:
        result.distance_pct = round(100 * activity.distance_m / (session.distance_km * 1000))
    if activity.distance_m and activity.duration_s:
        result.pace_s = round(activity.duration_s / (activity.distance_m / 1000))
        result.pace_status = _pace_status(result.pace_s, session.pace_min_s, session.pace_max_s)
    result.hr_below_pct, result.hr_in_pct, result.hr_above_pct = _hr_split(
        (activity.streams or {}).get("hr"), session.hr_min, session.hr_max
    )
    if session.type == "intervals" and session.intervals:
        result.interval_laps = _interval_laps(session.intervals, activity.laps)
    return result
