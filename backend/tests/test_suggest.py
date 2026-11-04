from app.progression.suggest import PrevSet, Suggestion, SuggestionKind, suggest_sets

INC = SuggestionKind.increase
HOLD = SuggestionKind.hold
RED = SuggestionKind.reduce


def _prev(*pairs):
    return [PrevSet(w, r) for w, r in pairs]


def _sug(*triples):
    return [Suggestion(w, r, k) for w, r, k in triples]


def test_no_history_returns_empty():
    assert suggest_sets([], [], sets=3, rep_min=8, rep_max=10, increment_kg=2.5) == []


def test_all_sets_at_top_of_range_increase():
    result = suggest_sets(_prev(*[(60, 8)] * 4), [], sets=4, rep_min=6, rep_max=8, increment_kg=2.5)
    assert result == _sug(*[(62.5, 6, INC)] * 4)


def test_below_top_holds_weight_and_adds_rep():
    prev = _prev((60, 8), (60, 7), (60, 6), (60, 6))
    result = suggest_sets(prev, [], sets=4, rep_min=6, rep_max=8, increment_kg=2.5)
    assert result == _sug((60, 8, HOLD), (60, 8, HOLD), (60, 7, HOLD), (60, 7, HOLD))


def test_rep_drop_vs_session_before_holds_reps():
    result = suggest_sets(
        _prev((60, 5)), _prev((60, 7)), sets=1, rep_min=6, rep_max=8, increment_kg=2.5
    )
    assert result == _sug((60, 5, HOLD))


def test_far_below_range_reduces():
    result = suggest_sets(_prev((60, 4)), [], sets=1, rep_min=6, rep_max=8, increment_kg=2.5)
    assert result == _sug((57.5, 6, RED))


def test_more_target_sets_than_history_repeats_last():
    prev = _prev((60, 8), (60, 7), (55, 6))
    result = suggest_sets(prev, [], sets=4, rep_min=6, rep_max=8, increment_kg=2.5)
    assert len(result) == 4
    assert result[3] == result[2]


def test_zero_increment_at_top_keeps_weight_and_adds_rep():
    result = suggest_sets(_prev((0, 12)), [], sets=1, rep_min=8, rep_max=12, increment_kg=0)
    assert result == _sug((0, 13, INC))


def test_reduce_never_below_zero():
    result = suggest_sets(_prev((1, 1)), [], sets=1, rep_min=6, rep_max=8, increment_kg=2.5)
    assert result[0].weight_kg == 0
