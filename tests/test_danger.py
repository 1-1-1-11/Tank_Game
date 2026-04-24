from tank_ai.danger import will_hit_bullet


def test_bullet_hits_on_first_step():
    bullets = [{"x": 1, "y": 1, "dx": 1, "dy": 0, "owner": "enemy"}]

    assert will_hit_bullet((2, 1), bullets, "me", 5, 5, set())


def test_bullet_hits_on_second_step():
    bullets = [{"x": 1, "y": 1, "dx": 1, "dy": 0, "owner": "enemy"}]

    assert will_hit_bullet((3, 1), bullets, "me", 5, 5, set())


def test_wall_blocks_bullet_before_second_step():
    bullets = [{"x": 1, "y": 1, "dx": 1, "dy": 0, "owner": "enemy"}]

    assert not will_hit_bullet((3, 1), bullets, "me", 5, 5, {(2, 1)})


def test_own_bullet_is_ignored():
    bullets = [{"x": 1, "y": 1, "dx": 1, "dy": 0, "owner": "me"}]

    assert not will_hit_bullet((2, 1), bullets, "me", 5, 5, set())

