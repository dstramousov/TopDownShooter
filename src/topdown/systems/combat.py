from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

from topdown.core.config import GoreConfig, ImpactDebrisConfig, MuzzleSmokeConfig
from topdown.core.types import TileKind
from topdown.entities.effects import (
    BloodDecal,
    BloodParticle,
    BloodPool,
    ImpactDebrisParticle,
    ImpactMark,
    MuzzleFlashEffect,
    MuzzleSmokeParticle,
    ShellCasing,
    TracerEffect,
)
from topdown.entities.enemy import Enemy
from topdown.systems.aiming import AimState
from topdown.world.collision import CollisionResolver
from topdown.world.map_model import TileMap
from topdown.world.raycast import RaycastHit, RaycastResolver


@dataclass(slots=True, frozen=True)
class WeaponConfig:
    """Configuration for a single weapon definition."""

    fire_interval_seconds: float
    projectile_speed: float
    projectile_lifetime_seconds: float
    projectile_radius: float
    muzzle_offset: float
    tracer_every_n_shot: int
    tracer_probability: float
    tracer_min_fraction: float
    tracer_max_fraction: float
    tracer_lifetime_seconds: float
    tracer_width: float = 3.0
    tracer_core_width: float = 1.4
    impact_mark_lifetime_seconds: float = 8.0
    impact_mark_max_count: int = 120
    spread_degrees: float = 0.0
    max_range: float = 760.0
    impact_mark_size: float = 8.0
    bullet_hole_diameter: float = 6.0
    damage: float = 30.0
    muzzle_side_offset: float = 11.0
    muzzle_flash_size: float = 22.0
    muzzle_flash_lifetime_seconds: float = 0.05
    recoil_distance: float = 7.0
    recoil_recovery_seconds: float = 0.07
    screen_shake_magnitude: float = 2.5
    screen_shake_duration_seconds: float = 0.06
    shell_enabled: bool = True
    shell_size: float = 4.0
    shell_speed_min: float = 90.0
    shell_speed_max: float = 160.0
    shell_lifetime_seconds: float = 1.0
    shell_bounce_damping: float = 0.45
    shell_max_bounces: int = 2


@dataclass(slots=True)
class ShotResult:
    """Structured result of a single fired shot."""

    did_fire: bool
    muzzle_x: float = 0.0
    muzzle_y: float = 0.0
    hit_x: float = 0.0
    hit_y: float = 0.0
    hit_surface: TileKind = TileKind.VOID
    created_tracer: bool = False
    hit_enemy: bool = False
    hit_enemy_index: int | None = None
    damage: float = 0.0
    recoil_distance: float = 0.0
    recoil_recovery_seconds: float = 0.0
    recoil_angle_deg: float = 0.0
    screen_shake_magnitude: float = 0.0
    screen_shake_duration_seconds: float = 0.0
    enemy_impulse_x: float = 0.0
    enemy_impulse_y: float = 0.0
    kill_freeze_seconds: float = 0.0


@dataclass(slots=True, frozen=True)
class AimPreview:
    """Debug preview of the current hitscan path."""

    muzzle_x: float
    muzzle_y: float
    hit: RaycastHit


@dataclass(slots=True)
class CombatState:
    """Mutable combat runtime state."""

    cooldown_remaining: float = 0.0
    shot_counter: int = 0
    active_weapon_name: str = "shotgun"
    tracers: list[TracerEffect] = field(default_factory=list)
    impact_marks: list[ImpactMark] = field(default_factory=list)
    impact_debris: list[ImpactDebrisParticle] = field(default_factory=list)
    blood_particles: list[BloodParticle] = field(default_factory=list)
    blood_pools: list[BloodPool] = field(default_factory=list)
    blood_decals: list[BloodDecal] = field(default_factory=list)
    muzzle_flashes: list[MuzzleFlashEffect] = field(default_factory=list)
    muzzle_smoke: list[MuzzleSmokeParticle] = field(default_factory=list)
    shell_casings: list[ShellCasing] = field(default_factory=list)


class CombatSystem:
    """Manage hitscan weapons, visual tracers, shell casings, and impact effects."""

    def __init__(
        self,
        weapons: dict[str, WeaponConfig],
        tile_size: int,
        impact_debris_config: ImpactDebrisConfig,
        gore_config: GoreConfig,
        collision_resolver: CollisionResolver | None = None,
        muzzle_smoke_config: MuzzleSmokeConfig | None = None,
        rng_seed: int = 1337,
    ) -> None:
        self._weapons = weapons
        self._raycast = RaycastResolver(tile_size=tile_size)
        self._collision_resolver = collision_resolver
        self._impact_debris_config = impact_debris_config
        self._gore_config = gore_config
        self._muzzle_smoke_config = muzzle_smoke_config or MuzzleSmokeConfig(
            enabled=False,
            count_min=0,
            count_max=0,
            size_min=0.0,
            size_max=0.0,
            speed_min=0.0,
            speed_max=0.0,
            lifetime_min_seconds=0.0,
            lifetime_max_seconds=0.0,
            max_count=0,
        )
        self._random = random.Random(rng_seed)

    def get_weapon(self, weapon_name: str) -> WeaponConfig:
        try:
            return self._weapons[weapon_name]
        except KeyError as exc:
            raise KeyError(f"Unknown weapon: {weapon_name}") from exc

    def update(self, state: CombatState, tile_map: TileMap | None = None, delta_time: float = 0.0) -> None:
        state.cooldown_remaining = max(0.0, state.cooldown_remaining - delta_time)
        state.tracers = self._update_effects(state.tracers, delta_time)
        state.impact_marks = self._update_effects(state.impact_marks, delta_time)
        state.impact_debris = self._update_effects(state.impact_debris, delta_time)
        state.blood_particles = self._update_effects(state.blood_particles, delta_time)
        state.blood_pools = self._update_effects(state.blood_pools, delta_time)
        state.blood_decals = self._update_effects(state.blood_decals, delta_time)
        state.muzzle_flashes = self._update_effects(state.muzzle_flashes, delta_time)
        state.muzzle_smoke = self._update_effects(state.muzzle_smoke, delta_time)
        if tile_map is not None:
            self._update_shell_casings(state.shell_casings, tile_map, delta_time)
            state.shell_casings = [shell for shell in state.shell_casings if shell.is_alive]

    def preview_shot(
        self,
        state: CombatState,
        tile_map: TileMap,
        player_x: float,
        player_y: float,
        aim_state: AimState,
    ) -> AimPreview:
        weapon = self.get_weapon(state.active_weapon_name)
        direction_x, direction_y = self._normalize_direction(aim_state.direction_x, aim_state.direction_y)
        muzzle_x, muzzle_y = self._resolve_muzzle_position(player_x, player_y, direction_x, direction_y, weapon)
        hit = self._raycast.cast(
            tile_map=tile_map,
            origin_x=muzzle_x,
            origin_y=muzzle_y,
            direction_x=direction_x,
            direction_y=direction_y,
            max_distance=weapon.max_range,
        )
        return AimPreview(muzzle_x=muzzle_x, muzzle_y=muzzle_y, hit=hit)


    def enemy_fire(
        self,
        state: CombatState,
        tile_map: TileMap,
        enemy: Enemy,
        target_x: float,
        target_y: float,
    ) -> ShotResult:
        """Fire a hitscan shot for an enemy using its configured weapon."""
        weapon = self.get_weapon(enemy.fire_weapon_name)
        direction_x = target_x - enemy.x
        direction_y = target_y - enemy.y
        direction_x, direction_y = self._normalize_direction(direction_x, direction_y)
        if direction_x == 0.0 and direction_y == 0.0:
            return ShotResult(did_fire=False)

        muzzle_x, muzzle_y = self._resolve_muzzle_position(enemy.x, enemy.y, direction_x, direction_y, weapon)
        environment_hit = self._raycast.cast(
            tile_map=tile_map,
            origin_x=muzzle_x,
            origin_y=muzzle_y,
            direction_x=direction_x,
            direction_y=direction_y,
            max_distance=min(enemy.fire_range, weapon.max_range),
        )
        player_hit = self._line_hits_circle(
            center_x=target_x,
            center_y=target_y,
            radius=12.0,
            origin_x=muzzle_x,
            origin_y=muzzle_y,
            direction_x=direction_x,
            direction_y=direction_y,
            max_distance=environment_hit.distance if environment_hit.hit else min(enemy.fire_range, weapon.max_range),
        )
        final_hit = environment_hit
        if player_hit is not None:
            hit_distance = player_hit
            final_hit = RaycastHit(
                hit=True,
                x=muzzle_x + direction_x * hit_distance,
                y=muzzle_y + direction_y * hit_distance,
                distance=hit_distance,
                tile_x=int(target_x // self._raycast._tile_size),
                tile_y=int(target_y // self._raycast._tile_size),
                surface_kind=TileKind.VOID,
            )

        state.shot_counter += 1
        shot_angle_deg = math.degrees(math.atan2(direction_y, direction_x))
        self._create_muzzle_flash(state, weapon, shot_angle_deg, muzzle_x, muzzle_y)
        self._create_muzzle_smoke(state, direction_x, direction_y, muzzle_x, muzzle_y)
        self._maybe_create_shell_casing(state, tile_map, weapon, direction_x, direction_y, muzzle_x, muzzle_y)
        self._maybe_create_tracer(state, weapon, muzzle_x, muzzle_y, final_hit.x, final_hit.y)
        if player_hit is None:
            self._maybe_create_impact_mark(state, weapon, final_hit)
            self._maybe_create_impact_debris(state, final_hit)

        return ShotResult(
            did_fire=True,
            muzzle_x=muzzle_x,
            muzzle_y=muzzle_y,
            hit_x=final_hit.x,
            hit_y=final_hit.y,
            hit_surface=final_hit.surface_kind,
            damage=enemy.attack_damage if player_hit is not None else 0.0,
            screen_shake_magnitude=weapon.screen_shake_magnitude * 0.35,
            screen_shake_duration_seconds=weapon.screen_shake_duration_seconds,
        )

    def try_fire(
        self,
        state: CombatState,
        tile_map: TileMap,
        player_x: float,
        player_y: float,
        aim_state: AimState,
        enemies: list[Enemy] | None = None,
    ) -> ShotResult:
        if state.cooldown_remaining > 0.0:
            return ShotResult(did_fire=False)

        weapon = self.get_weapon(state.active_weapon_name)
        spread_radians = math.radians(self._random.uniform(-weapon.spread_degrees, weapon.spread_degrees))
        cos_angle = math.cos(spread_radians)
        sin_angle = math.sin(spread_radians)
        direction_x = aim_state.direction_x * cos_angle - aim_state.direction_y * sin_angle
        direction_y = aim_state.direction_x * sin_angle + aim_state.direction_y * cos_angle
        direction_x, direction_y = self._normalize_direction(direction_x, direction_y)
        if direction_x == 0.0 and direction_y == 0.0:
            return ShotResult(did_fire=False)

        muzzle_x, muzzle_y = self._resolve_muzzle_position(player_x, player_y, direction_x, direction_y, weapon)
        environment_hit = self._raycast.cast(
            tile_map=tile_map,
            origin_x=muzzle_x,
            origin_y=muzzle_y,
            direction_x=direction_x,
            direction_y=direction_y,
            max_distance=weapon.max_range,
        )
        final_hit = environment_hit
        enemy_hit_index = self._find_enemy_hit(
            enemies=enemies or [],
            origin_x=muzzle_x,
            origin_y=muzzle_y,
            direction_x=direction_x,
            direction_y=direction_y,
            max_distance=min(environment_hit.distance, weapon.max_range) if environment_hit.hit else weapon.max_range,
        )
        enemy_impulse_x = 0.0
        enemy_impulse_y = 0.0
        if enemy_hit_index is not None:
            enemy = (enemies or [])[enemy_hit_index]
            enemy_distance = self._circle_hit_distance(enemy, muzzle_x, muzzle_y, direction_x, direction_y)
            final_hit = RaycastHit(
                hit=True,
                x=muzzle_x + direction_x * enemy_distance,
                y=muzzle_y + direction_y * enemy_distance,
                distance=enemy_distance,
                tile_x=int(enemy.x // self._raycast._tile_size),
                tile_y=int(enemy.y // self._raycast._tile_size),
                surface_kind=TileKind.VOID,
            )
            enemy_impulse_x = direction_x * (80.0 + weapon.damage * 1.15)
            enemy_impulse_y = direction_y * (80.0 + weapon.damage * 1.15)

        state.cooldown_remaining = weapon.fire_interval_seconds
        state.shot_counter += 1
        shot_angle_deg = math.degrees(math.atan2(direction_y, direction_x))
        self._create_muzzle_flash(state, weapon, shot_angle_deg, muzzle_x, muzzle_y)
        self._create_muzzle_smoke(state, direction_x, direction_y, muzzle_x, muzzle_y)
        self._maybe_create_shell_casing(state, tile_map, weapon, direction_x, direction_y, muzzle_x, muzzle_y)
        created_tracer = self._maybe_create_tracer(state, weapon, muzzle_x, muzzle_y, final_hit.x, final_hit.y)

        if enemy_hit_index is None:
            self._maybe_create_impact_mark(state, weapon, final_hit)
            self._maybe_create_impact_debris(state, final_hit)
        else:
            self._create_enemy_gore(state, tile_map, final_hit.x, final_hit.y, direction_x, direction_y)

        return ShotResult(
            did_fire=True,
            muzzle_x=muzzle_x,
            muzzle_y=muzzle_y,
            hit_x=final_hit.x,
            hit_y=final_hit.y,
            hit_surface=final_hit.surface_kind,
            created_tracer=created_tracer,
            hit_enemy=enemy_hit_index is not None,
            hit_enemy_index=enemy_hit_index,
            damage=weapon.damage,
            recoil_distance=weapon.recoil_distance,
            recoil_recovery_seconds=weapon.recoil_recovery_seconds,
            recoil_angle_deg=shot_angle_deg,
            screen_shake_magnitude=weapon.screen_shake_magnitude,
            screen_shake_duration_seconds=weapon.screen_shake_duration_seconds,
            enemy_impulse_x=enemy_impulse_x,
            enemy_impulse_y=enemy_impulse_y,
            kill_freeze_seconds=self._gore_config.kill_freeze_seconds if enemy_hit_index is not None else 0.0,
        )

    def _create_enemy_gore(
        self,
        state: CombatState,
        tile_map: TileMap,
        hit_x: float,
        hit_y: float,
        direction_x: float,
        direction_y: float,
    ) -> None:
        gore = self._gore_config
        intensity = max(0.0, min(1.0, gore.bloodiness / 100.0))
        if intensity <= 0.0:
            return
        count_min = max(1, round(gore.burst_count_min * (0.35 + intensity * 0.9)))
        count_max = max(count_min, round(gore.burst_count_max * (0.35 + intensity * 1.1)))
        count = self._random.randint(count_min, count_max)
        base_angle = math.atan2(direction_y, direction_x)
        for _ in range(count):
            drift_angle = base_angle + math.radians(self._random.uniform(-70.0, 70.0))
            speed = self._random.uniform(gore.burst_speed_min, gore.burst_speed_max) * (0.5 + intensity * 0.8)
            size = self._random.uniform(gore.burst_size_min, gore.burst_size_max) * (0.75 + intensity * 0.6)
            lifetime = self._random.uniform(gore.burst_lifetime_min_seconds, gore.burst_lifetime_max_seconds)
            state.blood_particles.append(
                BloodParticle(
                    x=hit_x + self._random.uniform(-2.0, 2.0),
                    y=hit_y + self._random.uniform(-2.0, 2.0),
                    velocity_x=math.cos(drift_angle) * speed,
                    velocity_y=math.sin(drift_angle) * speed,
                    size=size,
                    lifetime_seconds=lifetime,
                )
            )
        overflow = len(state.blood_particles) - gore.max_blood_particles
        if overflow > 0:
            del state.blood_particles[:overflow]

        pool_size = self._random.uniform(gore.pool_size_min, gore.pool_size_max) * (0.45 + intensity * 0.85)
        state.blood_pools.append(BloodPool(x=hit_x, y=hit_y, size=pool_size, growth_seconds=gore.pool_growth_seconds))
        overflow = len(state.blood_pools) - gore.max_blood_pools
        if overflow > 0:
            del state.blood_pools[:overflow]

        if self._random.random() <= gore.decal_chance * intensity:
            wall_hit = self._raycast.cast(
                tile_map=tile_map,
                origin_x=hit_x,
                origin_y=hit_y,
                direction_x=direction_x,
                direction_y=direction_y,
                max_distance=112.0,
            )
            if wall_hit.hit and self._is_solid_environment_hit(wall_hit):
                size = self._random.uniform(gore.decal_size_min, gore.decal_size_max) * (0.7 + intensity * 0.6)
                angle_deg = math.degrees(base_angle) + self._random.uniform(-28.0, 28.0)
                state.blood_decals.append(
                    BloodDecal(
                        x=wall_hit.x,
                        y=wall_hit.y,
                        angle_deg=angle_deg,
                        size=size,
                        lifetime_seconds=gore.decal_lifetime_seconds,
                    )
                )
                overflow = len(state.blood_decals) - gore.max_blood_decals
                if overflow > 0:
                    del state.blood_decals[:overflow]

    def _create_muzzle_flash(self, state: CombatState, weapon: WeaponConfig, angle_deg: float, muzzle_x: float, muzzle_y: float) -> None:
        size = weapon.muzzle_flash_size * self._random.uniform(0.92, 1.14)
        state.muzzle_flashes.append(
            MuzzleFlashEffect(
                x=muzzle_x,
                y=muzzle_y,
                angle_deg=angle_deg,
                size=size,
                lifetime_seconds=weapon.muzzle_flash_lifetime_seconds,
                variant=self._random.randint(0, 2),
            )
        )
        overflow = len(state.muzzle_flashes) - 14
        if overflow > 0:
            del state.muzzle_flashes[:overflow]

    def _maybe_create_tracer(self, state: CombatState, weapon: WeaponConfig, muzzle_x: float, muzzle_y: float, hit_x: float, hit_y: float) -> bool:
        every_n = max(1, weapon.tracer_every_n_shot)
        if state.shot_counter % every_n != 0:
            return False
        if self._random.random() > weapon.tracer_probability:
            return False
        end_x, end_y = self._raycast.build_partial_segment(
            origin_x=muzzle_x,
            origin_y=muzzle_y,
            hit_x=hit_x,
            hit_y=hit_y,
            min_fraction=weapon.tracer_min_fraction,
            max_fraction=weapon.tracer_max_fraction,
            random_value=self._random.random(),
        )
        state.tracers.append(
            TracerEffect(
                start_x=muzzle_x,
                start_y=muzzle_y,
                end_x=end_x,
                end_y=end_y,
                width=weapon.tracer_width,
                core_width=weapon.tracer_core_width,
                lifetime_seconds=weapon.tracer_lifetime_seconds,
            )
        )
        return True

    def _create_muzzle_smoke(self, state: CombatState, direction_x: float, direction_y: float, muzzle_x: float, muzzle_y: float) -> None:
        smoke = self._muzzle_smoke_config
        if not smoke.enabled:
            return
        count = self._random.randint(smoke.count_min, smoke.count_max)
        for _ in range(count):
            drift_angle = math.atan2(direction_y, direction_x) + math.radians(self._random.uniform(-18.0, 18.0))
            speed = self._random.uniform(smoke.speed_min, smoke.speed_max)
            size = self._random.uniform(smoke.size_min, smoke.size_max)
            lifetime = self._random.uniform(smoke.lifetime_min_seconds, smoke.lifetime_max_seconds)
            state.muzzle_smoke.append(
                MuzzleSmokeParticle(
                    x=muzzle_x + self._random.uniform(-1.5, 1.5),
                    y=muzzle_y + self._random.uniform(-1.5, 1.5),
                    velocity_x=math.cos(drift_angle) * speed,
                    velocity_y=math.sin(drift_angle) * speed,
                    size=size,
                    lifetime_seconds=lifetime,
                )
            )
        overflow = len(state.muzzle_smoke) - smoke.max_count
        if overflow > 0:
            del state.muzzle_smoke[:overflow]

    def _maybe_create_shell_casing(self, state: CombatState, tile_map: TileMap, weapon: WeaponConfig, direction_x: float, direction_y: float, muzzle_x: float, muzzle_y: float) -> None:
        if not weapon.shell_enabled:
            return
        right_x = -direction_y
        right_y = direction_x
        ejection_sign = -1.0
        base_speed = self._random.uniform(weapon.shell_speed_min, weapon.shell_speed_max)
        lateral_speed = base_speed * ejection_sign
        forward_speed = self._random.uniform(-26.0, 22.0)
        shell = ShellCasing(
            x=muzzle_x + right_x * (weapon.muzzle_side_offset * 0.35),
            y=muzzle_y + right_y * (weapon.muzzle_side_offset * 0.35),
            velocity_x=right_x * lateral_speed + direction_x * forward_speed,
            velocity_y=right_y * lateral_speed + direction_y * forward_speed,
            angle_deg=self._random.uniform(0.0, 180.0),
            angular_velocity_deg=self._random.uniform(-520.0, 520.0),
            size=weapon.shell_size,
            lifetime_seconds=weapon.shell_lifetime_seconds,
            bounce_damping=weapon.shell_bounce_damping,
            max_bounces=weapon.shell_max_bounces,
        )
        if self._shell_is_inside_wall(tile_map, shell.x, shell.y):
            return
        state.shell_casings.append(shell)
        overflow = len(state.shell_casings) - 48
        if overflow > 0:
            del state.shell_casings[:overflow]

    def _maybe_create_impact_mark(self, state: CombatState, weapon: WeaponConfig, hit: RaycastHit) -> None:
        if not self._is_solid_environment_hit(hit):
            return
        angle_deg = self._random.uniform(0.0, 180.0)
        state.impact_marks.append(
            ImpactMark(
                x=hit.x,
                y=hit.y,
                surface_kind=hit.surface_kind,
                angle_deg=angle_deg,
                size=weapon.impact_mark_size,
                hole_diameter=weapon.bullet_hole_diameter,
                lifetime_seconds=weapon.impact_mark_lifetime_seconds,
            )
        )
        overflow = len(state.impact_marks) - weapon.impact_mark_max_count
        if overflow > 0:
            del state.impact_marks[:overflow]

    def _maybe_create_impact_debris(self, state: CombatState, hit: RaycastHit) -> None:
        debris = self._impact_debris_config
        if not debris.enabled or not self._is_solid_environment_hit(hit):
            return
        count = self._resolve_debris_count(debris.intensity)
        for _ in range(count):
            angle_radians = self._random.uniform(0.0, math.tau)
            speed = self._random.uniform(debris.speed_min, debris.speed_max)
            size = self._random.uniform(debris.size_min, debris.size_max)
            lifetime = self._random.uniform(debris.lifetime_min_seconds, debris.lifetime_max_seconds)
            state.impact_debris.append(
                ImpactDebrisParticle(
                    x=hit.x,
                    y=hit.y,
                    velocity_x=math.cos(angle_radians) * speed,
                    velocity_y=math.sin(angle_radians) * speed,
                    size=size,
                    angle_deg=self._random.uniform(0.0, 180.0),
                    surface_kind=hit.surface_kind,
                    lifetime_seconds=lifetime,
                    drag=6.0,
                )
            )
        overflow = len(state.impact_debris) - debris.max_count
        if overflow > 0:
            del state.impact_debris[:overflow]

    def _update_shell_casings(self, shell_casings: list[ShellCasing], tile_map: TileMap, delta_time: float) -> None:
        tile_size = float(self._raycast._tile_size)
        for shell in shell_casings:
            prev_x = shell.x
            prev_y = shell.y
            shell.update(delta_time)
            shell.velocity_y += 160.0 * delta_time
            if shell.bounce_count >= shell.max_bounces:
                continue
            if self._shell_is_inside_wall(tile_map, shell.x, prev_y):
                shell.x = prev_x
                shell.velocity_x = -shell.velocity_x * shell.bounce_damping
                shell.bounce_count += 1
            if self._shell_is_inside_wall(tile_map, shell.x, shell.y):
                shell.y = prev_y
                shell.velocity_y = -shell.velocity_y * shell.bounce_damping
                shell.bounce_count += 1
            shell.x = min(max(shell.x, tile_size * 0.5), tile_map.width * tile_size - tile_size * 0.5)
            shell.y = min(max(shell.y, tile_size * 0.5), tile_map.height * tile_size - tile_size * 0.5)

    def _shell_is_inside_wall(self, tile_map: TileMap, x: float, y: float) -> bool:
        tile_x = int(x // self._raycast._tile_size)
        tile_y = int(y // self._raycast._tile_size)
        return tile_map.in_bounds(tile_x, tile_y) and not tile_map.is_walkable(tile_x, tile_y)

    @staticmethod
    def _update_effects(effects: list, delta_time: float) -> list:
        alive_effects: list = []
        for effect in effects:
            effect.update(delta_time)
            if effect.is_alive:
                alive_effects.append(effect)
        return alive_effects

    @staticmethod
    def _resolve_muzzle_position(player_x: float, player_y: float, direction_x: float, direction_y: float, weapon: WeaponConfig) -> tuple[float, float]:
        right_x = -direction_y
        right_y = direction_x
        muzzle_x = player_x + direction_x * weapon.muzzle_offset + right_x * weapon.muzzle_side_offset
        muzzle_y = player_y + direction_y * weapon.muzzle_offset + right_y * weapon.muzzle_side_offset
        return muzzle_x, muzzle_y

    @staticmethod
    def _normalize_direction(direction_x: float, direction_y: float) -> tuple[float, float]:
        direction_length = math.hypot(direction_x, direction_y)
        if direction_length == 0.0:
            return 0.0, 0.0
        return direction_x / direction_length, direction_y / direction_length

    @staticmethod
    def _is_solid_environment_hit(hit: RaycastHit) -> bool:
        return hit.hit and hit.surface_kind not in {TileKind.VOID, TileKind.GRASS, TileKind.DIRT, TileKind.WOOD_FLOOR, TileKind.TILE_FLOOR}

    @staticmethod
    def _resolve_debris_count(intensity: float) -> int:
        clamped = max(0.1, min(1.0, intensity))
        return max(1, round(1 + clamped * 17))

    @staticmethod
    def _line_hits_circle(
        center_x: float,
        center_y: float,
        radius: float,
        origin_x: float,
        origin_y: float,
        direction_x: float,
        direction_y: float,
        max_distance: float,
    ) -> float | None:
        offset_x = center_x - origin_x
        offset_y = center_y - origin_y
        projection = offset_x * direction_x + offset_y * direction_y
        if projection < 0.0 or projection > max_distance:
            return None
        closest_x = origin_x + direction_x * projection
        closest_y = origin_y + direction_y * projection
        if math.hypot(center_x - closest_x, center_y - closest_y) > radius:
            return None
        return projection

    @staticmethod
    def _circle_hit_distance(enemy: Enemy, origin_x: float, origin_y: float, direction_x: float, direction_y: float) -> float:
        to_center_x = enemy.x - origin_x
        to_center_y = enemy.y - origin_y
        projection = to_center_x * direction_x + to_center_y * direction_y
        closest_sq = to_center_x * to_center_x + to_center_y * to_center_y - projection * projection
        radius_sq = enemy.radius * enemy.radius
        offset = math.sqrt(max(0.0, radius_sq - closest_sq))
        return max(0.0, projection - offset)

    def _find_enemy_hit(self, enemies: list[Enemy], origin_x: float, origin_y: float, direction_x: float, direction_y: float, max_distance: float) -> int | None:
        nearest_index: int | None = None
        nearest_distance = max_distance
        for index, enemy in enumerate(enemies):
            if enemy.is_dead:
                continue
            to_center_x = enemy.x - origin_x
            to_center_y = enemy.y - origin_y
            projection = to_center_x * direction_x + to_center_y * direction_y
            if projection < 0.0 or projection > max_distance:
                continue
            closest_sq = to_center_x * to_center_x + to_center_y * to_center_y - projection * projection
            radius_sq = enemy.radius * enemy.radius
            if closest_sq > radius_sq:
                continue
            hit_distance = self._circle_hit_distance(enemy, origin_x, origin_y, direction_x, direction_y)
            if hit_distance <= nearest_distance:
                nearest_distance = hit_distance
                nearest_index = index
        return nearest_index
