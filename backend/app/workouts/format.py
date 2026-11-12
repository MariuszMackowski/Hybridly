"""Plain-text formatting of logged sets, shared by the coach export and the Strava description."""


def kg_text(value) -> str:
    """Weight without trailing zeros ("62.5", "60")."""
    return f"{float(value):g}"


def set_text(s, mark_pr: bool = True) -> str:
    """'60×8', '60 kg · 45 s', '40 m'; warm-ups get a W prefix, PRs a suffix (if mark_pr)."""
    if s.reps is not None:
        text = f"{kg_text(s.weight_kg or 0)}×{s.reps}"
    else:
        amount = f"{s.seconds} s" if s.seconds is not None else f"{s.distance_m:g} m"
        text = f"{kg_text(s.weight_kg)} kg · {amount}" if s.weight_kg else amount
    return ("W " if s.is_warmup else "") + text + (" PR" if mark_pr and s.is_pr else "")


def exercise_line(entry) -> str:
    """'Lat Pulldown (V-grip): 35×10, 45×8' with ' per side' for unilateral exercises."""
    name = entry.exercise.name + (f" ({entry.grip})" if entry.grip else "")
    side = " per side" if entry.exercise.per_side else ""
    return f"{name}{side}: " + ", ".join(set_text(s) for s in entry.sets)
