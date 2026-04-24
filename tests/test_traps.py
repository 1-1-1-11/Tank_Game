from tank_ai.traps import get_survival_depth


def test_survival_depth_detects_short_dead_end():
    assert get_survival_depth((0, 1), "DOWN", 1, 3, set(), max_depth=15) == 1


def test_survival_depth_returns_limit_when_path_is_long_enough():
    assert get_survival_depth((0, 0), "RIGHT", 20, 1, set(), max_depth=15) == 15
