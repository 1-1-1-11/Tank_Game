from bots.xjy import TankAI


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


def test_fallback_prefers_non_wall_non_boundary_when_only_reverse_is_open():
    ai = TankAI()
    ai.last_action = "RIGHT"
    ai.was_alive = True

    assert ai.get_action(make_state(1, 0)) == "LEFT"


def test_dead_bot_returns_up_without_updating_last_action():
    ai = TankAI()
    ai.last_action = "RIGHT"
    state = make_state(0, 0)
    state["self"]["alive"] = False

    assert ai.get_action(state) == "UP"
    assert ai.last_action == "RIGHT"

