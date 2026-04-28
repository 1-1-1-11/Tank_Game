"""State normalization helpers for judge-provided dictionaries."""

from typing import Any, Dict, List, Set, Tuple


def walls_set(walls_list: List[List[int]]) -> Set[Tuple[int, int]]:
    """Convert a list of wall coordinates to a set of (x, y) tuples."""
    return set(tuple(pos) for pos in walls_list)


def alive_enemies(state: Dict[str, Any], my_name: str) -> List[Dict[str, Any]]:
    """Return all enemy tanks that are currently alive."""
    return [
        tank
        for tank in state["tanks"]
        if tank["name"] != my_name and tank["alive"]
    ]


def enemy_positions(enemies: List[Dict[str, Any]]) -> Set[Tuple[int, int]]:
    """Extract positions from a list of enemy tank dicts."""
    return {(tank["x"], tank["y"]) for tank in enemies}


def enemy_positions_from_tanks(tanks: List[Dict[str, Any]]) -> Set[Tuple[int, int]]:
    """Extract positions from a list of tank dicts (including self)."""
    return {(tank["x"], tank["y"]) for tank in tanks if tank["alive"]}

