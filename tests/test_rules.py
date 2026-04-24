from tank_ai.rules import is_valid_move


def test_valid_move_accepts_open_cell():
    assert is_valid_move(1, 1, "RIGHT", 3, 3, set(), None)


def test_valid_move_rejects_out_of_bounds():
    assert not is_valid_move(-1, 0, "LEFT", 3, 3, set(), None)


def test_valid_move_rejects_wall():
    assert not is_valid_move(1, 1, "RIGHT", 3, 3, {(1, 1)}, None)


def test_valid_move_rejects_immediate_reverse():
    assert not is_valid_move(1, 1, "LEFT", 3, 3, set(), "RIGHT")


def test_valid_move_can_ignore_reverse_for_fallback():
    assert is_valid_move(1, 1, "LEFT", 3, 3, set(), "RIGHT", check_reverse=False)

