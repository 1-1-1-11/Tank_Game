"""Trap and survival-depth analysis."""

from tank_ai.constants import DIRS, OPPOSITE


def get_survival_depth(start_pos, start_move, map_w, map_h, walls, max_depth=20):
    stack = [(start_pos, start_move, 0, {start_pos})]
    max_survival = 0

    while stack:
        (cx, cy), last_move, depth, visited = stack.pop()

        if depth > max_survival:
            max_survival = depth

        if depth >= max_depth:
            return max_depth

        reverse_move = OPPOSITE.get(last_move)

        for move, (dx, dy) in DIRS.items():
            if move == reverse_move:
                continue

            nx, ny = cx + dx, cy + dy

            if not (0 <= nx < map_w and 0 <= ny < map_h):
                continue
            if (nx, ny) in walls:
                continue
            if (nx, ny) in visited:
                continue

            new_visited = visited.copy()
            new_visited.add((nx, ny))
            stack.append(((nx, ny), move, depth + 1, new_visited))

    return max_survival

