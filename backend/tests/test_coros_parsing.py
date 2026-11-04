import json
from datetime import date

from app.coros.parsing import (
    RecordRef,
    parse_activity_detail,
    parse_recovery,
    parse_sport_records,
    parse_training_load,
)

RECORDS = """Sport Records — 2026-01-01 to 2026-01-31 (4 records)
========================

1. Strength — 2026-01-20
   Location: Gym
   Time Window: startTimestamp=1700000000 | endTimestamp=1700002000
   Duration: 42:25 | Sets: 1
   | Avg HR: 102 bpm | Calories: 265 kcal
   LabelId: 111 | SportType: 402

2. Outdoor Run — 2026-01-19
   Location: Morning Run
   Start Coordinates: 1.000000, 2.000000
   Time Window: startTimestamp=1699900000 | endTimestamp=1699901748
   Duration: 29:08 | Distance: 5.01 km
   Average Pace: 5:49 /km | Avg HR: 148 bpm | Calories: 392 kcal
   LabelId: 222 | SportType: 100

3. Walk — 2026-01-18
   Location: City Walk
   Duration: 1:54:55 | Distance: 6.12 km
   LabelId: 333 | SportType: 900

4. Something weird without ids — 2026-01-17
   Duration: 10:00
"""

DETAIL = """🏃 Outdoor Run Activity Details
========================================

Workout Time: 29:08
Distance: 5.01 km
Average Heart Rate: 148 bpm
Training Load: 63
Aerobic TE: 2.3
Anaerobic TE: 0.9
"""

RECOVERY = (
    "Recovery Status\n========================\n\n"
    "Recovery: 85%\nLevel: Fresh\nEstimated Full Recovery: 6h"
)

LOAD = """Training Load Assessment
========================

2026-01-20
Comment: Performance
Short-Term Load: 31
Long-Term Load: 46
Load Ratio: 0.67

2026-01-19
Comment: Maintaining
Short-Term Load: 41
Long-Term Load: 47
Load Ratio: 0.87
"""


def test_records_extract_label_and_sport():
    refs, skipped = parse_sport_records(RECORDS)
    assert refs[:2] == [
        RecordRef("111", 402, "Gym", date(2026, 1, 20)),
        RecordRef("222", 100, "Morning Run", date(2026, 1, 19)),
    ]
    assert refs[2].label_id == "333"


def test_records_json_quoted_text():
    refs, _ = parse_sport_records(json.dumps(RECORDS))
    assert [r.label_id for r in refs] == ["111", "222", "333"]


def test_unparsable_record_block_is_skipped():
    refs, skipped = parse_sport_records(RECORDS)
    assert len(refs) == 3
    assert skipped == 1


def test_detail_training_load_and_te():
    assert parse_activity_detail(json.dumps(DETAIL)) == {
        "training_load": 63,
        "aerobic_te": 2.3,
        "anaerobic_te": 0.9,
    }


def test_detail_missing_fields_absent():
    assert parse_activity_detail("Workout Time: 10:00") == {}


def test_recovery_fields():
    assert parse_recovery(json.dumps(RECOVERY)) == {
        "recovery_pct": 85,
        "level": "Fresh",
        "full_recovery_h": 6,
    }


def test_training_load_days():
    days = parse_training_load(LOAD)
    assert days[0] == {
        "day": "2026-01-20",
        "comment": "Performance",
        "short_term": 31,
        "long_term": 46,
        "ratio": 0.67,
    }
    assert len(days) == 2
