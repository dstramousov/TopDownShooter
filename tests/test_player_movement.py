from __future__ import annotations

import math

from topdown.entities.player import Player
from topdown.systems.player_controller import InputState, PlayerController
from topdown.world.collision import CollisionResolver, MovementCommand
from topdown.world.static_maps import build_debug_static_map


def test_diagonal_input_is_normalized() -> None:
    command = PlayerController.build_movement(
        input_state=InputState(move_left=False, move_right=True, move_up=True, move_down=False),
        speed=240.0,
        delta_time=1.0,
    )
    assert math.isclose(math.hypot(command.dx, command.dy), 240.0, rel_tol=1e-6)


def test_player_does_not_cross_outer_wall() -> None:
    tile_map = build_debug_static_map()
    resolver = CollisionResolver(tile_size=64)
    player = Player(x=96.0, y=96.0, width=32.0, height=32.0, speed=240.0, health=100.0, max_health=100.0, hurt_flash_seconds=0.18)

    for _ in range(30):
        resolver.move_player(player, command=MovementCommand(dx=-10.0, dy=0.0), tile_map=tile_map)

    assert player.left >= 64.0
