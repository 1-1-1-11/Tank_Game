"""Immediate bullet danger checks."""


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

