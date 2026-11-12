def estimate_1rm(weight_kg: float, reps: int) -> float:
    """Estimate one-rep max: Brzycki up to 12 reps (matches Gravitus), Epley above."""
    if reps < 1:
        raise ValueError("reps must be >= 1")
    if weight_kg < 0:
        raise ValueError("weight must be >= 0")
    if reps == 1:
        return round(float(weight_kg), 2)
    if reps <= 12:
        return round(weight_kg * 36 / (37 - reps), 2)
    return round(weight_kg * (1 + reps / 30), 2)


def weight_for_reps(one_rm: float, reps: int) -> float:
    """Inverse of estimate_1rm: the weight that gives `one_rm` at `reps` reps."""
    if reps < 1:
        raise ValueError("reps must be >= 1")
    if reps == 1:
        return one_rm
    if reps <= 12:
        return one_rm * (37 - reps) / 36
    return one_rm / (1 + reps / 30)
