import json
import sys
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tank_ai.constants import (
    CLOCKWISE_NEXT,
    DIRS,
    DIR_LIST,
    OPPOSITE,
)
from tank_ai.danger import get_danger_map, will_hit_bullet
from tank_ai.mobility import bfs_mobility
from tank_ai.rules import is_valid_move
from tank_ai.scoring import score_candidate_1v1
from tank_ai.state import alive_enemies, enemy_positions, walls_set
from tank_ai.traps import get_survival_depth


class TankAI:
    last_action: Optional[str]
    was_alive: bool
    static_walls: Optional[Set[Tuple[int, int]]]
    mobility_map: Optional[List[List[int]]]
    trap_lookup: dict
    _dfs_memo: dict

    def __init__(self) -> None:
        self.last_action = None
        self.was_alive = False
        self.static_walls: Optional[Set[Tuple[int, int]]] = None
        self.mobility_map: Optional[List[List[int]]] = None
        self.trap_lookup: dict = {}
        self._dfs_memo: dict = {}

    def _rebuild_static_maps(
        self,
        w: int,
        h: int,
        walls: Set[Tuple[int, int]],
    ) -> None:
        self.static_walls = walls
        self.mobility_map = [[0] * h for _ in range(w)]
        self.trap_lookup = {}
        for x in range(w):
            for y in range(h):
                if (x, y) not in walls:
                    self.mobility_map[x][y] = bfs_mobility((x, y), w, h, walls)
        self._dfs_memo = {}
        for x in range(w):
            for y in range(h):
                if (x, y) in walls:
                    continue
                for move in DIR_LIST:
                    if not self._can_escape_dfs((x, y), move, w, h, walls, set(), 0):
                        self.trap_lookup[((x, y), move)] = True

    def _can_escape_dfs(
        self,
        pos: Tuple[int, int],
        last_move: str,
        w: int,
        h: int,
        walls: Set[Tuple[int, int]],
        visiting: Set[Tuple[Tuple[int, int], str]],
        depth: int,
    ) -> bool:
        state: Tuple[Tuple[int, int], str] = (pos, last_move)
        if state in self._dfs_memo:
            return self._dfs_memo[state]
        if state in visiting:
            return True
        if depth > 60:
            return True
        visiting.add(state)
        can_escape: bool = False
        rev: Optional[str] = OPPOSITE.get(last_move)
        for move, (dx, dy) in DIRS.items():
            if move == rev:
                continue
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in walls:
                if self._can_escape_dfs((nx, ny), move, w, h, walls, visiting, depth + 1):
                    can_escape = True
                    break
        visiting.remove(state)
        self._dfs_memo[state] = can_escape
        return can_escape

    def get_action(self, state: Dict[str, Any]) -> str:
        try:
            me = state["self"]

            if not self.was_alive and me["alive"]:
                self.last_action = None
            self.was_alive = me["alive"]
            if not me["alive"]:
                return "UP"

            w, h = state["map_width"], state["map_height"]
            walls = walls_set(state["walls"])
            my_pos = (me["x"], me["y"])
            enemies = alive_enemies(state, me["name"])
            enemies_pos = enemy_positions(enemies)

            if self.static_walls != walls:
                self._rebuild_static_maps(w, h, walls)

            danger_map = get_danger_map(walls, state["bullets"], me["name"], w, h)

            candidates = []
            for move in DIR_LIST:
                score = score_candidate_1v1(
                    move,
                    my_pos,
                    me["name"],
                    state["bullets"],
                    enemies_pos,
                    w,
                    h,
                    walls,
                    self.last_action,
                    danger_map,
                    self.trap_lookup,
                    self.mobility_map,
                )
                candidates.append((score, move))

            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1]

        except Exception:
            import traceback
            traceback.print_exc()
            return "UP"


if __name__ == "__main__":
    ai = TankAI()
    if sys.version_info >= (3, 7):
        try:
            sys.stdin.reconfigure(encoding="utf-8")
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            state = json.loads(line)
            action = ai.get_action(state)
            print(action)
            sys.stdout.flush()
            ai.last_action = action
        except Exception:
            print("UP")
            sys.stdout.flush()