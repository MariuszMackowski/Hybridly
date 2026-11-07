"""Fastest segments of standard distances within one activity (pure)."""

EFFORTS = {
    "100m": 100,
    "400m": 400,
    "1k": 1000,
    "5k": 5000,
    "10k": 10000,
    "half": 21097.5,
    "marathon": 42195,
}
MAX_SPEED_MS = 11.0  # faster than this between two records is a GPS jump, not running


def _fastest(times: list[float], dists: list[float], target: float) -> int | None:
    """Shortest time covering `target` metres; the segment start is interpolated."""
    best = None
    start = 0
    for end in range(1, len(dists)):
        if dists[end] - dists[0] < target:
            continue
        while dists[end] - dists[start + 1] >= target:
            start += 1
        # Slide the start forward inside [start, start+1] so the segment is exactly `target`.
        span = dists[start + 1] - dists[start]
        share = (dists[end] - target - dists[start]) / span if span > 0 else 0.0
        begin = times[start] + share * (times[start + 1] - times[start])
        elapsed = times[end] - begin
        if best is None or elapsed < best:
            best = elapsed
    return round(best) if best is not None else None


def _without_jumps(times: list[float], dists: list[float]) -> list[float]:
    """Cumulative distance with GPS jumps clipped to MAX_SPEED_MS between records."""
    clean = dists[:1]
    for i in range(1, len(dists)):
        step = dists[i] - dists[i - 1]
        limit = MAX_SPEED_MS * max(times[i] - times[i - 1], 0.0)
        clean.append(clean[-1] + min(step, limit))
    return clean


def best_efforts(times: list[float], dists: list[float]) -> dict[str, int]:
    """Seconds of the fastest segment per standard distance the activity covers."""
    clean = _without_jumps(times, dists)
    out = {}
    for key, target in EFFORTS.items():
        seconds = _fastest(times, clean, target)
        if seconds is not None:
            out[key] = seconds
    return out
