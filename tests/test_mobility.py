from tank_ai.mobility import bfs_mobility


def test_bfs_mobility_counts_reachable_space_within_limit():
    assert bfs_mobility((1, 1), 3, 3, set(), limit=8) == 9


def test_bfs_mobility_respects_walls():
    walls = {(0, 1), (1, 0), (2, 1), (1, 2)}

    assert bfs_mobility((1, 1), 3, 3, walls, limit=8) == 1

