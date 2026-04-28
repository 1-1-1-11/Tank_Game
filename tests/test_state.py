from tank_ai.state import walls_set, alive_enemies, enemy_positions


def test_walls_set_converts_list_to_set():
    result = walls_set([[0, 0], [1, 1], [2, 2]])
    assert result == {(0, 0), (1, 1), (2, 2)}


def test_walls_set_empty_list_returns_empty_set():
    result = walls_set([])
    assert result == set()


def test_alive_enemies_filters_self_and_dead():
    tanks = [
        {"name": "me", "alive": True, "x": 0, "y": 0},
        {"name": "enemy1", "alive": True, "x": 1, "y": 1},
        {"name": "enemy2", "alive": False, "x": 2, "y": 2},
        {"name": "enemy3", "alive": True, "x": 3, "y": 3},
    ]
    state = {"tanks": tanks}
    result = alive_enemies(state, "me")
    assert result == [
        {"name": "enemy1", "alive": True, "x": 1, "y": 1},
        {"name": "enemy3", "alive": True, "x": 3, "y": 3},
    ]


def test_alive_enemies_returns_only_alive_enemies():
    tanks = [
        {"name": "me", "alive": True, "x": 0, "y": 0},
        {"name": "enemy1", "alive": True, "x": 1, "y": 1},
        {"name": "enemy2", "alive": False, "x": 2, "y": 2},
        {"name": "enemy3", "alive": True, "x": 3, "y": 3},
    ]
    state = {"tanks": tanks}
    result = alive_enemies(state, "me")
    assert result == [
        {"name": "enemy1", "alive": True, "x": 1, "y": 1},
        {"name": "enemy3", "alive": True, "x": 3, "y": 3},
    ]


def test_enemy_positions_extracts_xy_tuples():
    enemies = [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
    result = enemy_positions(enemies)
    assert result == {(1, 2), (3, 4)}


def test_enemy_positions_empty_list():
    result = enemy_positions([])
    assert result == set()
