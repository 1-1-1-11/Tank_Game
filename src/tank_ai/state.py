"""State normalization helpers for judge-provided dictionaries."""


def walls_set(walls_list):
    return set(tuple(pos) for pos in walls_list)


def alive_enemies(state, my_name):
    return [
        tank
        for tank in state["tanks"]
        if tank["name"] != my_name and tank["alive"]
    ]


def enemy_positions(enemies):
    return {(tank["x"], tank["y"]) for tank in enemies}


def enemy_positions_from_tanks(tanks):
    """Extract positions from a list of tank dicts (including self)."""
    return {(tank["x"], tank["y"]) for tank in tanks if tank["alive"]}

