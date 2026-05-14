from __future__ import annotations

from dataclasses import dataclass, field

import pyray as pr

from topdown.core.config import GameConfig
from topdown.core.logging_ext import ProjectLoggerAdapter
from topdown.core.types import MapMode
from topdown.entities.enemy import Enemy
from topdown.entities.player import Player
from topdown.i18n.manager import I18NManager
from topdown.render.atlas import TextureAtlas
from topdown.render.tile_renderer import TileRenderer
from topdown.systems.aiming import AimController, AimState
from topdown.systems.combat import AimPreview, CombatState, CombatSystem, WeaponConfig
from topdown.systems.enemy_ai import EnemyAiSystem, VisionConePreview
from topdown.systems.player_controller import InputState, PlayerController
from topdown.world.camera import CameraController, CameraState
from topdown.world.collision import CollisionResolver
from topdown.world.generation import MapGenerator
from topdown.world.map_model import TileMap
from topdown.world.presets import get_generation_preset
from topdown.world.static_maps import build_debug_static_map


@dataclass(slots=True)
class GameState:
    """Mutable runtime state for the sixth milestone."""

    map_mode: MapMode
    seed: int
    tile_map: TileMap
    player: Player
    camera: CameraState
    aim: AimState
    combat: CombatState = field(default_factory=CombatState)
    enemies: list[Enemy] = field(default_factory=list)
    vision_previews: list[VisionConePreview] = field(default_factory=list)
    show_overlay: bool = True
    show_hitboxes: bool = False
    show_debug_beam: bool = False
    show_blocker_overlay: bool = False
    show_vision_cones: bool = False
    show_region_overlay: bool = False
    show_cover_overlay: bool = False
    show_spawn_overlay: bool = False
    show_enemy_hp: bool = False
    show_cover_nodes_overlay: bool = False
    aim_preview: AimPreview | None = None
    freeze_remaining_seconds: float = 0.0


class GameApp:
    """Pyray application entry point for the sixth milestone."""

    def __init__(self, config: GameConfig, logger: ProjectLoggerAdapter) -> None:
        self._config = config
        self._logger = logger
        self._generator = MapGenerator(config)
        self._atlas = TextureAtlas(root_dir=config.project_root, tile_size=config.world.tile_size)
        self._tile_renderer = TileRenderer(atlas=self._atlas, tile_size=config.world.tile_size, render_config=config.render)
        self._i18n = I18NManager(config.project_root / "lang", config.i18n.default_language)
        self._collision_resolver = CollisionResolver(tile_size=config.world.tile_size)
        self._camera_controller = CameraController(
            viewport_width=config.window.width,
            viewport_height=config.window.height,
            world_tile_size=config.world.tile_size,
        )
        weapon_configs = {
            name: WeaponConfig(
                fire_interval_seconds=definition.fire_interval_seconds,
                projectile_speed=definition.projectile_speed,
                projectile_lifetime_seconds=definition.projectile_lifetime_seconds,
                projectile_radius=definition.projectile_radius,
                muzzle_offset=definition.muzzle_offset,
                muzzle_side_offset=definition.muzzle_side_offset,
                tracer_every_n_shot=definition.tracer_every_n_shot,
                tracer_probability=definition.tracer_probability,
                tracer_min_fraction=definition.tracer_min_fraction,
                tracer_max_fraction=definition.tracer_max_fraction,
                tracer_lifetime_seconds=definition.tracer_lifetime_seconds,
                tracer_width=definition.tracer_width,
                tracer_core_width=definition.tracer_core_width,
                impact_mark_lifetime_seconds=definition.impact_mark_lifetime_seconds,
                impact_mark_max_count=definition.impact_mark_max_count,
                spread_degrees=definition.spread_degrees,
                max_range=definition.max_range,
                impact_mark_size=definition.impact_mark_size,
                bullet_hole_diameter=definition.bullet_hole_diameter,
                damage=definition.damage,
                muzzle_flash_size=definition.muzzle_flash_size,
                muzzle_flash_lifetime_seconds=definition.muzzle_flash_lifetime_seconds,
                recoil_distance=definition.recoil_distance,
                recoil_recovery_seconds=definition.recoil_recovery_seconds,
                screen_shake_magnitude=definition.screen_shake_magnitude,
                screen_shake_duration_seconds=definition.screen_shake_duration_seconds,
                shell_enabled=definition.shell_enabled,
                shell_size=definition.shell_size,
                shell_speed_min=definition.shell_speed_min,
                shell_speed_max=definition.shell_speed_max,
                shell_lifetime_seconds=definition.shell_lifetime_seconds,
                shell_bounce_damping=definition.shell_bounce_damping,
                shell_max_bounces=definition.shell_max_bounces,
            )
            for name, definition in config.weapons.items()
        }
        self._weapon_names = list(weapon_configs.keys())
        self._combat_system = CombatSystem(
            weapons=weapon_configs,
            tile_size=config.world.tile_size,
            impact_debris_config=config.effects.impact_debris,
            gore_config=config.effects.gore,
            collision_resolver=self._collision_resolver,
            muzzle_smoke_config=config.effects.muzzle_smoke,
        )
        self._enemy_ai = EnemyAiSystem(tile_size=config.world.tile_size, collision_resolver=self._collision_resolver)
        initial_mode = MapMode(config.app.default_map_mode)
        placeholder_map = build_debug_static_map()
        placeholder_player = self._spawn_player(placeholder_map)
        placeholder_aim = AimController.build(
            player_x=placeholder_player.x,
            player_y=placeholder_player.y,
            target_x=placeholder_player.x + 1.0,
            target_y=placeholder_player.y,
        )
        self._state = GameState(
            map_mode=initial_mode,
            seed=config.app.default_seed,
            tile_map=placeholder_map,
            player=placeholder_player,
            camera=CameraState(),
            aim=placeholder_aim,
        )

    def run(self) -> None:
        pr.set_config_flags(pr.FLAG_MSAA_4X_HINT)
        pr.init_window(self._config.window.width, self._config.window.height, self._config.app.name)
        pr.set_target_fps(self._config.window.target_fps)
        self._atlas.load()
        self._reload_map(reset_seed=False)
        self._logger.info("Application started with map mode: %s", self._state.map_mode)
        self._logger.dump_object("Loaded atlas keys", {"keys": sorted(self._atlas.keys)})

        try:
            while not pr.window_should_close():
                delta_time = pr.get_frame_time()
                if self._state.freeze_remaining_seconds > 0.0:
                    self._state.freeze_remaining_seconds = max(0.0, self._state.freeze_remaining_seconds - delta_time)
                else:
                    self._handle_input(delta_time)
                self._draw_frame()
        finally:
            self._atlas.unload()
            pr.close_window()

    def _spawn_player(self, tile_map: TileMap) -> Player:
        tile_size = self._config.world.tile_size
        spawn_x = tile_map.spawn_tile[0] * tile_size + tile_size / 2.0
        spawn_y = tile_map.spawn_tile[1] * tile_size + tile_size / 2.0
        return Player(
            x=spawn_x,
            y=spawn_y,
            width=tile_size * self._config.player.width_ratio,
            height=tile_size * self._config.player.height_ratio,
            speed=self._config.player.speed,
            health=self._config.player.health,
            max_health=self._config.player.health,
            hurt_flash_seconds=self._config.player.hurt_flash_seconds,
        )

    def _spawn_enemies(self, tile_map: TileMap) -> list[Enemy]:
        definition = self._config.enemies["grunt"]
        room_targets = {
            MapMode.DEBUG_STATIC: definition.count_small,
            MapMode.GENERATED_SMALL: definition.count_small,
            MapMode.GENERATED_MEDIUM: definition.count_medium,
            MapMode.GENERATED_LARGE: definition.count_large,
        }
        target_count = room_targets[self._state.map_mode]
        tile_size = self._config.world.tile_size
        spawn_tiles = list(tile_map.enemy_spawn_tiles)
        if self._state.map_mode is MapMode.DEBUG_STATIC or not spawn_tiles:
            spawn_tile = tile_map.spawn_tile
            sorted_rooms = sorted(
                tile_map.rooms,
                key=lambda room: abs(room.center[0] - spawn_tile[0]) + abs(room.center[1] - spawn_tile[1]),
                reverse=True,
            )
            spawn_tiles = [room.center for room in sorted_rooms]
        enemies: list[Enemy] = []
        for center_x, center_y in spawn_tiles[:target_count]:
            if not tile_map.is_walkable(center_x, center_y):
                continue
            enemies.append(
                Enemy(
                    x=center_x * tile_size + tile_size / 2.0,
                    y=center_y * tile_size + tile_size / 2.0,
                    width=tile_size * definition.width_ratio,
                    height=tile_size * definition.height_ratio,
                    speed=definition.speed,
                    health=definition.health,
                    max_health=definition.health,
                    vision_distance=definition.vision_distance,
                    vision_fov_degrees=definition.vision_fov_degrees,
                    stop_distance=definition.stop_distance,
                    attack_damage=definition.attack_damage,
                    attack_interval_seconds=definition.attack_interval_seconds,
                    attack_range=definition.attack_range,
                    corpse_lifetime_seconds=definition.corpse_lifetime_seconds,
                    memory_seconds=definition.memory_seconds,
                    strafe_speed_multiplier=definition.strafe_speed_multiplier,
                    separation_distance=definition.separation_distance,
                    separation_strength=definition.separation_strength,
                    search_turn_speed_degrees=definition.search_turn_speed_degrees,
                    fire_weapon_name=definition.fire_weapon_name,
                    fire_reaction_seconds=definition.fire_reaction_seconds,
                    coordination_range=definition.coordination_range,
                    cover_search_radius_tiles=definition.cover_search_radius_tiles,
                    reload_seconds=definition.reload_seconds,
                    magazine_size=definition.magazine_size,
                    retreat_health_threshold=definition.retreat_health_threshold,
                    fire_range=definition.fire_range,
                    reposition_cooldown_seconds=definition.reposition_cooldown_seconds,
                    min_hold_position_seconds=definition.min_hold_position_seconds,
                    reposition_min_distance=definition.reposition_min_distance,
                    reposition_chance=definition.reposition_chance,
                )
            )
        return enemies

    def _reload_map(self, reset_seed: bool = False) -> None:
        if self._state.map_mode is MapMode.DEBUG_STATIC:
            self._state.tile_map = build_debug_static_map()
        else:
            if reset_seed:
                self._state.seed += 1
            preset = get_generation_preset(self._config, self._state.map_mode)
            result = self._generator.generate(preset=preset, seed=self._state.seed, name=self._state.map_mode.value)
            self._state.tile_map = result.tile_map
            self._state.seed = result.seed

        self._state.player = self._spawn_player(self._state.tile_map)
        self._state.combat = CombatState(active_weapon_name=self._config.player.starting_weapon)
        self._state.enemies = self._spawn_enemies(self._state.tile_map)
        self._state.vision_previews = []
        self._state.aim = AimController.build(
            player_x=self._state.player.x,
            player_y=self._state.player.y,
            target_x=self._state.player.x + 1.0,
            target_y=self._state.player.y,
        )
        self._state.aim_preview = None
        self._camera_controller.follow(
            self._state.camera,
            target_x=self._state.player.x,
            target_y=self._state.player.y,
            map_width_tiles=self._state.tile_map.width,
            map_height_tiles=self._state.tile_map.height,
        )

    def _handle_input(self, delta_time: float) -> None:
        if pr.is_key_pressed(pr.KEY_F1):
            self._state.show_overlay = not self._state.show_overlay
        if pr.is_key_pressed(pr.KEY_F2):
            self._state.show_hitboxes = not self._state.show_hitboxes
        if pr.is_key_pressed(pr.KEY_F3):
            self._state.show_debug_beam = not self._state.show_debug_beam
        if pr.is_key_pressed(pr.KEY_F4):
            self._state.show_blocker_overlay = not self._state.show_blocker_overlay
        if pr.is_key_pressed(pr.KEY_F5):
            self._state.show_vision_cones = not self._state.show_vision_cones
        if pr.is_key_pressed(pr.KEY_F6):
            self._state.show_region_overlay = not self._state.show_region_overlay
        if pr.is_key_pressed(pr.KEY_F7):
            self._state.show_cover_overlay = not self._state.show_cover_overlay
        if pr.is_key_pressed(pr.KEY_F8):
            self._state.show_spawn_overlay = not self._state.show_spawn_overlay
        if pr.is_key_pressed(pr.KEY_F9):
            self._state.show_enemy_hp = not self._state.show_enemy_hp
        if pr.is_key_pressed(pr.KEY_F10):
            self._state.show_cover_nodes_overlay = not self._state.show_cover_nodes_overlay
        if pr.is_key_pressed(pr.KEY_ONE):
            self._switch_mode(MapMode.DEBUG_STATIC)
        if pr.is_key_pressed(pr.KEY_TWO):
            self._switch_mode(MapMode.GENERATED_SMALL)
        if pr.is_key_pressed(pr.KEY_THREE):
            self._switch_mode(MapMode.GENERATED_MEDIUM)
        if pr.is_key_pressed(pr.KEY_FOUR):
            self._switch_mode(MapMode.GENERATED_LARGE)
        if pr.is_key_pressed(pr.KEY_R):
            self._reload_map(reset_seed=True)
            self._logger.info("Map reloaded with seed %s", self._state.seed)
        if pr.is_key_pressed(pr.KEY_Q):
            self._cycle_weapon()
        if self._state.player.is_dead and (pr.is_key_pressed(pr.KEY_ENTER) or pr.is_key_pressed(pr.KEY_SPACE)):
            self._reload_map(reset_seed=False)
            self._logger.info("Restarted current map after game over")

        self._state.player.update_timers(delta_time)
        self._camera_controller.update(self._state.camera, delta_time)
        if self._state.player.is_dead:
            self._state.vision_previews = []
            self._combat_system.update(state=self._state.combat, tile_map=self._state.tile_map, delta_time=delta_time)
            return

        input_state = InputState(
            move_left=pr.is_key_down(pr.KEY_A) or pr.is_key_down(pr.KEY_LEFT),
            move_right=pr.is_key_down(pr.KEY_D) or pr.is_key_down(pr.KEY_RIGHT),
            move_up=pr.is_key_down(pr.KEY_W) or pr.is_key_down(pr.KEY_UP),
            move_down=pr.is_key_down(pr.KEY_S) or pr.is_key_down(pr.KEY_DOWN),
        )
        movement = PlayerController.build_movement(
            input_state=input_state,
            speed=self._state.player.speed,
            delta_time=delta_time,
        )
        self._collision_resolver.move_actor(self._state.player, movement, self._state.tile_map)
        self._camera_controller.follow(
            self._state.camera,
            target_x=self._state.player.x,
            target_y=self._state.player.y,
            map_width_tiles=self._state.tile_map.width,
            map_height_tiles=self._state.tile_map.height,
        )
        mouse_world_x, mouse_world_y = self._mouse_world_position()
        self._state.aim = AimController.build(
            player_x=self._state.player.x,
            player_y=self._state.player.y,
            target_x=mouse_world_x,
            target_y=mouse_world_y,
        )
        self._state.player.update_facing_from_point(mouse_world_x, mouse_world_y)
        self._state.aim_preview = self._combat_system.preview_shot(
            state=self._state.combat,
            tile_map=self._state.tile_map,
            player_x=self._state.player.x,
            player_y=self._state.player.y,
            aim_state=self._state.aim,
        )

        if pr.is_mouse_button_down(pr.MOUSE_BUTTON_LEFT):
            shot_result = self._combat_system.try_fire(
                state=self._state.combat,
                tile_map=self._state.tile_map,
                player_x=self._state.player.x,
                player_y=self._state.player.y,
                aim_state=self._state.aim,
                enemies=self._state.enemies,
            )
            if shot_result.hit_enemy and shot_result.hit_enemy_index is not None:
                enemy = self._state.enemies[shot_result.hit_enemy_index]
                enemy_killed = enemy.apply_damage(
                    shot_result.damage,
                    impulse_x=shot_result.enemy_impulse_x,
                    impulse_y=shot_result.enemy_impulse_y,
                )
                if enemy_killed:
                    self._state.freeze_remaining_seconds = max(self._state.freeze_remaining_seconds, shot_result.kill_freeze_seconds)
            if shot_result.did_fire:
                self._state.player.apply_recoil(
                    angle_deg=shot_result.recoil_angle_deg,
                    distance=shot_result.recoil_distance,
                    recovery_seconds=shot_result.recoil_recovery_seconds,
                )
                self._camera_controller.add_shake(
                    self._state.camera,
                    magnitude=shot_result.screen_shake_magnitude,
                    duration_seconds=shot_result.screen_shake_duration_seconds,
                )
                self._logger.debug(
                    "Shot: weapon=%s enemy=%s surface=%s",
                    self._state.combat.active_weapon_name,
                    shot_result.hit_enemy,
                    shot_result.hit_surface,
                )

        damage_to_player = self._enemy_ai.update(
            self._state.enemies,
            self._state.player,
            self._state.tile_map,
            delta_time,
            self._combat_system,
            self._state.combat,
        )
        if damage_to_player > 0.0:
            self._state.player.apply_damage(damage_to_player)
            self._camera_controller.add_shake(
                self._state.camera,
                magnitude=2.0,
                duration_seconds=0.04,
            )
            self._logger.debug("Player took %.1f damage", damage_to_player)
        if self._state.show_vision_cones:
            self._state.vision_previews = [
                self._enemy_ai.build_vision_preview(enemy, self._state.player, self._state.tile_map)
                for enemy in self._state.enemies
                if not enemy.is_dead
            ]
        else:
            self._state.vision_previews = []
        self._combat_system.update(state=self._state.combat, tile_map=self._state.tile_map, delta_time=delta_time)

    def _cycle_weapon(self) -> None:
        current_index = self._weapon_names.index(self._state.combat.active_weapon_name)
        next_index = (current_index + 1) % len(self._weapon_names)
        self._state.combat.active_weapon_name = self._weapon_names[next_index]
        self._state.combat.cooldown_remaining = 0.0
        self._logger.info("Switched weapon to %s", self._state.combat.active_weapon_name)

    def _switch_mode(self, mode: MapMode) -> None:
        self._state.map_mode = mode
        self._reload_map(reset_seed=False)
        self._logger.info("Switched map mode to %s", mode)

    def _draw_frame(self) -> None:
        background = self._config.render.background_color
        pr.begin_drawing()
        pr.clear_background(pr.Color(*background))
        camera_offset = self._compute_camera_offset(self._state.tile_map)
        self._tile_renderer.draw_map(self._state.tile_map, camera_offset=camera_offset)
        if self._state.show_blocker_overlay:
            self._tile_renderer.draw_collision_overlay(self._state.tile_map, camera_offset=camera_offset)
        if self._state.show_vision_cones:
            self._tile_renderer.draw_vision_cones(self._state.vision_previews, camera_offset=camera_offset)
        if self._state.show_region_overlay:
            self._tile_renderer.draw_region_overlay(self._state.tile_map, camera_offset=camera_offset)
        if self._state.show_cover_overlay:
            self._tile_renderer.draw_cover_overlay(self._state.tile_map, camera_offset=camera_offset)
        if self._state.show_spawn_overlay:
            self._tile_renderer.draw_spawn_overlay(self._state.tile_map, camera_offset=camera_offset)
        if self._state.show_cover_nodes_overlay:
            self._tile_renderer.draw_cover_nodes_overlay(self._state.tile_map, camera_offset=camera_offset)
        self._tile_renderer.draw_blood_decals(self._state.combat.blood_decals, camera_offset=camera_offset)
        self._tile_renderer.draw_blood_pools(self._state.combat.blood_pools, camera_offset=camera_offset)
        self._tile_renderer.draw_impact_marks(self._state.combat.impact_marks, camera_offset=camera_offset)
        self._tile_renderer.draw_impact_debris(self._state.combat.impact_debris, camera_offset=camera_offset)
        self._tile_renderer.draw_shell_casings(self._state.combat.shell_casings, camera_offset=camera_offset)
        self._tile_renderer.draw_muzzle_smoke(self._state.combat.muzzle_smoke, camera_offset=camera_offset)
        self._tile_renderer.draw_muzzle_flashes(self._state.combat.muzzle_flashes, camera_offset=camera_offset)
        if self._state.show_debug_beam and self._state.aim_preview is not None and not self._state.player.is_dead:
            self._tile_renderer.draw_debug_beam(self._state.aim_preview, camera_offset=camera_offset)
        self._tile_renderer.draw_tracers(self._state.combat.tracers, camera_offset=camera_offset)
        self._tile_renderer.draw_blood_particles(self._state.combat.blood_particles, camera_offset=camera_offset)
        self._tile_renderer.draw_enemies(
            self._state.enemies,
            camera_offset=camera_offset,
            show_hitbox=self._state.show_hitboxes,
            show_health=self._state.show_enemy_hp,
        )
        self._tile_renderer.draw_player(self._state.player, camera_offset=camera_offset, show_hitbox=self._state.show_hitboxes)
        self._draw_hud()
        if self._state.show_overlay:
            self._draw_overlay()
        if self._state.player.is_dead:
            self._draw_game_over()
        pr.end_drawing()

    def _compute_camera_offset(self, tile_map: TileMap) -> tuple[int, int]:
        map_pixel_width = tile_map.width * self._config.world.tile_size
        map_pixel_height = tile_map.height * self._config.world.tile_size
        margin_x = max((self._config.window.width - map_pixel_width) // 2, 0)
        margin_y = max((self._config.window.height - map_pixel_height) // 2, 0)
        return int(round(margin_x - self._state.camera.x + self._state.camera.shake_x)), int(round(margin_y - self._state.camera.y + self._state.camera.shake_y))

    def _mouse_world_position(self) -> tuple[float, float]:
        camera_offset = self._compute_camera_offset(self._state.tile_map)
        mouse_position = pr.get_mouse_position()
        return float(mouse_position.x - camera_offset[0]), float(mouse_position.y - camera_offset[1])

    def _draw_hud(self) -> None:
        panel_x = 16
        panel_y = self._config.window.height - 104
        panel_width = 360
        panel_height = 88
        pr.draw_rectangle(panel_x, panel_y, panel_width, panel_height, pr.fade(pr.BLACK, 0.62))
        pr.draw_text(self._i18n.translate("hud.player_hp"), panel_x + 16, panel_y + 12, 20, pr.RAYWHITE)
        bar_x = panel_x + 16
        bar_y = panel_y + 40
        bar_w = 220
        bar_h = 22
        pr.draw_rectangle(bar_x, bar_y, bar_w, bar_h, pr.fade(pr.DARKGRAY, 0.9))
        pr.draw_rectangle(bar_x, bar_y, int(round(bar_w * self._state.player.health_ratio)), bar_h, pr.RED)
        pr.draw_rectangle_lines(bar_x, bar_y, bar_w, bar_h, pr.RAYWHITE)
        hp_text = f"{self._state.player.health:.0f}/{self._state.player.max_health:.0f}"
        pr.draw_text(hp_text, bar_x + 76, bar_y + 2, 18, pr.WHITE)
        alive_enemies = sum(not enemy.is_dead for enemy in self._state.enemies)
        weapon_name = self._state.combat.active_weapon_name.upper()
        pr.draw_text(f"{self._i18n.translate('hud.weapon')}: {weapon_name}", panel_x + 16, panel_y + 68, 18, pr.GOLD)
        pr.draw_text(f"{self._i18n.translate('hud.enemies')}: {alive_enemies}", panel_x + 190, panel_y + 68, 18, pr.ORANGE)

    def _draw_game_over(self) -> None:
        pr.draw_rectangle(0, 0, self._config.window.width, self._config.window.height, pr.fade(pr.BLACK, 0.42))
        center_x = self._config.window.width // 2
        center_y = self._config.window.height // 2
        title = self._i18n.translate("hud.game_over")
        subtitle = self._i18n.translate("hud.game_over_help")
        title_width = pr.measure_text(title, 48)
        subtitle_width = pr.measure_text(subtitle, 24)
        pr.draw_text(title, center_x - title_width // 2, center_y - 40, 48, pr.RED)
        pr.draw_text(subtitle, center_x - subtitle_width // 2, center_y + 18, 24, pr.RAYWHITE)

    def _draw_overlay(self) -> None:
        player = self._state.player
        aim = self._state.aim
        preview = self._state.aim_preview
        tile_size = self._config.world.tile_size
        weapon = self._combat_system.get_weapon(self._state.combat.active_weapon_name)
        hit_distance = preview.hit.distance if preview is not None else 0.0
        hit_surface = preview.hit.surface_kind.name if preview is not None else "VOID"
        alive_enemies = sum(not enemy.is_dead for enemy in self._state.enemies)
        alerted_enemies = sum(enemy.sees_player for enemy in self._state.enemies if not enemy.is_dead)
        lines = [
            f"{self._i18n.translate('map.mode')}: {self._display_mode(self._state.map_mode)}",
            f"{self._i18n.translate('map.seed')}: {self._state.seed}",
            f"{self._i18n.translate('map.size')}: {self._state.tile_map.width}x{self._state.tile_map.height}",
            f"{self._i18n.translate('player.position')}: {player.x:.1f}, {player.y:.1f}",
            f"{self._i18n.translate('player.tile')}: {int(player.x // tile_size)}, {int(player.y // tile_size)}",
            f"{self._i18n.translate('player.speed')}: {player.speed:.1f}",
            f"{self._i18n.translate('player.facing')}: {player.facing_angle_deg:.1f}",
            f"{self._i18n.translate('player.health')}: {player.health:.1f}/{player.max_health:.1f}",
            f"{self._i18n.translate('player.aim')}: {aim.target_x:.1f}, {aim.target_y:.1f}",
            f"{self._i18n.translate('combat.weapon')}: {self._state.combat.active_weapon_name}",
            f"{self._i18n.translate('combat.fire_interval')}: {weapon.fire_interval_seconds:.2f}",
            f"{self._i18n.translate('combat.damage')}: {weapon.damage:.1f}",
            f"{self._i18n.translate('combat.range')}: {weapon.max_range:.1f}",
            f"{self._i18n.translate('combat.hit_distance')}: {hit_distance:.1f}",
            f"{self._i18n.translate('combat.hit_surface')}: {hit_surface}",
            f"{self._i18n.translate('combat.debug_beam')}: {'on' if self._state.show_debug_beam else 'off'}",
            f"{self._i18n.translate('map.blockers')}: {'on' if self._state.show_blocker_overlay else 'off'}",
            f"{self._i18n.translate('enemy.count')}: {alive_enemies}",
            f"{self._i18n.translate('enemy.alerted')}: {alerted_enemies}",
            f"{self._i18n.translate('enemy.vision_debug')}: {'on' if self._state.show_vision_cones else 'off'}",
            f"regions: {'on' if self._state.show_region_overlay else 'off'}",
            f"covers: {'on' if self._state.show_cover_overlay else 'off'} ({len(self._state.tile_map.cover_tiles)})",
            f"cover nodes: {'on' if self._state.show_cover_nodes_overlay else 'off'} ({len(self._state.tile_map.cover_nodes)})",
            f"spawns: {'on' if self._state.show_spawn_overlay else 'off'} ({len(self._state.tile_map.enemy_spawn_tiles)})",
            f"enemy hp: {'on' if self._state.show_enemy_hp else 'off'}",
            f"{self._i18n.translate('combat.tracers')}: {len(self._state.combat.tracers)}",
            f"{self._i18n.translate('combat.impacts')}: {len(self._state.combat.impact_marks)}",
            f"{self._i18n.translate('combat.debris')}: {len(self._state.combat.impact_debris)}",
            f"{self._i18n.translate('combat.flashes')}: {len(self._state.combat.muzzle_flashes)}",
            f"shells: {len(self._state.combat.shell_casings)}",
            f"shake: {self._state.camera.shake_magnitude:.1f}/{self._state.camera.shake_duration_seconds:.2f}",
            f"{self._i18n.translate('combat.cooldown')}: {self._state.combat.cooldown_remaining:.2f}",
            self._i18n.translate("map.help"),
            self._i18n.translate("player.help"),
            self._i18n.translate("combat.help"),
            self._i18n.translate("enemy.help"),
            "F6 regions | F7 covers | F8 spawns | F9 enemy HP | F10 cover nodes",
        ]
        panel_height = 24 + 24 * len(lines)
        pr.draw_rectangle(16, 16, 640, panel_height, pr.fade(pr.BLACK, 0.55))
        for index, line in enumerate(lines):
            pr.draw_text(line, 28, 28 + index * 24, 20, pr.RAYWHITE)

    def _display_mode(self, mode: MapMode) -> str:
        return self._i18n.translate(f"map.{mode.value}")
