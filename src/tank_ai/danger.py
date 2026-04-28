"""Immediate bullet danger checks and danger map generation."""

from tank_ai.constants import DIRS


def will_hit_bullet(my_next_pos, bullets, my_name, map_w, map_h, walls):
    mx, my = my_next_pos

    for bullet in bullets:
        if bullet["owner"] == my_name:
            continue

        bx, by = bullet["x"], bullet["y"]
        dx, dy = bullet["dx"], bullet["dy"]

        s1_x, s1_y = bx + dx, by + dy
        if not (0 <= s1_x < map_w and 0 <= s1_y < map_h) or (s1_x, s1_y) in walls:
            continue
        if (s1_x, s1_y) == (mx, my):
            return True

        s2_x, s2_y = s1_x + dx, s1_y + dy
        if not (0 <= s2_x < map_w and 0 <= s2_y < map_h) or (s2_x, s2_y) in walls:
            continue
        if (s2_x, s2_y) == (mx, my):
            return True

    return False


def get_danger_map(bullets, my_name, map_w, map_h, walls, danger_penalty=5000.0):
    """Build a 2D danger map accumulating danger from bullet paths."""
    dmap = [[0.0] * map_h for _ in range(map_w)]

    for b in bullets:
        if b["owner"] == my_name:
            continue

        bx, by = b["x"], b["y"]
        bdx, bdy = b["dx"], b["dy"]

        cx, cy = bx, by
        while 0 <= cx < map_w and 0 <= cy < map_h:
            if (cx, cy) in walls:
                break
            dmap[cx][cy] += danger_penalty
            cx += bdx
            cy += bdy

    return dmap

