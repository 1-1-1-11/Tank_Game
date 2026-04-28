"""Movement legality checks."""

from typing import Optional, Set, Tuple

from tank_ai.constants import OPPOSITE


def in_bounds(x: int, y: int, map_w: int, map_h: int) -> bool:
    """Check if a position is within map boundaries."""
    return 0 <= x < map_w and 0 <= y < map_h


def is_valid_move(
    x: int,
    y: int,
    move: str,
    map_w: int,
    map_h: int,
    walls: Set[Tuple[int, int]],
    last_action: Optional[str] = None,
    check_reverse: bool = True,
) -> bool:
    """Check if a move is valid (in bounds, not into walls, not reversing)."""
    if not in_bounds(x, y, map_w, map_h):
        return False
    if (x, y) in walls:
        return False
    if check_reverse and last_action and move == OPPOSITE.get(last_action):
        return False
    return True

