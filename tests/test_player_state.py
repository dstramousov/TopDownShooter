from __future__ import annotations

from topdown.entities.player import Player


def test_player_damage_and_health_ratio() -> None:
    player = Player(x=0.0, y=0.0, width=32.0, height=32.0, speed=100.0, health=100.0, max_health=100.0, hurt_flash_seconds=0.2)

    player.apply_damage(25.0)

    assert player.health == 75.0
    assert player.health_ratio == 0.75
    assert player.hurt_alpha > 0.0


def test_player_dies_at_zero_health() -> None:
    player = Player(x=0.0, y=0.0, width=32.0, height=32.0, speed=100.0, health=10.0, max_health=10.0, hurt_flash_seconds=0.2)

    player.apply_damage(50.0)

    assert player.is_dead is True
    assert player.health == 0.0
