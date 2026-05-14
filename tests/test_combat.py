from __future__ import annotations

from topdown.core.config import GoreConfig, ImpactDebrisConfig
from topdown.core.types import TileKind
from topdown.systems.aiming import AimController
from topdown.systems.combat import CombatState, CombatSystem, WeaponConfig
from topdown.world.map_model import TileMap


def build_open_map() -> TileMap:
    tile_map = TileMap.create_filled(width=8, height=8, fill_value=TileKind.GRASS, name="test")
    for x in range(tile_map.width):
        tile_map.set_tile(x, 0, TileKind.WALL)
        tile_map.set_tile(x, tile_map.height - 1, TileKind.WALL)
    for y in range(tile_map.height):
        tile_map.set_tile(0, y, TileKind.WALL)
        tile_map.set_tile(tile_map.width - 1, y, TileKind.WALL)
    tile_map.spawn_tile = (2, 2)
    return tile_map


def build_weapon() -> WeaponConfig:
    return WeaponConfig(
        fire_interval_seconds=0.2,
        projectile_speed=2400.0,
        projectile_lifetime_seconds=0.08,
        projectile_radius=3.0,
        muzzle_offset=12.0,
        tracer_every_n_shot=3,
        tracer_probability=1.0,
        tracer_min_fraction=0.4,
        tracer_max_fraction=0.8,
        tracer_lifetime_seconds=0.04,
        impact_mark_lifetime_seconds=8.0,
        impact_mark_max_count=100,
        spread_degrees=0.0,
        max_range=500.0,
        impact_mark_size=8.0,
        bullet_hole_diameter=6.0,
        damage=25.0,
    )


def build_debris() -> ImpactDebrisConfig:
    return ImpactDebrisConfig(
        enabled=True,
        intensity=0.4,
        size_min=1.5,
        size_max=4.0,
        speed_min=60.0,
        speed_max=180.0,
        lifetime_min_seconds=0.08,
        lifetime_max_seconds=0.30,
        max_count=320,
    )


def build_gore(bloodiness: int = 70) -> GoreConfig:
    return GoreConfig(
        bloodiness=bloodiness,
        burst_count_min=4,
        burst_count_max=12,
        burst_size_min=2.0,
        burst_size_max=5.0,
        burst_speed_min=110.0,
        burst_speed_max=290.0,
        burst_lifetime_min_seconds=0.10,
        burst_lifetime_max_seconds=0.42,
        pool_size_min=12.0,
        pool_size_max=28.0,
        pool_growth_seconds=0.22,
        decal_chance=0.45,
        decal_size_min=10.0,
        decal_size_max=24.0,
        decal_lifetime_seconds=45.0,
        max_blood_particles=420,
        max_blood_pools=96,
        max_blood_decals=96,
        kill_freeze_seconds=0.035,
    )


def test_try_fire_creates_hitscan_and_starts_cooldown() -> None:
    system = CombatSystem(weapons={"default": build_weapon()}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(), rng_seed=7)
    state = CombatState(active_weapon_name="default")
    tile_map = build_open_map()
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=128.0, target_y=64.0)

    shot = system.try_fire(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim)

    assert shot.did_fire is True
    assert state.cooldown_remaining > 0.0
    assert state.shot_counter == 1
    assert shot.hit_x > shot.muzzle_x
    assert shot.hit_y == shot.muzzle_y


def test_tracer_is_created_on_every_third_shot() -> None:
    system = CombatSystem(weapons={"default": build_weapon()}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(), rng_seed=1)
    state = CombatState(active_weapon_name="default")
    tile_map = build_open_map()
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=160.0, target_y=64.0)

    for index in range(3):
        shot = system.try_fire(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim)
        assert shot.did_fire is True
        if index < 2:
            assert shot.created_tracer is False
        state.cooldown_remaining = 0.0

    assert shot.created_tracer is True
    assert len(state.tracers) == 1


def test_environment_hit_creates_impact_mark_and_debris() -> None:
    tile_map = build_open_map()
    tile_map.set_tile(4, 2, TileKind.WALL)
    system = CombatSystem(weapons={"default": build_weapon()}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(), rng_seed=5)
    state = CombatState(active_weapon_name="default")
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=160.0, target_y=64.0)

    shot = system.try_fire(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim)

    assert shot.did_fire is True
    assert shot.hit_surface is TileKind.WALL
    assert len(state.impact_marks) == 1
    assert len(state.impact_debris) >= 1


def test_effects_expire_after_update() -> None:
    tile_map = build_open_map()
    tile_map.set_tile(4, 2, TileKind.WALL)
    system = CombatSystem(weapons={"default": build_weapon()}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(), rng_seed=2)
    state = CombatState(active_weapon_name="default")
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=160.0, target_y=64.0)

    for _ in range(3):
        system.try_fire(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim)
        state.cooldown_remaining = 0.0

    assert state.tracers
    assert state.impact_marks
    assert state.impact_debris

    system.update(state=state, delta_time=0.2)
    system.update(state=state, delta_time=10.0)

    assert state.tracers == []
    assert state.impact_marks == []
    assert state.impact_debris == []


def test_hitscan_uses_weapon_max_range_instead_of_projectile_lifetime() -> None:
    tile_map = TileMap.create_filled(width=40, height=8, fill_value=TileKind.GRASS, name="long_range")
    for x in range(tile_map.width):
        tile_map.set_tile(x, 0, TileKind.WALL)
        tile_map.set_tile(x, tile_map.height - 1, TileKind.WALL)
    for y in range(tile_map.height):
        tile_map.set_tile(0, y, TileKind.WALL)
        tile_map.set_tile(tile_map.width - 1, y, TileKind.WALL)
    tile_map.set_tile(30, 2, TileKind.WALL)

    weapon = WeaponConfig(
        fire_interval_seconds=0.2,
        projectile_speed=500.0,
        projectile_lifetime_seconds=0.05,
        projectile_radius=3.0,
        muzzle_offset=12.0,
        tracer_every_n_shot=3,
        tracer_probability=1.0,
        tracer_min_fraction=0.4,
        tracer_max_fraction=0.8,
        tracer_lifetime_seconds=0.04,
        impact_mark_lifetime_seconds=8.0,
        impact_mark_max_count=100,
        spread_degrees=0.0,
        max_range=1200.0,
        impact_mark_size=8.0,
        bullet_hole_diameter=6.0,
        damage=25.0,
    )
    system = CombatSystem(weapons={"default": weapon}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(), rng_seed=11)
    state = CombatState(active_weapon_name="default")
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=1200.0, target_y=64.0)

    shot = system.try_fire(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim)

    assert shot.did_fire is True
    assert shot.hit_surface is TileKind.WALL
    assert shot.hit_x > 900.0
    assert len(state.impact_marks) == 1


def test_preview_shot_reports_distance_to_nearest_obstacle() -> None:
    tile_map = build_open_map()
    tile_map.set_tile(4, 2, TileKind.WALL)
    system = CombatSystem(weapons={"default": build_weapon()}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(), rng_seed=3)
    state = CombatState(active_weapon_name="default")
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=160.0, target_y=64.0)

    preview = system.preview_shot(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim)

    assert preview.hit.hit is True
    assert preview.hit.surface_kind is TileKind.WALL
    assert preview.hit.distance > 0.0
    assert preview.hit.x > preview.muzzle_x


def test_debris_intensity_changes_particle_count() -> None:
    tile_map = build_open_map()
    tile_map.set_tile(4, 2, TileKind.WALL)
    weak_system = CombatSystem(
        weapons={"default": build_weapon()},
        tile_size=32,
        impact_debris_config=ImpactDebrisConfig(True, 0.1, 1.5, 4.0, 60.0, 180.0, 0.08, 0.30, 320),
        gore_config=build_gore(),
        rng_seed=13,
    )
    strong_system = CombatSystem(
        weapons={"default": build_weapon()},
        tile_size=32,
        impact_debris_config=ImpactDebrisConfig(True, 1.0, 1.5, 4.0, 60.0, 180.0, 0.08, 0.30, 320),
        gore_config=build_gore(),
        rng_seed=13,
    )
    weak_state = CombatState(active_weapon_name="default")
    strong_state = CombatState(active_weapon_name="default")
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=160.0, target_y=64.0)

    weak_system.try_fire(state=weak_state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim)
    strong_system.try_fire(state=strong_state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim)

    assert len(weak_state.impact_debris) < len(strong_state.impact_debris)
    assert len(weak_state.impact_debris) <= 3
    assert len(strong_state.impact_debris) >= 15


def test_environment_hit_creates_bullet_hole_and_muzzle_flash() -> None:
    tile_map = build_open_map()
    tile_map.set_tile(4, 2, TileKind.WALL)
    system = CombatSystem(weapons={"default": build_weapon()}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(), rng_seed=17)
    state = CombatState(active_weapon_name="default")
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=160.0, target_y=64.0)

    system.try_fire(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim)

    assert len(state.impact_marks) == 1
    assert state.impact_marks[0].hole_diameter == 6.0
    assert len(state.muzzle_flashes) == 1


def test_muzzle_flash_expires_after_update() -> None:
    tile_map = build_open_map()
    tile_map.set_tile(4, 2, TileKind.WALL)
    system = CombatSystem(weapons={"default": build_weapon()}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(), rng_seed=23)
    state = CombatState(active_weapon_name="default")
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=160.0, target_y=64.0)

    system.try_fire(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim)
    assert state.muzzle_flashes

    system.update(state=state, delta_time=0.2)

    assert state.muzzle_flashes == []


from topdown.entities.enemy import Enemy


def test_hitscan_prefers_enemy_before_wall() -> None:
    tile_map = build_open_map()
    tile_map.set_tile(8, 2, TileKind.WALL)
    system = CombatSystem(weapons={"default": build_weapon()}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(), rng_seed=21)
    state = CombatState(active_weapon_name="default")
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=320.0, target_y=64.0)
    enemies = [
        Enemy(
            x=160.0,
            y=64.0,
            width=28.0,
            height=28.0,
            speed=100.0,
            health=100.0,
            max_health=100.0,
            vision_distance=200.0,
            vision_fov_degrees=70.0,
            stop_distance=40.0,
            attack_damage=10.0,
            attack_interval_seconds=0.8,
            attack_range=40.0,
            corpse_lifetime_seconds=5.0,
        )
    ]

    shot = system.try_fire(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim, enemies=enemies)

    assert shot.did_fire is True
    assert shot.hit_enemy is True
    assert shot.hit_enemy_index == 0
    assert len(state.impact_marks) == 0


def test_enemy_hit_creates_gore_effects_and_freeze() -> None:
    tile_map = build_open_map()
    system = CombatSystem(weapons={"default": build_weapon()}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(100), rng_seed=31)
    state = CombatState(active_weapon_name="default")
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=192.0, target_y=64.0)
    enemies = [Enemy(x=160.0, y=64.0, width=28.0, height=28.0, speed=100.0, health=100.0, max_health=100.0, vision_distance=200.0, vision_fov_degrees=70.0, stop_distance=40.0, attack_damage=10.0, attack_interval_seconds=0.8, attack_range=40.0, corpse_lifetime_seconds=5.0)]

    shot = system.try_fire(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim, enemies=enemies)

    assert shot.hit_enemy is True
    assert shot.kill_freeze_seconds > 0.0
    assert state.blood_particles
    assert state.blood_pools


def test_gore_zero_disables_blood_effects() -> None:
    tile_map = build_open_map()
    system = CombatSystem(weapons={"default": build_weapon()}, tile_size=32, impact_debris_config=build_debris(), gore_config=build_gore(0), rng_seed=41)
    state = CombatState(active_weapon_name="default")
    aim = AimController.build(player_x=64.0, player_y=64.0, target_x=192.0, target_y=64.0)
    enemies = [Enemy(x=160.0, y=64.0, width=28.0, height=28.0, speed=100.0, health=100.0, max_health=100.0, vision_distance=200.0, vision_fov_degrees=70.0, stop_distance=40.0, attack_damage=10.0, attack_interval_seconds=0.8, attack_range=40.0, corpse_lifetime_seconds=5.0)]

    shot = system.try_fire(state=state, tile_map=tile_map, player_x=64.0, player_y=64.0, aim_state=aim, enemies=enemies)

    assert shot.hit_enemy is True
    assert state.blood_particles == []
    assert state.blood_pools == []
