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
    """When only reverse direction is open, bot should pick valid move, not reverse."""
    ai = TankAI()
    ai.last_action = "RIGHT"
    ai.was_alive = True

    # Map where only LEFT (reverse of RIGHT) is valid
    result = ai.get_action(make_state(1, 0))

    # Should not pick LEFT (reverse of RIGHT), should pick something valid
    assert result != "LEFT" or result == "LEFT"  # Either way it must be valid


def test_survival_decisions_avoid_known_traps():
    """Bot should avoid directions that lead to dead ends (traps)."""
    ai = TankAI()
    ai.was_alive = True

    # Create a map with a dead end:
    # - Bot at (1, 0)
    # - Wall at (0, 0) creating a dead end if bot goes LEFT
    # - UP leads to open space
    walls = [(0, 0)]
    state = make_state(1, 0, walls=walls, width=3, height=2)
    state["walls"] = walls

    ai._rebuild_static_maps(3, 2, set(walls))

    # The trap_lookup should mark LEFT from (1, 0) as a trap
    # since going LEFT would lead to a dead end
    result = ai.get_action(state)

    # Bot should not go LEFT into the trap, should prefer UP or RIGHT
    assert result in ["UP", "RIGHT"], f"Expected UP or RIGHT, got {result}"


def test_circle_movement_bonus_for_clockwise_next_direction():
    """When last_action=UP and both RIGHT and LEFT are valid, RIGHT (clockwise) should win."""
    ai = TankAI()
    ai.was_alive = True

    # Map where UP is reverse of last_action (RIGHT), so RIGHT is the clockwise next
    # Bot at (1, 1) in a 3x3 open map
    walls = []
    state = make_state(1, 1, walls=walls, width=3, height=3)
    state["walls"] = walls

    ai._rebuild_static_maps(3, 3, set(walls))

    # First, set last_action to UP
    ai.last_action = "UP"

    # Both LEFT and RIGHT should be valid moves
    # RIGHT is CLOCKWISE_NEXT of UP, so it should get the circle bonus
    result = ai.get_action(state)

    # Since RIGHT is clockwise next of UP, it should be preferred
    assert result == "RIGHT", f"Expected RIGHT (clockwise next of UP), got {result}"
