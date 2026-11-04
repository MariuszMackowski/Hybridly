"""Synthetic plan YAML builders for tests."""

from datetime import date, timedelta


def plan_yaml(name: str, monday: date, weeks: int = 2, flags_week1: str = "[]") -> str:
    """Plan with an easy run on Monday, intervals on Friday and a long run on Sunday each week."""
    lines = ["version: 1", f"name: {name}", "weeks:"]
    for w in range(weeks):
        start = monday + timedelta(days=7 * w)
        flags = flags_week1 if w == 0 else "[]"
        lines += [
            f"  - week: {w + 1}",
            f"    start: {start}",
            "    phase: Base",
            f"    flags: {flags}",
            "    target_km: 30",
            f"    day_notes: [{{date: {start + timedelta(days=1)}, text: 'Gym lighter'}}]",
            "    sessions:",
            f"      - {{date: {start}, type: easy, title: Easy 8 km, distance_km: 8,"
            " pace: {min: '5:40', max: '6:20'}, hr: {min: 133, max: 146}}",
            f"      - {{date: {start + timedelta(days=4)}, type: intervals, title: 5x1km,"
            " intervals: {reps: 5, distance_m: 1000, pace: {min: '4:15', max: '4:25'}}}",
            f"      - {{date: {start + timedelta(days=6)}, type: long, title: Long 16 km,"
            " distance_km: 16}",
        ]
    return "\n".join(lines) + "\n"
