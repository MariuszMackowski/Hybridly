from pathlib import Path

import pytest

from app.imports.gravitus.parser import GSet, lb_to_kg, mark_warmups, parse_export

SAMPLE = (Path(__file__).parent / "fixtures" / "gravitus_sample.csv").read_text()


@pytest.fixture(scope="module")
def parsed():
    return parse_export(SAMPLE)


def _workout(parsed, external_id):
    return next(w for w in parsed[0] if w.external_id == external_id)


def test_lb_to_kg_rounds_to_quarter():
    assert lb_to_kg(22.05) == 10.0
    assert lb_to_kg(132.28) == 60.0
    assert lb_to_kg(44.09) == 20.0


def test_parse_counts_workouts_and_templates(parsed):
    workouts, templates = parsed
    assert len(workouts) == 3
    assert [t.name for t in templates] == ["Upper"]


def test_sets_link_to_workout_despite_none_suffix(parsed):
    first = _workout(parsed, "2026-01-03 08:00:00+00:00")
    assert len(first.sets) == 6
    leg_day = _workout(parsed, "2026-01-05 08:00:00+00:00")
    assert leg_day.title == "Leg day"
    assert len(leg_day.sets) == 2


def test_orphan_sets_are_dropped(parsed):
    assert sum(len(w.sets) for w in parsed[0]) == 9


def test_time_set_has_seconds_no_reps(parsed):
    carry = _workout(parsed, "2026-01-05 08:00:00+00:00").sets[1]
    assert carry.seconds == 45 and carry.reps is None


def test_zero_weight_kept_as_zero(parsed):
    pull_up = _workout(parsed, "2026-01-03 08:00:00+00:00").sets[4]
    assert pull_up.weight_kg == 0.0


def test_template_groups_in_order(parsed):
    assert parsed[1][0].groups == [["Bench Press"], ["Pull-Up", "Barbell Row"]]


def test_profile_section_is_ignored(parsed):
    assert "example.com" not in repr(parsed)


def test_leading_light_sets_marked_warmup():
    sets = [
        GSet(0, i, "Bench Press", w, r, None, None)
        for i, (w, r) in enumerate([(20, 10), (40, 8), (45, 8), (20, 12)])
    ]
    assert [s.is_warmup for s in mark_warmups(sets)] == [True, False, False, False]


def test_bodyweight_sets_never_warmup():
    sets = [GSet(0, i, "Pull-Up", 0.0, 5, None, None) for i in range(3)]
    assert not any(s.is_warmup for s in mark_warmups(sets))


def test_parsed_workout_marks_warmups(parsed):
    bench = _workout(parsed, "2026-01-03 08:00:00+00:00").sets[:4]
    assert [s.is_warmup for s in bench] == [True, False, False, False]
