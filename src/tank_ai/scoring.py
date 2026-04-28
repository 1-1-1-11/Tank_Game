"""Candidate move scoring for the main bot."""

from typing import Any, Dict, List, Optional, Set, Tuple

from tank_ai.constants import (
    CLOCKWISE_NEXT,
    DIRS,
    SCORE_BULLET_HIT,
    SCORE_INVALID,
    SCORE_TRAP_BASE,
    TRAP_SURVIVAL_THRESHOLD,
    WEIGHT_AIM,
    WEIGHT_CENTER,
    WEIGHT_CONTINUITY,
    WEIGHT_MOBILITY,
    WEIGHT_SURVIVAL_DEPTH,
)
from tank_ai.danger import get_danger_map, will_hit_bullet
from tank_ai.mobility import bfs_mobility
from tank_ai.rules import is_valid_move
from tank_ai.traps import get_survival_depth

# 1v1 scoring constants
SCORE_SURVIVAL_1V1: float = 0.0
SCORE_TRADE_LIVES: float = -5000.0
SCORE_SUICIDE: float = -99999.0

MOBILITY_WEIGHT_1V1: float = 10.0
DANGER_PENALTY_1V1: float = 5000.0
TRAP_PENALTY_1V1: float = 20000.0
AIM_BONUS_1V1: float = 50.0
CIRCLE_BONUS_1V1: float = 8.0


def is_aiming_enemy(
    my_pos: Tuple[int, int],
    move: str,
    enemies_pos: Set[Tuple[int, int]],
    map_w: int,
    map_h: int,
    walls: Set[Tuple[int, int]],
) -> bool:
    """Check if moving in given direction aims at an enemy."""
    dx, dy = DIRS[move]
    cx, cy = my_pos[0] + dx, my_pos[1] + dy
    dist: int = 0

    while 0 <= cx < map_w and 0 <= cy < map_h and dist < 10:
        if (cx, cy) in walls:
            return False
        if (cx, cy) in enemies_pos:
            return True
        cx += dx
        cy += dy
        dist += 1

    return False


def score_candidate(
    move: str,
    my_pos: Tuple[int, int],
    my_name: str,
    bullets: List[Dict[str, Any]],
    enemies_pos: Set[Tuple[int, int]],
    map_w: int,
    map_h: int,
    walls: Set[Tuple[int, int]],
    last_action: Optional[str],
    mobility_cache: Optional[dict] = None,
) -> float:
    """Score a candidate move for the main bot."""
    my_x, my_y = my_pos
    dx, dy = DIRS[move]
    nx, ny = my_x + dx, my_y + dy
    score: float = 0.0

    if not is_valid_move(nx, ny, move, map_w, map_h, walls, last_action, check_reverse=True):
        return SCORE_INVALID

    if will_hit_bullet((nx, ny), bullets, my_name, map_w, map_h, walls):
        score += SCORE_BULLET_HIT

    survival_steps: int = get_survival_depth(
        (nx, ny), move, map_w, map_h, walls, max_depth=TRAP_SURVIVAL_THRESHOLD
    )

    if survival_steps < TRAP_SURVIVAL_THRESHOLD:
        score += SCORE_TRAP_BASE + (survival_steps * WEIGHT_SURVIVAL_DEPTH)
    else:
        if (nx, ny) in enemies_pos:
            score -= 500.0

        pos_key = (nx, ny)
        if mobility_cache is not None and pos_key in mobility_cache:
            mobility = mobility_cache[pos_key]
        else:
            mobility = bfs_mobility(pos_key, map_w, map_h, walls)
            if mobility_cache is not None:
                mobility_cache[pos_key] = mobility
        score += mobility * WEIGHT_MOBILITY

        dist_center: int = abs(nx - map_w // 2) + abs(ny - map_h // 2)
        score -= dist_center * WEIGHT_CENTER

        if is_aiming_enemy((nx, ny), move, enemies_pos, map_w, map_h, walls):
            score += WEIGHT_AIM

        if last_action == move:
            score += WEIGHT_CONTINUITY

    return score


def score_candidate_1v1(
    move: str,
    my_pos: Tuple[int, int],
    my_name: str,
    bullets: List[Dict[str, Any]],
    enemies_pos: Set[Tuple[int, int]],
    map_w: int,
    map_h: int,
    walls: Set[Tuple[int, int]],
    last_action: Optional[str],
    danger_map: List[List[float]],
    trap_lookup: dict,
    mobility_map: List[List[int]],
) -> float:
    """Score a candidate move using 1v1-specific logic."""
    my_x, my_y = my_pos
    dx, dy = DIRS[move]
    nx, ny = my_x + dx, my_y + dy
    score: float = SCORE_SURVIVAL_1V1

    # [1] Absolute rule checks
    if not is_valid_move(nx, ny, move, map_w, map_h, walls, last_action, check_reverse=True):
        return SCORE_SUICIDE

    # [2] Bullet hit check
    if will_hit_bullet((nx, ny), bullets, my_name, map_w, map_h, walls):
        return SCORE_SUICIDE

    # [3] Collision with enemy = trade lives
    if (nx, ny) in enemies_pos:
        return SCORE_TRADE_LIVES

    # [4] Danger map penalty
    if danger_map[nx][ny] > 0:
        score -= danger_map[nx][ny]

    # [5] Trap lookup penalty
    if trap_lookup.get(((nx, ny), move), False):
        score -= TRAP_PENALTY_1V1

    # [6] Tactical value (only if we are not in immediate danger)
    if score > -100:
        # Aim bonus
        aim_bonus: float = _get_aim_value_1v1((nx, ny), move, enemies_pos, map_w, map_h, walls)
        score += aim_bonus * AIM_BONUS_1V1

        # Mobility bonus
        score += mobility_map[nx][ny] * MOBILITY_WEIGHT_1V1

        # Circle bonus (clockwise movement around the map)
        if last_action and move == CLOCKWISE_NEXT[last_action]:
            score += CIRCLE_BONUS_1V1

    return score


def _get_aim_value_1v1(
    my_pos: Tuple[int, int],
    move: str,
    enemies_pos: Set[Tuple[int, int]],
    map_w: int,
    map_h: int,
    walls: Set[Tuple[int, int]],
) -> float:
    """Check if a move aims at an enemy and return 1.0 or 0.0."""
    dx, dy = DIRS[move]
    cx, cy = my_pos[0] + dx, my_pos[1] + dy
    while 0 <= cx < map_w and 0 <= cy < map_h:
        if (cx, cy) in walls:
            return 0.0
        if (cx, cy) in enemies_pos:
            return 1.0
        cx += dx
        cy += dy
    return 0.0

