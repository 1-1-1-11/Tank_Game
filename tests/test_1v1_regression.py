import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bots.xjy1v1 import TankAI


def make_state(x, y, walls=None, bullets=None, tanks=None, width=2, height=1):
    me = {"name": "XJY", "x": x, "y": y, "hp": 3, "alive": True}
    return {
        "self": me,
        "map_width": width,
        "map_height": height,
        "walls": list(walls or []),
        "tanks": tanks or [me],
        "bullets": bullets or [],
    }


def test_dead_bot_returns_up_without_updating_last_action():
    """When bot dies, get_action returns UP without updating last_action."""
    ai = TankAI()
    ai.last_action = "RIGHT"
    ai.was_alive = True

    state = make_state(0, 0)
    state["self"]["alive"] = False

    result = ai.get_action(state)

    assert result == "UP"
    assert ai.last_action == "RIGHT"


def test_fallback_prefers_non_wall_non_boundary_when_only_reverse_is_open():
    """When reverse is blocked by wall, bot should pick perpendicular direction not reverse."""
    ai = TankAI()
    ai.last_action = "RIGHT"
    ai.was_alive = True

    # 3x3 map, bot at (1,1), wall at (0,1) blocks LEFT (reverse of RIGHT)
    # UP and DOWN are valid perpendicular moves, LEFT is blocked, RIGHT is forward
    walls = [(0, 1)]
    state = make_state(1, 1, walls=walls, width=3, height=3)

    ai._rebuild_static_maps(3, 3, set(walls))

    result = ai.get_action(state)

    # Bot should NOT pick LEFT (reverse), should pick UP, DOWN, or RIGHT (forward)
    assert result != "LEFT", f"Expected not LEFT (reverse blocked), got {result}"


def test_survival_decisions_avoid_known_traps():
    """Bot should avoid directions that lead to dead ends (traps)."""
    ai = TankAI()
    ai.last_action = "RIGHT"
    ai.was_alive = True

    # Create a map with a dead end at (0,2):
    # - Bot at (1, 2)
    # - Walls at (0,1) and (0,3) make (0,2) a dead end (only exit is back to 1,2)
    # - Going LEFT (reverse) leads to dead end, should be marked as trap
    walls = [(0, 1), (0, 3)]
    state = make_state(1, 2, walls=walls, width=3, height=4)

    ai._rebuild_static_maps(3, 4, set(walls))

    # The trap_lookup should mark LEFT from (1, 2) as a trap
    # since going LEFT leads to (0,2) which is a dead end
    result = ai.get_action(state)

    # Bot should not go LEFT into the trap, should prefer UP, DOWN, or RIGHT
    assert result != "LEFT", f"Expected not LEFT (trap), got {result}"


def test_circle_movement_bonus_for_clockwise_next_direction():
    """When last_action=UP and both RIGHT and LEFT are valid, RIGHT (clockwise) should win."""
    ai = TankAI()
    ai.was_alive = True

    # Map where UP is reverse of last_action (RIGHT), so RIGHT is the clockwise next
    # Bot at (1, 1) in a 3x3 open map
    walls = []
    state = make_state(1, 1, walls=walls, width=3, height=3)

    ai._rebuild_static_maps(3, 3, set(walls))

    # First, set last_action to UP
    ai.last_action = "UP"

    # Both LEFT and RIGHT should be valid moves
    # RIGHT is CLOCKWISE_NEXT of UP, so it should get the circle bonus
    result = ai.get_action(state)

    # Since RIGHT is clockwise next of UP, it should be preferred
    assert result == "RIGHT", f"Expected RIGHT (clockwise next of UP), got {result}"
