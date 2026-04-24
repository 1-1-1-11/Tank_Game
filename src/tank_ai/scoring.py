"""Candidate move scoring for the main bot."""

from tank_ai.constants import (
    DIRS,
    SCORE_BULLET_HIT,
    SCORE_INVALID,
    SCORE_TRAP_BASE,
    WEIGHT_AIM,
    WEIGHT_CENTER,
    WEIGHT_CONTINUITY,
    WEIGHT_MOBILITY,
    WEIGHT_SURVIVAL_DEPTH,
)
from tank_ai.danger import will_hit_bullet
from tank_ai.mobility import bfs_mobility
from tank_ai.rules import is_valid_move
from tank_ai.traps import get_survival_depth


def is_aiming_enemy(my_pos, move, enemies_pos, map_w, map_h, walls):
    dx, dy = DIRS[move]
    cx, cy = my_pos[0] + dx, my_pos[1] + dy
    dist = 0

    while 0 <= cx < map_w and 0 <= cy < map_h and dist < 10:
        if (cx, cy) in walls:
            return False
        if (cx, cy) in enemies_pos:
            return True
        cx += dx
        cy += dy
        dist += 1

    return False


def score_candidate(move, my_pos, my_name, bullets, enemies_pos, map_w, map_h, walls, last_action):
    my_x, my_y = my_pos
    dx, dy = DIRS[move]
    nx, ny = my_x + dx, my_y + dy
    score = 0.0

    if not is_valid_move(nx, ny, move, map_w, map_h, walls, last_action, check_reverse=True):
        return SCORE_INVALID

    if will_hit_bullet((nx, ny), bullets, my_name, map_w, map_h, walls):
        score += SCORE_BULLET_HIT

    survival_steps = get_survival_depth((nx, ny), move, map_w, map_h, walls, max_depth=15)

    if survival_steps < 15:
        score += SCORE_TRAP_BASE + (survival_steps * WEIGHT_SURVIVAL_DEPTH)
    else:
        if (nx, ny) in enemies_pos:
            score -= 500.0

        mobility = bfs_mobility((nx, ny), map_w, map_h, walls)
        score += mobility * WEIGHT_MOBILITY

        dist_center = abs(nx - map_w // 2) + abs(ny - map_h // 2)
        score -= dist_center * WEIGHT_CENTER

        if is_aiming_enemy((nx, ny), move, enemies_pos, map_w, map_h, walls):
            score += WEIGHT_AIM

        if last_action == move:
            score += WEIGHT_CONTINUITY

    return score

