from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class PrevSet:
    """A working set from an earlier session."""

    weight_kg: float
    reps: int


class SuggestionKind(StrEnum):
    increase = "increase"
    hold = "hold"
    reduce = "reduce"


@dataclass(frozen=True)
class Suggestion:
    """Target weight and reps for one set."""

    weight_kg: float
    reps: int
    kind: SuggestionKind


def _suggest_one(
    prev: PrevSet, before: PrevSet | None, rep_min: int, rep_max: int, increment_kg: float
) -> Suggestion:
    """Suggest one set when the exercise is not ready for a weight increase."""
    if prev.reps <= rep_min - 2:
        return Suggestion(max(0.0, prev.weight_kg - increment_kg), rep_min, SuggestionKind.reduce)
    if before is not None and before.weight_kg == prev.weight_kg and prev.reps <= before.reps - 2:
        return Suggestion(prev.weight_kg, prev.reps, SuggestionKind.hold)
    return Suggestion(prev.weight_kg, min(prev.reps + 1, rep_max), SuggestionKind.hold)


def suggest_sets(
    previous: list[PrevSet],
    before_previous: list[PrevSet],
    sets: int,
    rep_min: int,
    rep_max: int,
    increment_kg: float,
) -> list[Suggestion]:
    """Double progression: all sets at top of range -> add weight, else chase +1 rep."""
    if not previous:
        return []
    if all(s.reps >= rep_max for s in previous):
        result = [
            Suggestion(s.weight_kg + increment_kg, rep_min, SuggestionKind.increase)
            for s in previous
        ]
    else:
        result = [
            _suggest_one(
                prev,
                before_previous[i] if i < len(before_previous) else None,
                rep_min,
                rep_max,
                increment_kg,
            )
            for i, prev in enumerate(previous)
        ]
    if len(result) < sets:
        result += [result[-1]] * (sets - len(result))
    return result[:sets]
