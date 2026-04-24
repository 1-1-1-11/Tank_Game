"""Mobility scoring using bounded BFS."""

from collections import deque

from tank_ai.constants import DIRS


def bfs_mobility(start_pos, map_w, map_h, walls, limit=8):
    queue = deque([(start_pos, 0)])
    visited = {start_pos}
    count = 0

    while queue:
        curr, depth = queue.popleft()
        if depth >= limit:
            continue

        count += 1
        for dx, dy in DIRS.values():
            nx, ny = curr[0] + dx, curr[1] + dy
            if (
                0 <= nx < map_w
                and 0 <= ny < map_h
                and (nx, ny) not in walls
                and (nx, ny) not in visited
            ):
                visited.add((nx, ny))
                queue.append(((nx, ny), depth + 1))

    return count

