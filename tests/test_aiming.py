from __future__ import annotations

import math

from topdown.systems.aiming import AimController


def test_aim_controller_points_to_cursor() -> None:
    aim = AimController.build(player_x=10.0, player_y=10.0, target_x=20.0, target_y=10.0)

    assert math.isclose(aim.direction_x, 1.0)
    assert math.isclose(aim.direction_y, 0.0)
    assert math.isclose(aim.angle_deg, 0.0)


def test_aim_controller_normalizes_diagonal() -> None:
    aim = AimController.build(player_x=0.0, player_y=0.0, target_x=3.0, target_y=3.0)

    expected = math.sqrt(0.5)
    assert math.isclose(aim.direction_x, expected)
    assert math.isclose(aim.direction_y, expected)
    assert math.isclose(aim.angle_deg, 45.0)
