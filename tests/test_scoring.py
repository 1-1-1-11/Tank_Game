"""Tests for is_aiming_enemy and score_candidate."""

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tank_ai.scoring import is_aiming_enemy, score_candidate
from tank_ai.constants import SCORE_INVALID, SCORE_BULLET_HIT


class TestIsAimingEnemy:
    def test_returns_true_when_enemy_in_line_of_sight(self):
        my_pos = (0, 0)
        move = "RIGHT"
        enemy_pos = {(3, 0)}
        map_w, map_h = 10, 10
        walls = set()

        result = is_aiming_enemy(my_pos, move, enemy_pos, map_w, map_h, walls)

        assert result is True

    def test_returns_false_when_wall_blocks(self):
        my_pos = (0, 0)
        move = "RIGHT"
        enemy_pos = {(3, 0)}
        map_w, map_h = 10, 10
        walls = {(1, 0)}

        result = is_aiming_enemy(my_pos, move, enemy_pos, map_w, map_h, walls)

        assert result is False

    def test_returns_false_when_no_enemy_in_range(self):
        my_pos = (0, 0)
        move = "RIGHT"
        enemy_pos = set()
        map_w, map_h = 10, 10
        walls = set()

        result = is_aiming_enemy(my_pos, move, enemy_pos, map_w, map_h, walls)

        assert result is False


class TestScoreCandidate:
    def test_valid_move_returns_non_invalid_score(self):
        move = "RIGHT"
        my_pos = (0, 0)
        my_name = "player1"
        bullets = []
        enemies_pos = {(4, 4)}
        map_w, map_h = 5, 5
        walls = set()
        last_action = None

        score = score_candidate(
            move, my_pos, my_name, bullets, enemies_pos, map_w, map_h, walls, last_action
        )

        assert score > 0, f"Expected positive score for open map, got {score}"

    def test_invalid_move_returns_score_invalid(self):
        move = "LEFT"
        my_pos = (0, 0)
        my_name = "player1"
        bullets = []
        enemies_pos = set()
        map_w, map_h = 5, 5
        walls = set()
        last_action = None

        score = score_candidate(
            move, my_pos, my_name, bullets, enemies_pos, map_w, map_h, walls, last_action
        )

        assert score == SCORE_INVALID

    def test_reverse_move_rejected(self):
        move = "LEFT"
        my_pos = (1, 0)
        my_name = "player1"
        bullets = []
        enemies_pos = set()
        map_w, map_h = 5, 5
        walls = set()
        last_action = "RIGHT"

        score = score_candidate(
            move, my_pos, my_name, bullets, enemies_pos, map_w, map_h, walls, last_action
        )

        assert score == SCORE_INVALID

    def test_bullet_danger_penalized(self):
        move = "RIGHT"
        my_pos = (1, 0)
        my_name = "player1"
        # Bullet at (3,0) moving LEFT toward player's next position (2,0)
        bullets = [
            {"owner": "enemy1", "x": 3, "y": 0, "dx": -1, "dy": 0}
        ]
        enemies_pos = set()
        map_w, map_h = 10, 10
        walls = set()
        last_action = None

        score = score_candidate(
            move, my_pos, my_name, bullets, enemies_pos, map_w, map_h, walls, last_action
        )

        # Score should be significantly lower due to bullet danger penalty
        score_without_bullet = score_candidate(
            move, my_pos, my_name, [], enemies_pos, map_w, map_h, walls, last_action
        )
        assert score < score_without_bullet
        assert score < SCORE_BULLET_HIT + 1000, f"Expected bullet danger penalty, got score {score}"
