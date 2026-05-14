from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(slots=True, frozen=True)
class WindowConfig:
    width: int
    height: int
    target_fps: int
    resizable: bool


@dataclass(slots=True, frozen=True)
class GenerationSizeConfig:
    width: int
    height: int
    room_attempts: int
    room_min_size: int
    room_max_size: int


@dataclass(slots=True, frozen=True)
class GenerationConfig:
    retry_count: int
    corridor_half_width: int
    min_open_ratio: float
    max_open_ratio: float
    small: GenerationSizeConfig
    medium: GenerationSizeConfig
    large: GenerationSizeConfig


@dataclass(slots=True, frozen=True)
class RenderConfig:
    background_color: tuple[int, int, int, int]
    show_grid: bool


@dataclass(slots=True, frozen=True)
class LoggingConfig:
    level: str
    log_to_file: bool
    file: str
    use_colors: bool


@dataclass(slots=True, frozen=True)
class I18NConfig:
    default_language: str
    available_languages: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class AppConfig:
    name: str
    default_map_mode: str
    default_seed: int


@dataclass(slots=True, frozen=True)
class WorldConfig:
    tile_size: int


@dataclass(slots=True, frozen=True)
class PlayerConfig:
    speed: float
    width_ratio: float
    height_ratio: float
    starting_weapon: str
    health: float
    hurt_flash_seconds: float


@dataclass(slots=True, frozen=True)
class WeaponDefinitionConfig:
    fire_interval_seconds: float
    projectile_speed: float
    projectile_lifetime_seconds: float
    projectile_radius: float
    muzzle_offset: float
    muzzle_side_offset: float
    tracer_every_n_shot: int
    tracer_probability: float
    tracer_min_fraction: float
    tracer_max_fraction: float
    tracer_lifetime_seconds: float
    tracer_width: float
    tracer_core_width: float
    impact_mark_lifetime_seconds: float
    impact_mark_max_count: int
    spread_degrees: float
    max_range: float
    impact_mark_size: float
    bullet_hole_diameter: float
    damage: float
    muzzle_flash_size: float
    muzzle_flash_lifetime_seconds: float
    recoil_distance: float
    recoil_recovery_seconds: float
    screen_shake_magnitude: float
    screen_shake_duration_seconds: float
    shell_enabled: bool
    shell_size: float
    shell_speed_min: float
    shell_speed_max: float
    shell_lifetime_seconds: float
    shell_bounce_damping: float
    shell_max_bounces: int


@dataclass(slots=True, frozen=True)
class ImpactDebrisConfig:
    enabled: bool
    intensity: float
    size_min: float
    size_max: float
    speed_min: float
    speed_max: float
    lifetime_min_seconds: float
    lifetime_max_seconds: float
    max_count: int


@dataclass(slots=True, frozen=True)
class MuzzleSmokeConfig:
    enabled: bool
    count_min: int
    count_max: int
    size_min: float
    size_max: float
    speed_min: float
    speed_max: float
    lifetime_min_seconds: float
    lifetime_max_seconds: float
    max_count: int


@dataclass(slots=True, frozen=True)
class GoreConfig:
    bloodiness: int
    burst_count_min: int
    burst_count_max: int
    burst_size_min: float
    burst_size_max: float
    burst_speed_min: float
    burst_speed_max: float
    burst_lifetime_min_seconds: float
    burst_lifetime_max_seconds: float
    pool_size_min: float
    pool_size_max: float
    pool_growth_seconds: float
    decal_chance: float
    decal_size_min: float
    decal_size_max: float
    decal_lifetime_seconds: float
    max_blood_particles: int
    max_blood_pools: int
    max_blood_decals: int
    kill_freeze_seconds: float


@dataclass(slots=True, frozen=True)
class EffectsConfig:
    impact_debris: ImpactDebrisConfig
    muzzle_smoke: MuzzleSmokeConfig
    gore: GoreConfig


@dataclass(slots=True, frozen=True)
class EnemyDefinitionConfig:
    count_small: int
    count_medium: int
    count_large: int
    speed: float
    health: float
    width_ratio: float
    height_ratio: float
    vision_distance: float
    vision_fov_degrees: float
    stop_distance: float
    attack_damage: float
    attack_interval_seconds: float
    attack_range: float
    corpse_lifetime_seconds: float
    memory_seconds: float
    strafe_speed_multiplier: float
    separation_distance: float
    separation_strength: float
    search_turn_speed_degrees: float
    fire_weapon_name: str
    fire_reaction_seconds: float
    coordination_range: float
    cover_search_radius_tiles: int
    reload_seconds: float
    magazine_size: int
    retreat_health_threshold: float
    fire_range: float
    reposition_cooldown_seconds: float
    min_hold_position_seconds: float
    reposition_min_distance: float
    reposition_chance: float


@dataclass(slots=True, frozen=True)
class GameConfig:
    project_root: Path
    app: AppConfig
    window: WindowConfig
    world: WorldConfig
    player: PlayerConfig
    weapons: dict[str, WeaponDefinitionConfig]
    enemies: dict[str, EnemyDefinitionConfig]
    generation: GenerationConfig
    render: RenderConfig
    effects: EffectsConfig
    logging: LoggingConfig
    i18n: I18NConfig


def _load_generation_size(section: dict[str, object]) -> GenerationSizeConfig:
    return GenerationSizeConfig(
        width=int(section["width"]),
        height=int(section["height"]),
        room_attempts=int(section["room_attempts"]),
        room_min_size=int(section["room_min_size"]),
        room_max_size=int(section["room_max_size"]),
    )


def _load_weapon_definitions(section: dict[str, object]) -> dict[str, WeaponDefinitionConfig]:
    weapons: dict[str, WeaponDefinitionConfig] = {}
    for name, raw_weapon in section.items():
        if not isinstance(raw_weapon, dict):
            continue
        weapons[name] = WeaponDefinitionConfig(
            fire_interval_seconds=float(raw_weapon["fire_interval_seconds"]),
            projectile_speed=float(raw_weapon["projectile_speed"]),
            projectile_lifetime_seconds=float(raw_weapon["projectile_lifetime_seconds"]),
            projectile_radius=float(raw_weapon["projectile_radius"]),
            muzzle_offset=float(raw_weapon["muzzle_offset"]),
            muzzle_side_offset=float(raw_weapon.get("muzzle_side_offset", 11.0)),
            tracer_every_n_shot=int(raw_weapon["tracer_every_n_shot"]),
            tracer_probability=float(raw_weapon["tracer_probability"]),
            tracer_min_fraction=float(raw_weapon["tracer_min_fraction"]),
            tracer_max_fraction=float(raw_weapon["tracer_max_fraction"]),
            tracer_lifetime_seconds=float(raw_weapon["tracer_lifetime_seconds"]),
            tracer_width=float(raw_weapon.get("tracer_width", 3.0)),
            tracer_core_width=float(raw_weapon.get("tracer_core_width", 1.4)),
            impact_mark_lifetime_seconds=float(raw_weapon["impact_mark_lifetime_seconds"]),
            impact_mark_max_count=int(raw_weapon["impact_mark_max_count"]),
            spread_degrees=float(raw_weapon["spread_degrees"]),
            max_range=float(raw_weapon["max_range"]),
            impact_mark_size=float(raw_weapon["impact_mark_size"]),
            bullet_hole_diameter=float(raw_weapon["bullet_hole_diameter"]),
            damage=float(raw_weapon["damage"]),
            muzzle_flash_size=float(raw_weapon.get("muzzle_flash_size", 22.0)),
            muzzle_flash_lifetime_seconds=float(raw_weapon.get("muzzle_flash_lifetime_seconds", 0.05)),
            recoil_distance=float(raw_weapon.get("recoil_distance", 7.0)),
            recoil_recovery_seconds=float(raw_weapon.get("recoil_recovery_seconds", 0.07)),
            screen_shake_magnitude=float(raw_weapon.get("screen_shake_magnitude", 2.5)),
            screen_shake_duration_seconds=float(raw_weapon.get("screen_shake_duration_seconds", 0.06)),
            shell_enabled=bool(raw_weapon.get("shell_enabled", True)),
            shell_size=float(raw_weapon.get("shell_size", 4.0)),
            shell_speed_min=float(raw_weapon.get("shell_speed_min", 90.0)),
            shell_speed_max=float(raw_weapon.get("shell_speed_max", 160.0)),
            shell_lifetime_seconds=float(raw_weapon.get("shell_lifetime_seconds", 1.0)),
            shell_bounce_damping=float(raw_weapon.get("shell_bounce_damping", 0.45)),
            shell_max_bounces=int(raw_weapon.get("shell_max_bounces", 2)),
        )
    return weapons


def _load_enemy_definitions(section: dict[str, object]) -> dict[str, EnemyDefinitionConfig]:
    enemies: dict[str, EnemyDefinitionConfig] = {}
    for name, raw_enemy in section.items():
        if not isinstance(raw_enemy, dict):
            continue
        enemies[name] = EnemyDefinitionConfig(
            count_small=int(raw_enemy["count_small"]),
            count_medium=int(raw_enemy["count_medium"]),
            count_large=int(raw_enemy["count_large"]),
            speed=float(raw_enemy["speed"]),
            health=float(raw_enemy["health"]),
            width_ratio=float(raw_enemy["width_ratio"]),
            height_ratio=float(raw_enemy["height_ratio"]),
            vision_distance=float(raw_enemy["vision_distance"]),
            vision_fov_degrees=float(raw_enemy["vision_fov_degrees"]),
            stop_distance=float(raw_enemy["stop_distance"]),
            attack_damage=float(raw_enemy["attack_damage"]),
            attack_interval_seconds=float(raw_enemy["attack_interval_seconds"]),
            attack_range=float(raw_enemy["attack_range"]),
            corpse_lifetime_seconds=float(raw_enemy["corpse_lifetime_seconds"]),
            memory_seconds=float(raw_enemy.get("memory_seconds", 1.35)),
            strafe_speed_multiplier=float(raw_enemy.get("strafe_speed_multiplier", 0.55)),
            separation_distance=float(raw_enemy.get("separation_distance", 42.0)),
            separation_strength=float(raw_enemy.get("separation_strength", 0.9)),
            search_turn_speed_degrees=float(raw_enemy.get("search_turn_speed_degrees", 180.0)),
            fire_weapon_name=str(raw_enemy.get("fire_weapon_name", "pistol")),
            fire_reaction_seconds=float(raw_enemy.get("fire_reaction_seconds", 0.18)),
            coordination_range=float(raw_enemy.get("coordination_range", 220.0)),
            cover_search_radius_tiles=int(raw_enemy.get("cover_search_radius_tiles", 6)),
            reload_seconds=float(raw_enemy.get("reload_seconds", 1.1)),
            magazine_size=int(raw_enemy.get("magazine_size", 8)),
            retreat_health_threshold=float(raw_enemy.get("retreat_health_threshold", 0.35)),
            fire_range=float(raw_enemy.get("fire_range", 260.0)),
            reposition_cooldown_seconds=float(raw_enemy.get("reposition_cooldown_seconds", 1.6)),
            min_hold_position_seconds=float(raw_enemy.get("min_hold_position_seconds", 1.2)),
            reposition_min_distance=float(raw_enemy.get("reposition_min_distance", 96.0)),
            reposition_chance=float(raw_enemy.get("reposition_chance", 0.35)),
        )
    return enemies


def load_config(config_path: Path) -> GameConfig:
    with config_path.open("rb") as file_obj:
        raw_config = tomllib.load(file_obj)

    generation_sizes = raw_config["generation"]["sizes"]
    player_section = raw_config["player"]
    weapon_definitions = _load_weapon_definitions(raw_config["weapons"])
    enemy_definitions = _load_enemy_definitions(raw_config["enemies"])
    debris_section = raw_config["effects"]["impact_debris"]
    smoke_section = raw_config["effects"]["muzzle_smoke"]
    gore_section = raw_config["effects"]["gore"]
    return GameConfig(
        project_root=config_path.resolve().parent,
        app=AppConfig(
            name=str(raw_config["app"]["name"]),
            default_map_mode=str(raw_config["app"]["default_map_mode"]),
            default_seed=int(raw_config["app"]["default_seed"]),
        ),
        window=WindowConfig(
            width=int(raw_config["window"]["width"]),
            height=int(raw_config["window"]["height"]),
            target_fps=int(raw_config["window"]["target_fps"]),
            resizable=bool(raw_config["window"]["resizable"]),
        ),
        world=WorldConfig(tile_size=int(raw_config["world"]["tile_size"])),
        player=PlayerConfig(
            speed=float(player_section["speed"]),
            width_ratio=float(player_section["width_ratio"]),
            height_ratio=float(player_section["height_ratio"]),
            starting_weapon=str(player_section["starting_weapon"]),
            health=float(player_section["health"]),
            hurt_flash_seconds=float(player_section["hurt_flash_seconds"]),
        ),
        weapons=weapon_definitions,
        enemies=enemy_definitions,
        generation=GenerationConfig(
            retry_count=int(raw_config["generation"]["retry_count"]),
            corridor_half_width=int(raw_config["generation"]["corridor_half_width"]),
            min_open_ratio=float(raw_config["generation"]["min_open_ratio"]),
            max_open_ratio=float(raw_config["generation"]["max_open_ratio"]),
            small=_load_generation_size(generation_sizes["small"]),
            medium=_load_generation_size(generation_sizes["medium"]),
            large=_load_generation_size(generation_sizes["large"]),
        ),
        render=RenderConfig(
            background_color=tuple(int(value) for value in raw_config["render"]["background_color"]),
            show_grid=bool(raw_config["render"]["show_grid"]),
        ),
        effects=EffectsConfig(
            impact_debris=ImpactDebrisConfig(
                enabled=bool(debris_section["enabled"]),
                intensity=max(0.1, min(1.0, float(debris_section["intensity"]))),
                size_min=float(debris_section["size_min"]),
                size_max=float(debris_section["size_max"]),
                speed_min=float(debris_section["speed_min"]),
                speed_max=float(debris_section["speed_max"]),
                lifetime_min_seconds=float(debris_section["lifetime_min_seconds"]),
                lifetime_max_seconds=float(debris_section["lifetime_max_seconds"]),
                max_count=int(debris_section["max_count"]),
            ),
            muzzle_smoke=MuzzleSmokeConfig(
                enabled=bool(smoke_section["enabled"]),
                count_min=int(smoke_section["count_min"]),
                count_max=int(smoke_section["count_max"]),
                size_min=float(smoke_section["size_min"]),
                size_max=float(smoke_section["size_max"]),
                speed_min=float(smoke_section["speed_min"]),
                speed_max=float(smoke_section["speed_max"]),
                lifetime_min_seconds=float(smoke_section["lifetime_min_seconds"]),
                lifetime_max_seconds=float(smoke_section["lifetime_max_seconds"]),
                max_count=int(smoke_section["max_count"]),
            ),
            gore=GoreConfig(
                bloodiness=max(0, min(100, int(gore_section["bloodiness"]))),
                burst_count_min=int(gore_section["burst_count_min"]),
                burst_count_max=int(gore_section["burst_count_max"]),
                burst_size_min=float(gore_section["burst_size_min"]),
                burst_size_max=float(gore_section["burst_size_max"]),
                burst_speed_min=float(gore_section["burst_speed_min"]),
                burst_speed_max=float(gore_section["burst_speed_max"]),
                burst_lifetime_min_seconds=float(gore_section["burst_lifetime_min_seconds"]),
                burst_lifetime_max_seconds=float(gore_section["burst_lifetime_max_seconds"]),
                pool_size_min=float(gore_section["pool_size_min"]),
                pool_size_max=float(gore_section["pool_size_max"]),
                pool_growth_seconds=float(gore_section["pool_growth_seconds"]),
                decal_chance=float(gore_section["decal_chance"]),
                decal_size_min=float(gore_section["decal_size_min"]),
                decal_size_max=float(gore_section["decal_size_max"]),
                decal_lifetime_seconds=float(gore_section["decal_lifetime_seconds"]),
                max_blood_particles=int(gore_section["max_blood_particles"]),
                max_blood_pools=int(gore_section["max_blood_pools"]),
                max_blood_decals=int(gore_section["max_blood_decals"]),
                kill_freeze_seconds=float(gore_section["kill_freeze_seconds"]),
            ),
        ),
        logging=LoggingConfig(
            level=str(raw_config["logging"]["level"]),
            log_to_file=bool(raw_config["logging"]["log_to_file"]),
            file=str(raw_config["logging"]["file"]),
            use_colors=bool(raw_config["logging"]["use_colors"]),
        ),
        i18n=I18NConfig(
            default_language=str(raw_config["i18n"]["default_language"]),
            available_languages=tuple(str(value) for value in raw_config["i18n"]["available_languages"]),
        ),
    )
