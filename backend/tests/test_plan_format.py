from datetime import date

import pytest

from app.plans.format import COACH_INSTRUCTIONS, PlanFormatError, pace_to_s, parse_plan_yaml

PLAN = """
version: 1
name: Test plan
goal: {race: Test Marathon, date: 2026-04-19, target_time: "3:30:00"}
weeks:
  - week: 1
    start: 2026-01-05
    phase: Base
    flags: [cutback]
    target_km: 30
    day_notes: [{date: 2026-01-06, text: "Gym lighter"}]
    sessions:
      - date: 2026-01-05
        type: easy
        title: Easy 8 km
        description: "Easy 8km, 5:40-6:20/km (HR133-146)"
        distance_km: 8
        pace: {min: "5:40", max: "6:20"}
        hr: {min: 133, max: 146}
      - date: 2026-01-09
        type: intervals
        title: 6x400
        description: "Interwały 6x400m @4:15-4:20/km"
        intervals: {reps: 6, distance_m: 400, pace: {min: "4:15", max: "4:20"}, recovery: 2 min jog}
"""


def test_valid_plan_parses():
    plan = parse_plan_yaml(PLAN)
    week = plan.weeks[0]
    assert plan.name == "Test plan"
    assert plan.goal.date == date(2026, 4, 19)
    assert week.flags == ["cutback"]
    assert week.sessions[1].intervals.reps == 6
    assert week.day_notes[0].text == "Gym lighter"


def test_pace_strings_to_seconds():
    assert pace_to_s("5:40") == 340
    assert parse_plan_yaml(PLAN).weeks[0].sessions[0].pace.min_s == 340


def test_week_start_must_be_monday():
    with pytest.raises(PlanFormatError) as caught:
        parse_plan_yaml(PLAN.replace("start: 2026-01-05", "start: 2026-01-06"))
    assert "weeks.0.start" in caught.value.path


def test_session_outside_week_rejected():
    with pytest.raises(PlanFormatError) as caught:
        parse_plan_yaml(PLAN.replace("date: 2026-01-09", "date: 2026-01-19"))
    assert "weeks.0.sessions.1" in caught.value.path


def test_invalid_plan_reports_field_path():
    with pytest.raises(PlanFormatError) as caught:
        parse_plan_yaml(PLAN.replace("type: easy", "type: jogging"))
    assert caught.value.path == "weeks.0.sessions.0.type"


def test_pace_range_must_be_ordered():
    with pytest.raises(PlanFormatError):
        parse_plan_yaml(PLAN.replace('{min: "5:40", max: "6:20"}', '{min: "6:20", max: "5:40"}'))


def test_not_yaml_rejected():
    with pytest.raises(PlanFormatError):
        parse_plan_yaml("weeks: [: : :")


def test_instructions_contain_example_that_parses():
    example = COACH_INSTRUCTIONS.split("```yaml")[1].split("```")[0]
    assert parse_plan_yaml(example).weeks
