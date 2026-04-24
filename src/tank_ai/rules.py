"""Movement legality checks."""

from tank_ai.constants import OPPOSITE


def in_bounds(x, y, map_w, map_h):
    return 0 <= x < map_w and 0 <= y < map_h


def is_valid_move(x, y, move, map_w, map_h, walls, last_action=None, check_reverse=True):
    if not in_bounds(x, y, map_w, map_h):
        return False
    if (x, y) in walls:
        return False
    if check_reverse and last_action and move == OPPOSITE.get(last_action):
        return False
    return True

