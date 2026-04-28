"""Mobility scoring using bounded BFS."""

from collections import deque
from typing import Deque, Set, Tuple

from tank_ai.constants import BFS_MOBILITY_LIMIT, DIRS


def bfs_mobility(
    start_pos: Tuple[int, int],
    map_w: int,
    map_h: int,
    walls: Set[Tuple[int, int]],
    limit: int = BFS_MOBILITY_LIMIT,
) -> int:
    """Calculate mobility (reachable cells) from start_pos using bounded BFS."""
    queue: Deque[Tuple[Tuple[int, int], int]] = deque([(start_pos, 0)])
    visited: Set[Tuple[int, int]] = {start_pos}
    count: int = 0

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

