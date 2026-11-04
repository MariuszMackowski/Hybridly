"""Training load, recovery and muscle fatigue (pure functions; constants tunable here)."""

import math
from dataclasses import dataclass, field
from datetime import datetime

STRENGTH_K = 4.0  # scales strength sets to the COROS training-load scale (~15 hard sets ≈ 60-80)
REL_MIN, REL_MAX, REL_UNKNOWN = 0.3, 1.0, 0.6
LOAD_PER_MIN = {"walk": 0.6}  # fallback when COROS gave no training load
DEFAULT_LOAD_PER_MIN = 1.2
RECOVERY_TAU_H = 36.0
MUSCLE_TAU_H = 48.0
MUSCLE_FULL = 6.0  # hard-set equivalents that make a muscle fully red
FULL_RECOVERY_SHARE = 0.05
MIN_CAPACITY = 120.0
CAPACITY_FACTOR = 3.0


@dataclass
class Event:
    """A load at a moment; `muscles` maps muscle → hard-set equivalents."""

    at: datetime
    load: float
    muscles: dict[str, float] = field(default_factory=dict)


@dataclass
class Recovery:
    """Overall state."""

    recovery_pct: int
    hours_to_full: int
    acute: float
    capacity: float


def strength_set_load(load_factor: float, rel: float | None, per_side: bool) -> float:
    """Load of one working set: K × exercise factor × relative intensity × sides."""
    intensity = REL_UNKNOWN if rel is None else min(REL_MAX, max(REL_MIN, rel))
    return STRENGTH_K * load_factor * intensity * (2 if per_side else 1)


def activity_load(sport: str, training_load: int | None, duration_s: int) -> float:
    """COROS training load, or a duration-based estimate."""
    if training_load is not None:
        return float(training_load)
    return duration_s / 60 * LOAD_PER_MIN.get(sport, DEFAULT_LOAD_PER_MIN)


def decay(hours: float, tau: float) -> float:
    """Exponential decay factor after `hours`."""
    return math.exp(-max(0.0, hours) / tau)


def _hours(now: datetime, at: datetime) -> float:
    """Hours between two instants."""
    return (now - at).total_seconds() / 3600


def recovery(events: list[Event], now: datetime, capacity: float) -> Recovery:
    """Recovery % from decaying acute load against the athlete's capacity."""
    acute = sum(e.load * decay(_hours(now, e.at), RECOVERY_TAU_H) for e in events if e.at <= now)
    pct = round(100 * min(1.0, max(0.0, 1 - acute / capacity)))
    floor = FULL_RECOVERY_SHARE * capacity
    hours = math.ceil(RECOVERY_TAU_H * math.log(acute / floor)) if acute > floor else 0
    return Recovery(pct, hours, round(acute, 1), round(capacity, 1))


def capacity_from_daily(daily_loads: list[float]) -> float:
    """3 × mean daily load over the window, never below MIN_CAPACITY."""
    mean = sum(daily_loads) / len(daily_loads) if daily_loads else 0.0
    return max(MIN_CAPACITY, CAPACITY_FACTOR * mean)


def muscle_levels(events: list[Event], now: datetime) -> dict[str, float]:
    """0..1 fatigue per muscle (1 = MUSCLE_FULL hard sets right now)."""
    scores: dict[str, float] = {}
    for event in events:
        if event.at > now:
            continue
        factor = decay(_hours(now, event.at), MUSCLE_TAU_H)
        for muscle, amount in event.muscles.items():
            scores[muscle] = scores.get(muscle, 0.0) + amount * factor
    return {m: round(min(1.0, s / MUSCLE_FULL), 3) for m, s in scores.items()}
