import pytest

from app.progression.e1rm import estimate_1rm


def test_brzycki_matches_gravitus():
    assert estimate_1rm(10.0, 5) == 11.25
    assert estimate_1rm(40.0, 10) == 53.33


def test_single_rep_returns_weight():
    assert estimate_1rm(100, 1) == 100


def test_high_reps_use_epley():
    assert estimate_1rm(30, 15) == 45.0


def test_invalid_reps_raise():
    with pytest.raises(ValueError):
        estimate_1rm(50, 0)
