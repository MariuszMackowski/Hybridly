from enum import StrEnum


class Muscle(StrEnum):
    """Muscle groups used for exercise mapping and the fatigue map."""

    chest = "chest"
    front_delts = "front_delts"
    side_delts = "side_delts"
    rear_delts = "rear_delts"
    lats = "lats"
    upper_back = "upper_back"
    lower_back = "lower_back"
    biceps = "biceps"
    triceps = "triceps"
    forearms = "forearms"
    abs = "abs"
    obliques = "obliques"
    glutes = "glutes"
    quads = "quads"
    hamstrings = "hamstrings"
    adductors = "adductors"
    abductors = "abductors"
    calves = "calves"
    tibialis = "tibialis"
