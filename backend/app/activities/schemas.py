from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


class ActivitySummary(BaseModel):
    """Row of the activities list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    sport: str
    name: str | None
    started_at: datetime
    duration_s: int
    distance_m: float | None
    avg_hr: int | None
    avg_speed: float | None
    training_load: int | None

    @computed_field
    @property
    def avg_pace_s_per_km(self) -> float | None:
        """Average pace from distance and moving time."""
        if not self.distance_m or not self.duration_s:
            return None
        return round(self.duration_s / (self.distance_m / 1000), 1)


class LapOut(BaseModel):
    """Lap of an activity."""

    model_config = ConfigDict(from_attributes=True)

    index: int
    start_offset_s: int
    duration_s: int
    distance_m: float | None
    avg_hr: int | None
    max_hr: int | None
    avg_speed: float | None
    avg_cadence_spm: int | None
    avg_power_w: int | None = None
    avg_stride_m: float | None = None


class ActivityDetail(ActivitySummary):
    """Full activity with laps and streams."""

    sport_type: int | None
    external_id: str | None
    max_hr: int | None
    ascent_m: float | None
    calories: int | None
    avg_cadence_spm: int | None
    avg_stride_m: float | None
    avg_power_w: int | None
    avg_gct_ms: float | None
    avg_vo_cm: float | None
    avg_vr_pct: float | None
    aerobic_te: float | None
    anaerobic_te: float | None
    laps: list[LapOut]
    streams: dict


class UploadResult(BaseModel):
    """Outcome for one uploaded file."""

    filename: str
    status: str  # created | duplicate | error
    id: int | None = None
    detail: str | None = None
