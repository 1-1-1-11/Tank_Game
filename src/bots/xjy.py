import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tank_ai.constants import DIRS, DIR_LIST, SCORE_INVALID
from tank_ai.danger import will_hit_bullet
from tank_ai.mobility import bfs_mobility
from tank_ai.rules import is_valid_move
from tank_ai.scoring import is_aiming_enemy, score_candidate
from tank_ai.state import alive_enemies, enemy_positions, walls_set
from tank_ai.traps import get_survival_depth

logging.basicConfig(level=logging.WARNING, format="%(name)s %(levelname)s: %(message)s")


class TankAI:
    last_action: Optional[str]
    was_alive: bool
    map_w: int
    map_h: int
    walls: Set[Tuple[int, int]]
    static_map_initialized: bool
    memo_depth: dict
    _danger_map_cache: Optional[List[List[float]]]
    _mobility_cache: dict

    def __init__(self) -> None:
        self.last_action = None
        self.was_alive = False

        self.map_w = 0
        self.map_h = 0
        self.walls: Set[Tuple[int, int]] = set()
        self.static_map_initialized = False

        self.memo_depth: dict = {}
        self._danger_map_cache = None
        self._mobility_cache = {}

    def _reset_state(self) -> None:
        self.last_action = None
        self.memo_depth = {}

    def _update_static_map(self, w: int, h: int, walls_list: List[List[int]]) -> None:
        current_walls = walls_set(walls_list)
        if (
            self.map_w == w
            and self.map_h == h
            and self.walls == current_walls
            and self.static_map_initialized
        ):
            return

        self.map_w = w
        self.map_h = h
        self.walls = current_walls
        self.static_map_initialized = True
        self._danger_map_cache = None
        self._mobility_cache = {}

    def _is_valid_move(self, x: int, y: int, move: str, check_reverse: bool = True) -> bool:
        return is_valid_move(
            x,
            y,
            move,
            self.map_w,
            self.map_h,
            self.walls,
            self.last_action,
            check_reverse=check_reverse,
        )

    def _will_hit_bullet(
        self,
        my_next_pos: Tuple[int, int],
        bullets: List[Dict[str, Any]],
        my_name: str,
    ) -> bool:
        return will_hit_bullet(
            my_next_pos,
            bullets,
            my_name,
            self.map_w,
            self.map_h,
            self.walls,
        )

    def _get_survival_depth(
        self,
        start_pos: Tuple[int, int],
        start_move: str,
        max_depth: int = 20,
    ) -> int:
        return get_survival_depth(
            start_pos,
            start_move,
            self.map_w,
            self.map_h,
            self.walls,
            max_depth=max_depth,
        )

    def _bfs_mobility(self, start_pos: Tuple[int, int]) -> int:
        if start_pos not in self._mobility_cache:
            self._mobility_cache[start_pos] = bfs_mobility(start_pos, self.map_w, self.map_h, self.walls)
        return self._mobility_cache[start_pos]

    def _is_aiming_enemy(
        self,
        my_pos: Tuple[int, int],
        move: str,
        enemies_pos: Set[Tuple[int, int]],
    ) -> bool:
        return is_aiming_enemy(my_pos, move, enemies_pos, self.map_w, self.map_h, self.walls)

    def get_action(self, state: Dict[str, Any]) -> str:
        try:
            me = state["self"]

            if not me["alive"]:
                self.was_alive = False
                return "UP"

            if not self.was_alive and me["alive"]:
                self._reset_state()

            self.was_alive = True

            self._update_static_map(state["map_width"], state["map_height"], state["walls"])

            my_pos = (me["x"], me["y"])
            bullets = state["bullets"]
            enemies = alive_enemies(state, me["name"])
            enemies_pos = enemy_positions(enemies)

            candidates = []
            for move in DIR_LIST:
                score = score_candidate(
                    move,
                    my_pos,
                    me["name"],
                    bullets,
                    enemies_pos,
                    self.map_w,
                    self.map_h,
                    self.walls,
                    self.last_action,
                    mobility_cache=self._mobility_cache,
                )
                candidates.append((score, move))

            candidates.sort(key=lambda item: item[0], reverse=True)
            best_score, best_move = candidates[0]

            if best_score == SCORE_INVALID:
                my_x, my_y = my_pos
                for move in DIR_LIST:
                    dx, dy = DIRS[move]
                    nx, ny = my_x + dx, my_y + dy
                    if self._is_valid_move(nx, ny, move, check_reverse=False):
                        best_move = move
                        break

            self.last_action = best_move
            return best_move

        except Exception:
            logging.exception("TankAI.get_action error")
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
        except Exception:
            logging.exception("TankAI I/O loop error")
            print("UP")
            sys.stdout.flush()
