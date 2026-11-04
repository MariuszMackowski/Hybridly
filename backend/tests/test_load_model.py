from datetime import UTC, datetime, timedelta

import pytest

from app.load.model import (
    Event,
    activity_load,
    muscle_levels,
    recovery,
    strength_set_load,
)

NOW = datetime(2026, 1, 10, 12, tzinfo=UTC)


def test_strength_set_load_scales_with_intensity_and_factor():
    assert strength_set_load(load_factor=1.5, rel=1.0, per_side=False) == pytest.approx(6.0)
    assert strength_set_load(load_factor=1.0, rel=0.5, per_side=True) == pytest.approx(4.0)


def test_strength_set_load_clamps_relative_intensity():
    assert strength_set_load(1.0, rel=0.1, per_side=False) == pytest.approx(1.2)
    assert strength_set_load(1.0, rel=None, per_side=False) == pytest.approx(2.4)


def test_activity_load_prefers_coros_training_load():
    assert activity_load("run", training_load=63, duration_s=1800) == 63
    assert activity_load("walk", training_load=None, duration_s=3600) == pytest.approx(36)
    assert activity_load("run", training_load=None, duration_s=3000) == pytest.approx(60)


def test_recovery_after_fresh_load_and_decay():
    fresh = recovery([Event(NOW, 60)], NOW, capacity=120)
    assert fresh.recovery_pct == 50
    later = recovery([Event(NOW - timedelta(hours=36), 60)], NOW, capacity=120)
    assert later.recovery_pct == pytest.approx(82, abs=1)
    assert later.hours_to_full == pytest.approx(47, abs=1)


def test_recovery_full_without_events():
    result = recovery([], NOW, capacity=120)
    assert (result.recovery_pct, result.hours_to_full) == (100, 0)


def test_muscle_levels_primary_secondary_and_decay():
    events = [
        Event(NOW, 6.0, muscles={"chest": 6.0, "triceps": 3.0}),  # hard-set equivalents
        Event(NOW - timedelta(hours=96), 6.0, muscles={"lats": 6.0}),
    ]
    levels = muscle_levels(events, NOW)
    assert levels["chest"] == pytest.approx(1.0)
    assert levels["triceps"] == pytest.approx(0.5)
    assert levels["lats"] == pytest.approx(0.135, abs=0.01)
