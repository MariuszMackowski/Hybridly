import pytest

from app.activities.fit_parser import fit_sha256, parse_fit
from tests.fitgen import START, make_fit


def test_summary_fields_from_session():
    parsed = parse_fit(make_fit(seconds=600, speed=3.0))
    assert parsed.sport == "run"
    assert parsed.started_at == START
    assert parsed.duration_s == 600
    assert parsed.distance_m == pytest.approx(1800)
    assert (parsed.avg_hr, parsed.max_hr) == (140, 150)
    assert parsed.avg_speed == pytest.approx(3.0)
    assert parsed.ascent_m == 25
    assert parsed.calories == 120


def test_cadence_doubled_to_spm():
    assert parse_fit(make_fit()).avg_cadence_spm == 160


def test_laps_parsed_in_order():
    laps = parse_fit(make_fit(seconds=600, laps=3)).laps
    assert [lap.index for lap in laps] == [0, 1, 2]
    assert [lap.start_offset_s for lap in laps] == [0, 200, 400]
    assert laps[1].avg_hr == 136
    assert laps[0].distance_m == pytest.approx(600)


def test_streams_downsampled():
    streams = parse_fit(make_fit(seconds=600)).streams
    assert streams["t"][:3] == [0, 5, 10]
    assert len(streams["t"]) == 121
    assert len(streams["hr"]) == len(streams["t"]) == len(streams["lat"])
    assert streams["lat"][0] == pytest.approx(10.0, abs=1e-4)


def test_fit_without_gps_or_hr():
    parsed = parse_fit(make_fit(with_gps=False, with_hr=False))
    assert parsed.avg_hr is None
    assert "lat" not in parsed.streams and "hr" not in parsed.streams
    assert parsed.distance_m == pytest.approx(1800)


def test_walk_sport_mapped():
    assert parse_fit(make_fit(sport="walking")).sport == "walk"


def test_invalid_bytes_raise_value_error():
    with pytest.raises(ValueError):
        parse_fit(b"not a fit file")


def test_sha256_is_stable():
    data = make_fit()
    assert fit_sha256(data) == fit_sha256(bytes(data))
    assert len(fit_sha256(data)) == 64
