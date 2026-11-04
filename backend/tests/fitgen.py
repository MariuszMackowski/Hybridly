"""Build small synthetic FIT activity files for tests (no real GPS/personal data)."""

from datetime import UTC, datetime

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import FileType, Manufacturer, Sport

START = datetime(2026, 1, 10, 8, 0, tzinfo=UTC)
_SPORTS = {"running": Sport.RUNNING, "walking": Sport.WALKING, "basketball": Sport.BASKETBALL}


def _ms(seconds: float, start: datetime = START) -> int:
    """Epoch milliseconds for an offset from start."""
    return int((start.timestamp() + seconds) * 1000)


def make_fit(
    seconds: int = 600,
    laps: int = 2,
    sport: str = "running",
    with_gps: bool = True,
    with_hr: bool = True,
    speed: float = 3.0,
    start: datetime = START,
) -> bytes:
    """1 Hz records at constant speed, equal laps, one session."""
    builder = FitFileBuilder(auto_define=True, min_string_size=50)
    file_id = FileIdMessage()
    file_id.type = FileType.ACTIVITY
    file_id.manufacturer = Manufacturer.DEVELOPMENT.value
    file_id.product = 0
    file_id.time_created = _ms(0, start)
    file_id.serial_number = 1
    builder.add(file_id)

    for t in range(seconds + 1):
        rec = RecordMessage()
        rec.timestamp = _ms(t, start)
        rec.distance = speed * t
        rec.speed = speed
        rec.altitude = 10.0 + (t % 20)
        rec.cadence = 80
        if with_hr:
            rec.heart_rate = 130 + (t * 20 // seconds)
        if with_gps:
            rec.position_lat = 10.0 + t * 1e-5
            rec.position_long = 20.0 + t * 1e-5
        builder.add(rec)

    lap_len = seconds // laps
    for i in range(laps):
        lap = LapMessage()
        lap.start_time = _ms(i * lap_len, start)
        lap.timestamp = _ms((i + 1) * lap_len, start)
        lap.total_elapsed_time = lap_len
        lap.total_timer_time = lap_len
        lap.total_distance = speed * lap_len
        lap.avg_speed = speed
        if with_hr:
            lap.avg_heart_rate = 135 + i
            lap.max_heart_rate = 150 + i
        lap.avg_running_cadence = 80
        builder.add(lap)

    session = SessionMessage()
    session.start_time = _ms(0, start)
    session.timestamp = _ms(seconds, start)
    session.sport = _SPORTS[sport]
    session.total_elapsed_time = seconds
    session.total_timer_time = seconds
    session.total_distance = speed * seconds
    session.avg_speed = speed
    session.total_ascent = 25
    session.total_calories = 120
    session.avg_running_cadence = 80
    if with_hr:
        session.avg_heart_rate = 140
        session.max_heart_rate = 150
    builder.add(session)
    return builder.build().to_bytes()
