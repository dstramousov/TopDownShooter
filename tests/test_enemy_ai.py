from __future__ import annotations

from topdown.entities.enemy import Enemy
from topdown.entities.player import Player
from topdown.world.collision import CollisionResolver
from topdown.world.map_model import TileMap
from topdown.core.types import TileKind
from topdown.systems.enemy_ai import EnemyAiSystem


def build_map() -> TileMap:
    tile_map = TileMap.create_filled(width=12, height=12, fill_value=TileKind.GRASS, name="enemy_test")
    for x in range(tile_map.width):
        tile_map.set_tile(x, 0, TileKind.WALL)
        tile_map.set_tile(x, tile_map.height - 1, TileKind.WALL)
    for y in range(tile_map.height):
        tile_map.set_tile(0, y, TileKind.WALL)
        tile_map.set_tile(tile_map.width - 1, y, TileKind.WALL)
    return tile_map


def build_enemy() -> Enemy:
    return Enemy(
        x=128.0,
        y=128.0,
        width=32.0,
        height=32.0,
        speed=100.0,
        health=100.0,
        max_health=100.0,
        vision_distance=220.0,
        vision_fov_degrees=70.0,
        stop_distance=48.0,
        attack_damage=12.0,
        attack_interval_seconds=0.8,
        attack_range=40.0,
        corpse_lifetime_seconds=5.0,
        memory_seconds=1.35,
        strafe_speed_multiplier=0.55,
        separation_distance=42.0,
        separation_strength=0.9,
        search_turn_speed_degrees=180.0,
        facing_angle_deg=0.0,
    )


def build_player(x: float, y: float) -> Player:
    return Player(x=x, y=y, width=32.0, height=32.0, speed=0.0, health=100.0, max_health=100.0, hurt_flash_seconds=0.18)


def test_enemy_sees_player_inside_fov_without_obstacle() -> None:
    tile_map = build_map()
    enemy = build_enemy()
    player = build_player(220.0, 128.0)
    system = EnemyAiSystem(tile_size=32, collision_resolver=CollisionResolver(tile_size=32))

    assert system.can_see_player(enemy, player, tile_map) is True


def test_enemy_does_not_see_player_outside_fov_or_behind_wall() -> None:
    tile_map = build_map()
    tile_map.set_tile(5, 5, TileKind.WALL)
    enemy = build_enemy()
    player = build_player(220.0, 220.0)
    system = EnemyAiSystem(tile_size=32, collision_resolver=CollisionResolver(tile_size=32))

    assert system.can_see_player(enemy, player, tile_map) is False

    enemy.update_facing_from_point(player.x, player.y)
    assert system.can_see_player(enemy, player, tile_map) is False


def test_enemy_melee_attack_returns_damage_when_in_range() -> None:
    tile_map = build_map()
    enemy = build_enemy()
    player = build_player(156.0, 128.0)
    system = EnemyAiSystem(tile_size=32, collision_resolver=CollisionResolver(tile_size=32))

    damage = system.update([enemy], player, tile_map, delta_time=0.016)

    assert damage == enemy.attack_damage
    assert enemy.state == "attack"
    assert enemy.attack_cooldown_remaining > 0.0


def test_enemy_searches_last_seen_position_after_losing_sight() -> None:
    tile_map = build_map()
    enemy = build_enemy()
    player = build_player(220.0, 128.0)
    system = EnemyAiSystem(tile_size=32, collision_resolver=CollisionResolver(tile_size=32))

    system.update([enemy], player, tile_map, delta_time=0.016)
    tile_map.set_tile(5, 4, TileKind.WALL)
    tile_map.set_tile(5, 5, TileKind.WALL)
    tile_map.set_tile(5, 6, TileKind.WALL)

    damage = system.update([enemy], player, tile_map, delta_time=0.1)

    assert damage == 0.0
    assert enemy.state in {"search", "investigate"}
    assert enemy.memory_remaining > 0.0


def test_enemy_separation_pushes_neighbors_apart() -> None:
    tile_map = build_map()
    enemy_a = build_enemy()
    enemy_b = build_enemy()
    enemy_b.x += 8.0
    enemy_b.y += 4.0
    player = build_player(220.0, 128.0)
    system = EnemyAiSystem(tile_size=32, collision_resolver=CollisionResolver(tile_size=32))

    old_distance = ((enemy_a.x - enemy_b.x) ** 2 + (enemy_a.y - enemy_b.y) ** 2) ** 0.5
    system.update([enemy_a, enemy_b], player, tile_map, delta_time=0.1)
    new_distance = ((enemy_a.x - enemy_b.x) ** 2 + (enemy_a.y - enemy_b.y) ** 2) ** 0.5

    assert new_distance > old_distance
