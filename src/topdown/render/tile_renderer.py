from __future__ import annotations

from dataclasses import dataclass
import math

import pyray as pr

from topdown.core.config import RenderConfig
from topdown.core.types import TileKind
from topdown.entities.effects import BloodDecal, BloodParticle, BloodPool, ImpactDebrisParticle, ImpactMark, MuzzleFlashEffect, MuzzleSmokeParticle, ShellCasing, TracerEffect
from topdown.entities.enemy import Enemy
from topdown.entities.player import Player
from topdown.render.atlas import TextureAtlas
from topdown.systems.combat import AimPreview
from topdown.systems.enemy_ai import VisionConePreview
from topdown.world.map_model import CoverNode, TileMap


@dataclass(slots=True)
class TileRenderer:
    """Render the world, actors, and debug geometry with Pyray."""

    atlas: TextureAtlas
    tile_size: int
    render_config: RenderConfig

    def draw_map(self, tile_map: TileMap, camera_offset: tuple[int, int] = (0, 0)) -> None:
        offset_x, offset_y = camera_offset
        min_x, max_x, min_y, max_y = self._visible_tile_bounds(tile_map, camera_offset)
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                tile_kind = tile_map.get_tile(x, y)
                if tile_kind is TileKind.VOID:
                    continue
                draw_x = x * self.tile_size + offset_x
                draw_y = y * self.tile_size + offset_y
                texture = self._select_wall_texture(tile_map, x, y) if tile_kind is TileKind.WALL else self.atlas.get_floor_texture(tile_kind, x, y)
                self._draw_tile_texture(texture, draw_x, draw_y)
                if tile_map.is_cover(x, y):
                    self._draw_cover_block(draw_x, draw_y)
                if self.render_config.show_grid:
                    pr.draw_rectangle_lines(int(round(draw_x)), int(round(draw_y)), self.tile_size, self.tile_size, pr.fade(pr.BLACK, 0.15))

        spawn_x = tile_map.spawn_tile[0] * self.tile_size + offset_x + self.tile_size // 2
        spawn_y = tile_map.spawn_tile[1] * self.tile_size + offset_y + self.tile_size // 2
        pr.draw_circle_lines(int(round(spawn_x)), int(round(spawn_y)), self.tile_size // 5, pr.GOLD)

    def draw_collision_overlay(self, tile_map: TileMap, camera_offset: tuple[int, int] = (0, 0)) -> None:
        offset_x, offset_y = camera_offset
        line_color = pr.fade(pr.RED, 0.80)
        min_x, max_x, min_y, max_y = self._visible_tile_bounds(tile_map, camera_offset)
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if tile_map.is_walkable(x, y):
                    continue
                draw_x = x * self.tile_size + offset_x
                draw_y = y * self.tile_size + offset_y
                pr.draw_rectangle_lines(int(round(draw_x)), int(round(draw_y)), self.tile_size, self.tile_size, line_color)
        pr.draw_rectangle_lines(int(round(offset_x)), int(round(offset_y)), tile_map.width * self.tile_size, tile_map.height * self.tile_size, pr.fade(pr.MAROON, 0.85))

    def draw_region_overlay(self, tile_map: TileMap, camera_offset: tuple[int, int] = (0, 0)) -> None:
        palette = {
            "player_start": pr.GREEN,
            "transition": pr.SKYBLUE,
            "combat_alpha": pr.GOLD,
            "combat_beta": pr.ORANGE,
            "pressure": pr.RED,
        }
        offset_x, offset_y = camera_offset
        for region in tile_map.regions:
            color = pr.fade(palette.get(region.role, pr.PURPLE), 0.8)
            draw_x = region.x * self.tile_size + offset_x
            draw_y = region.y * self.tile_size + offset_y
            draw_w = region.width * self.tile_size
            draw_h = region.height * self.tile_size
            pr.draw_rectangle_lines(int(round(draw_x)), int(round(draw_y)), draw_w, draw_h, color)
            label = region.role.replace('_', ' ')
            pr.draw_text(label, int(round(draw_x)) + 8, int(round(draw_y)) + 8, 16, color)

    def draw_cover_overlay(self, tile_map: TileMap, camera_offset: tuple[int, int] = (0, 0)) -> None:
        offset_x, offset_y = camera_offset
        min_x, max_x, min_y, max_y = self._visible_tile_bounds(tile_map, camera_offset)
        for x, y in sorted(tile_map.cover_tiles):
            if x < min_x or x > max_x or y < min_y or y > max_y:
                continue
            draw_x = x * self.tile_size + offset_x
            draw_y = y * self.tile_size + offset_y
            pr.draw_rectangle_lines(int(round(draw_x)), int(round(draw_y)), self.tile_size, self.tile_size, pr.fade(pr.BLUE, 0.9))
            pr.draw_circle(int(round(draw_x + self.tile_size / 2)), int(round(draw_y + self.tile_size / 2)), 4, pr.fade(pr.BLUE, 0.85))

    def draw_cover_nodes_overlay(self, tile_map: TileMap, camera_offset: tuple[int, int] = (0, 0)) -> None:
        offset_x, offset_y = camera_offset
        min_x, max_x, min_y, max_y = self._visible_tile_bounds(tile_map, camera_offset)
        palette = {
            "hold": pr.GOLD,
            "left_peek": pr.GREEN,
            "right_peek": pr.LIME,
            "transition": pr.SKYBLUE,
            "fallback": pr.PURPLE,
        }
        labels = {
            "hold": "H",
            "left_peek": "L",
            "right_peek": "R",
            "transition": "T",
            "fallback": "F",
        }
        for node in tile_map.cover_nodes:
            if node.tile_x < min_x or node.tile_x > max_x or node.tile_y < min_y or node.tile_y > max_y:
                continue
            draw_x = node.tile_x * self.tile_size + offset_x + self.tile_size / 2
            draw_y = node.tile_y * self.tile_size + offset_y + self.tile_size / 2
            color = pr.fade(palette.get(node.node_type, pr.WHITE), 0.95)
            pr.draw_circle(int(round(draw_x)), int(round(draw_y)), 5, color)
            pr.draw_circle_lines(int(round(draw_x)), int(round(draw_y)), 8, color)
            pr.draw_line(
                int(round(draw_x)),
                int(round(draw_y)),
                int(round(draw_x + node.facing_dx * 14)),
                int(round(draw_y + node.facing_dy * 14)),
                color,
            )
            pr.draw_text(labels.get(node.node_type, "?"), int(round(draw_x)) - 5, int(round(draw_y)) - 20, 14, color)

    def draw_spawn_overlay(self, tile_map: TileMap, camera_offset: tuple[int, int] = (0, 0)) -> None:
        offset_x, offset_y = camera_offset
        px = tile_map.spawn_tile[0] * self.tile_size + offset_x + self.tile_size // 2
        py = tile_map.spawn_tile[1] * self.tile_size + offset_y + self.tile_size // 2
        pr.draw_circle_lines(int(round(px)), int(round(py)), self.tile_size // 4, pr.GREEN)
        pr.draw_text('P', int(round(px)) - 5, int(round(py)) - 10, 18, pr.GREEN)
        for index, (x, y) in enumerate(tile_map.enemy_spawn_tiles, start=1):
            sx = x * self.tile_size + offset_x + self.tile_size // 2
            sy = y * self.tile_size + offset_y + self.tile_size // 2
            pr.draw_circle_lines(int(round(sx)), int(round(sy)), self.tile_size // 5, pr.RED)
            pr.draw_text(str(index), int(round(sx)) - 5, int(round(sy)) - 9, 16, pr.RED)

    def draw_player(self, player: Player, camera_offset: tuple[int, int] = (0, 0), show_hitbox: bool = False) -> None:
        texture = self.atlas.get("player")
        recoil_x, recoil_y = player.recoil_offset
        draw_x = player.x + recoil_x + camera_offset[0]
        draw_y = player.y + recoil_y + camera_offset[1]
        if not self._is_world_point_visible(draw_x, draw_y, 96.0):
            return
        tint = pr.WHITE if player.hurt_alpha <= 0.0 else pr.fade(pr.RED, min(1.0, 0.35 + player.hurt_alpha * 0.55))
        self._draw_centered_texture(texture, draw_x, draw_y, rotation_deg=player.facing_angle_deg, tint=tint)
        if show_hitbox:
            rect_x = int(round(player.left + camera_offset[0]))
            rect_y = int(round(player.top + camera_offset[1]))
            outline = pr.MAROON if player.is_dead else pr.RED
            pr.draw_rectangle_lines(rect_x, rect_y, int(round(player.width)), int(round(player.height)), outline)
            pr.draw_circle(int(round(draw_x)), int(round(draw_y)), 3, pr.YELLOW)

    def draw_enemies(
        self,
        enemies: list[Enemy],
        camera_offset: tuple[int, int] = (0, 0),
        show_hitbox: bool = False,
        show_health: bool = False,
    ) -> None:
        texture = self.atlas.get("player")
        for enemy in enemies:
            if enemy.is_dead and not enemy.is_corpse_visible:
                continue
            draw_x = enemy.x + camera_offset[0]
            draw_y = enemy.y + camera_offset[1]
            if not self._is_world_point_visible(draw_x, draw_y, 96.0):
                continue
            if enemy.is_dead:
                tint = pr.fade(pr.DARKGRAY, max(0.2, enemy.corpse_alpha * 0.7))
            elif enemy.hurt_alpha > 0.0:
                tint = pr.fade(pr.RED, min(1.0, 0.45 + enemy.hurt_alpha * 0.5))
            else:
                tint = pr.fade(pr.SKYBLUE, 0.92)
            self._draw_centered_texture(texture, draw_x, draw_y, rotation_deg=enemy.facing_angle_deg, tint=tint)
            if show_hitbox:
                rect_x = int(round(enemy.left + camera_offset[0]))
                rect_y = int(round(enemy.top + camera_offset[1]))
                outline = pr.MAROON if enemy.is_dead else pr.RED
                pr.draw_rectangle_lines(rect_x, rect_y, int(round(enemy.width)), int(round(enemy.height)), outline)
                pr.draw_circle(int(round(draw_x)), int(round(draw_y)), 3, pr.ORANGE)
            if show_health and not enemy.is_dead:
                self._draw_enemy_health(enemy, draw_x, draw_y)


    def _draw_enemy_health(self, enemy: Enemy, draw_x: float, draw_y: float) -> None:
        health_text = f"{enemy.health:.0f}"
        font_size = 18
        text_width = pr.measure_text(health_text, font_size)
        text_x = int(round(draw_x - text_width / 2))
        text_y = int(round(draw_y - self.tile_size * 0.72))
        pr.draw_rectangle(text_x - 4, text_y - 2, text_width + 8, font_size + 4, pr.fade(pr.BLACK, 0.55))
        pr.draw_text(health_text, text_x, text_y, font_size, pr.LIME)

    def draw_vision_cones(self, previews: list[VisionConePreview], camera_offset: tuple[int, int] = (0, 0)) -> None:
        for preview in previews:
            if not self._is_world_point_visible(preview.origin_x + camera_offset[0], preview.origin_y + camera_offset[1], 160.0):
                continue
            color = pr.fade(pr.RED if preview.player_visible else pr.GREEN, 0.75)
            origin = pr.Vector2(preview.origin_x + camera_offset[0], preview.origin_y + camera_offset[1])
            left = pr.Vector2(preview.left_hit.x + camera_offset[0], preview.left_hit.y + camera_offset[1])
            right = pr.Vector2(preview.right_hit.x + camera_offset[0], preview.right_hit.y + camera_offset[1])
            center = pr.Vector2(preview.center_hit.x + camera_offset[0], preview.center_hit.y + camera_offset[1])
            pr.draw_line_ex(origin, left, 2.0, color)
            pr.draw_line_ex(origin, right, 2.0, color)
            pr.draw_line_ex(origin, center, 1.0, pr.fade(color, 0.65))
            pr.draw_circle(int(round(origin.x)), int(round(origin.y)), 3, color)

    def draw_debug_beam(self, preview: AimPreview, camera_offset: tuple[int, int] = (0, 0)) -> None:
        start = pr.Vector2(preview.muzzle_x + camera_offset[0], preview.muzzle_y + camera_offset[1])
        end = pr.Vector2(preview.hit.x + camera_offset[0], preview.hit.y + camera_offset[1])
        beam_color = pr.fade(pr.RED, 0.65) if preview.hit.hit else pr.fade(pr.SKYBLUE, 0.55)
        pr.draw_line_ex(start, end, 2.0, beam_color)
        pr.draw_circle_v(start, 3.0, pr.fade(pr.RED, 0.80))
        pr.draw_circle_v(end, 3.0, pr.fade(pr.YELLOW, 0.85))

    def draw_tracers(self, tracers: list[TracerEffect], camera_offset: tuple[int, int] = (0, 0)) -> None:
        for tracer in tracers:
            if not self._segment_might_be_visible(tracer.start_x + camera_offset[0], tracer.start_y + camera_offset[1], tracer.end_x + camera_offset[0], tracer.end_y + camera_offset[1]):
                continue
            alpha = max(0.10, tracer.alpha)
            start = pr.Vector2(tracer.start_x + camera_offset[0], tracer.start_y + camera_offset[1])
            end = pr.Vector2(tracer.end_x + camera_offset[0], tracer.end_y + camera_offset[1])
            pr.draw_line_ex(start, end, tracer.width, pr.fade(pr.GOLD, alpha))
            pr.draw_line_ex(start, end, tracer.core_width, pr.fade(pr.WHITE, min(1.0, alpha * 1.1)))
            pr.draw_circle_v(end, max(1.0, tracer.width * 0.55), pr.fade(pr.WHITE, min(1.0, alpha * 0.95)))


    def draw_blood_decals(self, decals: list[BloodDecal], camera_offset: tuple[int, int] = (0, 0)) -> None:
        for decal in decals:
            center_x = decal.x + camera_offset[0]
            center_y = decal.y + camera_offset[1]
            if not self._is_world_point_visible(center_x, center_y, 64.0):
                continue
            alpha = max(0.14, decal.alpha)
            angle_rad = math.radians(decal.angle_deg)
            half = decal.size / 2.0
            dx = math.cos(angle_rad) * half
            dy = math.sin(angle_rad) * half
            side_x = -dy * 0.36
            side_y = dx * 0.36
            tip = pr.Vector2(center_x + dx, center_y + dy)
            left = pr.Vector2(center_x - dx + side_x, center_y - dy + side_y)
            right = pr.Vector2(center_x - dx - side_x, center_y - dy - side_y)
            pr.draw_triangle(tip, left, right, pr.fade(pr.Color(120, 0, 0, 255), alpha * 0.7))
            pr.draw_circle(int(round(center_x)), int(round(center_y)), max(1, int(round(decal.size * 0.16))), pr.fade(pr.Color(160, 10, 10, 255), alpha * 0.9))

    def draw_blood_pools(self, pools: list[BloodPool], camera_offset: tuple[int, int] = (0, 0)) -> None:
        for pool in pools:
            center_x = pool.x + camera_offset[0]
            center_y = pool.y + camera_offset[1]
            if not self._is_world_point_visible(center_x, center_y, 96.0):
                continue
            alpha = 0.88
            radius_x = pool.size * (0.55 + pool.growth_alpha * 0.45)
            radius_y = pool.size * (0.38 + pool.growth_alpha * 0.30)
            color_outer = pr.fade(pr.Color(72, 0, 0, 255), alpha)
            color_inner = pr.fade(pr.Color(122, 8, 8, 255), alpha * 0.85)
            self._draw_ellipse(center_x, center_y, radius_x, radius_y, color_outer)
            self._draw_ellipse(center_x + radius_x * 0.08, center_y - radius_y * 0.05, radius_x * 0.62, radius_y * 0.52, color_inner)

    def draw_blood_particles(self, particles: list[BloodParticle], camera_offset: tuple[int, int] = (0, 0)) -> None:
        for particle in particles:
            center_x = particle.x + camera_offset[0]
            center_y = particle.y + camera_offset[1]
            if not self._is_world_point_visible(center_x, center_y, 48.0):
                continue
            alpha = max(0.08, particle.alpha)
            radius = max(1, int(round(particle.size * 0.55)))
            pr.draw_circle(int(round(center_x)), int(round(center_y)), radius, pr.fade(pr.Color(188, 16, 16, 255), alpha))

    def draw_impact_marks(self, impact_marks: list[ImpactMark], camera_offset: tuple[int, int] = (0, 0)) -> None:
        for mark in impact_marks:
            if not self._is_world_point_visible(mark.x + camera_offset[0], mark.y + camera_offset[1], 48.0):
                continue
            alpha = max(0.12, mark.alpha)
            center_x = mark.x + camera_offset[0]
            center_y = mark.y + camera_offset[1]
            hole_color = pr.fade(pr.BLACK, min(0.95, alpha + 0.15))
            hole_radius = max(1, int(round(mark.hole_diameter / 2.0)))
            pr.draw_circle(int(round(center_x)), int(round(center_y)), hole_radius, hole_color)
            ring_color = self._impact_color(mark.surface_kind, alpha)
            half = mark.size / 2.0
            angle_rad = math.radians(mark.angle_deg)
            dx = math.cos(angle_rad) * half
            dy = math.sin(angle_rad) * half
            start = pr.Vector2(center_x - dx, center_y - dy)
            end = pr.Vector2(center_x + dx, center_y + dy)
            pr.draw_line_ex(start, end, 2.0, ring_color)

    def draw_impact_debris(self, particles: list[ImpactDebrisParticle], camera_offset: tuple[int, int] = (0, 0)) -> None:
        for particle in particles:
            if not self._is_world_point_visible(particle.x + camera_offset[0], particle.y + camera_offset[1], 48.0):
                continue
            alpha = max(0.08, particle.alpha)
            color = self._impact_color(particle.surface_kind, alpha)
            center_x = particle.x + camera_offset[0]
            center_y = particle.y + camera_offset[1]
            half = particle.size / 2.0
            angle_rad = math.radians(particle.angle_deg)
            dx = math.cos(angle_rad) * half
            dy = math.sin(angle_rad) * half
            start = pr.Vector2(center_x - dx, center_y - dy)
            end = pr.Vector2(center_x + dx, center_y + dy)
            pr.draw_line_ex(start, end, max(1.0, particle.size * 0.55), color)

    def draw_muzzle_flashes(self, muzzle_flashes: list[MuzzleFlashEffect], camera_offset: tuple[int, int] = (0, 0)) -> None:
        white_hot = pr.Color(255, 251, 238, 255)
        hot_yellow = pr.Color(255, 228, 80, 255)
        hot_orange = pr.Color(255, 142, 20, 255)
        ember = pr.Color(255, 96, 18, 255)
        for flash in muzzle_flashes:
            if not self._is_world_point_visible(flash.x + camera_offset[0], flash.y + camera_offset[1], 96.0):
                continue
            alpha = max(0.18, flash.alpha)
            origin_x = flash.x + camera_offset[0]
            origin_y = flash.y + camera_offset[1]
            angle_rad = math.radians(flash.angle_deg)
            forward_x = math.cos(angle_rad)
            forward_y = math.sin(angle_rad)
            right_x = -forward_y
            right_y = forward_x
            size = flash.size * (0.84 + flash.alpha * 0.32)
            self._draw_flash_bloom(origin_x, origin_y, forward_x, forward_y, right_x, right_y, size, alpha * 0.30)
            self._draw_flash_spear(origin_x, origin_y, forward_x, forward_y, right_x, right_y, size, alpha * 0.90, hot_orange, 1.00, flash.variant)
            self._draw_flash_spear(origin_x, origin_y, forward_x, forward_y, right_x, right_y, size, alpha, hot_yellow, 0.72, flash.variant)
            self._draw_flash_spear(origin_x, origin_y, forward_x, forward_y, right_x, right_y, size, alpha, white_hot, 0.38, flash.variant)
            self._draw_flash_spikes(origin_x, origin_y, forward_x, forward_y, right_x, right_y, size, alpha * 0.78, ember, flash.variant)

    def draw_shell_casings(self, shell_casings: list[ShellCasing], camera_offset: tuple[int, int] = (0, 0)) -> None:
        for shell in shell_casings:
            center_x = shell.x + camera_offset[0]
            center_y = shell.y + camera_offset[1]
            if not self._is_world_point_visible(center_x, center_y, 32.0):
                continue
            alpha = max(0.12, shell.alpha)
            half_w = shell.size * 0.65
            half_h = max(1.2, shell.size * 0.32)
            angle_rad = math.radians(shell.angle_deg)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            points = []
            for local_x, local_y in ((-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)):
                world_x = center_x + local_x * cos_a - local_y * sin_a
                world_y = center_y + local_x * sin_a + local_y * cos_a
                points.append(pr.Vector2(world_x, world_y))
            fill = pr.fade(pr.GOLD, alpha)
            glow = pr.fade(pr.YELLOW, min(1.0, alpha * 0.9))
            pr.draw_triangle(points[0], points[1], points[2], fill)
            pr.draw_triangle(points[0], points[2], points[3], fill)
            pr.draw_line_ex(points[0], points[1], 1.0, glow)
            pr.draw_line_ex(points[1], points[2], 1.0, pr.fade(pr.WHITE, alpha * 0.75))

    def draw_muzzle_smoke(self, smoke_particles: list[MuzzleSmokeParticle], camera_offset: tuple[int, int] = (0, 0)) -> None:
        for particle in smoke_particles:
            center_x = particle.x + camera_offset[0]
            center_y = particle.y + camera_offset[1]
            if not self._is_world_point_visible(center_x, center_y, 64.0):
                continue
            outer_radius = max(1, int(round(particle.size)))
            inner_radius = max(1, int(round(particle.size * 0.55)))
            pr.draw_circle(int(round(center_x)), int(round(center_y)), outer_radius, pr.fade(pr.LIGHTGRAY, max(0.03, particle.alpha * 0.35)))
            pr.draw_circle(int(round(center_x)), int(round(center_y)), inner_radius, pr.fade(pr.GRAY, max(0.04, particle.alpha * 0.55)))


    def _draw_flash_bloom(
        self,
        origin_x: float,
        origin_y: float,
        forward_x: float,
        forward_y: float,
        right_x: float,
        right_y: float,
        base_size: float,
        alpha: float,
    ) -> None:
        smoke = pr.Color(236, 236, 236, 255)
        hot_smoke = pr.Color(255, 210, 150, 255)
        center = pr.Vector2(origin_x + forward_x * base_size * 0.18, origin_y + forward_y * base_size * 0.18)
        radius = max(1, int(round(base_size * 0.16)))
        pr.draw_circle(int(round(center.x)), int(round(center.y)), radius, pr.fade(smoke, alpha * 0.55))
        pr.draw_circle(int(round(center.x)), int(round(center.y)), max(1, int(round(radius * 0.55))), pr.fade(hot_smoke, alpha * 0.85))

    def _draw_flash_spear(
        self,
        origin_x: float,
        origin_y: float,
        forward_x: float,
        forward_y: float,
        right_x: float,
        right_y: float,
        base_size: float,
        alpha: float,
        color: pr.Color,
        scale: float,
        variant: int,
    ) -> None:
        length = base_size * scale * (1.45 + variant * 0.08)
        width = base_size * scale * (0.24 + (variant % 2) * 0.03)
        base_forward = base_size * scale * 0.04
        base_spread = base_size * scale * 0.10
        tip = pr.Vector2(origin_x + forward_x * length, origin_y + forward_y * length)
        left = pr.Vector2(
            origin_x + forward_x * base_forward + right_x * (width + base_spread),
            origin_y + forward_y * base_forward + right_y * (width + base_spread),
        )
        right = pr.Vector2(
            origin_x + forward_x * base_forward - right_x * (width + base_spread),
            origin_y + forward_y * base_forward - right_y * (width + base_spread),
        )
        pr.draw_triangle(tip, left, right, pr.fade(color, alpha))

    def _draw_flash_spikes(
        self,
        origin_x: float,
        origin_y: float,
        forward_x: float,
        forward_y: float,
        right_x: float,
        right_y: float,
        base_size: float,
        alpha: float,
        color: pr.Color,
        variant: int,
    ) -> None:
        side_length = base_size * (0.52 + variant * 0.04)
        side_width = base_size * 0.16
        forward_bias = base_size * 0.18
        left_tip = pr.Vector2(
            origin_x + forward_x * forward_bias + right_x * side_length,
            origin_y + forward_y * forward_bias + right_y * side_length,
        )
        right_tip = pr.Vector2(
            origin_x + forward_x * forward_bias - right_x * side_length,
            origin_y + forward_y * forward_bias - right_y * side_length,
        )
        left_a = pr.Vector2(origin_x + right_x * side_width, origin_y + right_y * side_width)
        left_b = pr.Vector2(
            origin_x + forward_x * base_size * 0.30 + right_x * side_width * 1.1,
            origin_y + forward_y * base_size * 0.30 + right_y * side_width * 1.1,
        )
        right_a = pr.Vector2(origin_x - right_x * side_width, origin_y - right_y * side_width)
        right_b = pr.Vector2(
            origin_x + forward_x * base_size * 0.30 - right_x * side_width * 1.1,
            origin_y + forward_y * base_size * 0.30 - right_y * side_width * 1.1,
        )
        pr.draw_triangle(left_tip, left_a, left_b, pr.fade(color, alpha))
        pr.draw_triangle(right_tip, right_a, right_b, pr.fade(color, alpha))


    @staticmethod
    def _draw_ellipse(center_x: float, center_y: float, radius_x: float, radius_y: float, color: pr.Color) -> None:
        steps = 14
        points: list[pr.Vector2] = []
        for index in range(steps):
            angle = math.tau * index / steps
            points.append(pr.Vector2(center_x + math.cos(angle) * radius_x, center_y + math.sin(angle) * radius_y))
        center = pr.Vector2(center_x, center_y)
        for index in range(steps):
            pr.draw_triangle(center, points[index], points[(index + 1) % steps], color)

    def _draw_tile_texture(self, texture: pr.Texture, draw_x: float, draw_y: float) -> None:
        source = pr.Rectangle(0, 0, float(texture.width), float(texture.height))
        destination = pr.Rectangle(float(draw_x), float(draw_y), float(self.tile_size), float(self.tile_size))
        pr.draw_texture_pro(texture, source, destination, pr.Vector2(0.0, 0.0), 0.0, pr.WHITE)

    def _draw_centered_texture(self, texture: pr.Texture, center_x: float, center_y: float, rotation_deg: float = 0.0, tint: pr.Color = pr.WHITE) -> None:
        source = pr.Rectangle(0, 0, float(texture.width), float(texture.height))
        destination = pr.Rectangle(float(center_x), float(center_y), float(self.tile_size), float(self.tile_size))
        origin = pr.Vector2(float(self.tile_size / 2.0), float(self.tile_size / 2.0))
        pr.draw_texture_pro(texture, source, destination, origin, rotation_deg, tint)


    def _visible_tile_bounds(self, tile_map: TileMap, camera_offset: tuple[int, int]) -> tuple[int, int, int, int]:
        screen_w = pr.get_screen_width()
        screen_h = pr.get_screen_height()
        margin_tiles = 2
        min_x = max(0, int((-camera_offset[0]) // self.tile_size) - margin_tiles)
        min_y = max(0, int((-camera_offset[1]) // self.tile_size) - margin_tiles)
        max_x = min(tile_map.width - 1, int((screen_w - camera_offset[0]) // self.tile_size) + margin_tiles)
        max_y = min(tile_map.height - 1, int((screen_h - camera_offset[1]) // self.tile_size) + margin_tiles)
        return min_x, max_x, min_y, max_y

    @staticmethod
    def _is_world_point_visible(screen_x: float, screen_y: float, margin: float = 0.0) -> bool:
        screen_w = pr.get_screen_width()
        screen_h = pr.get_screen_height()
        return -margin <= screen_x <= screen_w + margin and -margin <= screen_y <= screen_h + margin

    @classmethod
    def _segment_might_be_visible(cls, start_x: float, start_y: float, end_x: float, end_y: float) -> bool:
        if cls._is_world_point_visible(start_x, start_y, 16.0) or cls._is_world_point_visible(end_x, end_y, 16.0):
            return True
        screen_w = pr.get_screen_width()
        screen_h = pr.get_screen_height()
        min_x = min(start_x, end_x)
        max_x = max(start_x, end_x)
        min_y = min(start_y, end_y)
        max_y = max(start_y, end_y)
        return not (max_x < 0 or min_x > screen_w or max_y < 0 or min_y > screen_h)

    def _draw_cover_block(self, draw_x: float, draw_y: float) -> None:
        inset = max(6, self.tile_size // 8)
        outer_x = int(round(draw_x + inset))
        outer_y = int(round(draw_y + inset))
        outer_w = self.tile_size - inset * 2
        outer_h = self.tile_size - inset * 2
        pr.draw_rectangle(outer_x, outer_y, outer_w, outer_h, pr.fade(pr.DARKBROWN, 0.92))
        pr.draw_rectangle_lines(outer_x, outer_y, outer_w, outer_h, pr.fade(pr.BEIGE, 0.8))

    def _select_wall_texture(self, tile_map: TileMap, x: int, y: int) -> pr.Texture:
        north = self._is_wall(tile_map, x, y - 1)
        south = self._is_wall(tile_map, x, y + 1)
        west = self._is_wall(tile_map, x - 1, y)
        east = self._is_wall(tile_map, x + 1, y)
        if not north and east and south and not west:
            return self.atlas.get("wall_top_left")
        if not north and not east and south and west:
            return self.atlas.get("wall_top_right")
        if north and east and not south and not west:
            return self.atlas.get("wall_bottom_left")
        if north and not east and not south and west:
            return self.atlas.get("wall_bottom_right")
        if (north or south) and not (west and east):
            return self.atlas.get("wall_vertical")
        if (west or east) and not (north and south):
            return self.atlas.get("wall_horizontal")
        return self.atlas.get("wall_center")

    @staticmethod
    def _impact_color(surface_kind: TileKind, alpha: float) -> pr.Color:
        if surface_kind is TileKind.WALL:
            return pr.fade(pr.LIGHTGRAY, alpha)
        if surface_kind is TileKind.WOOD_FLOOR:
            return pr.fade(pr.BROWN, alpha)
        if surface_kind is TileKind.TILE_FLOOR:
            return pr.fade(pr.GRAY, alpha)
        if surface_kind is TileKind.DIRT:
            return pr.fade(pr.BEIGE, alpha)
        if surface_kind is TileKind.GRASS:
            return pr.fade(pr.LIME, alpha)
        return pr.fade(pr.RAYWHITE, alpha)

    @staticmethod
    def _is_wall(tile_map: TileMap, x: int, y: int) -> bool:
        return tile_map.in_bounds(x, y) and tile_map.get_tile(x, y) is TileKind.WALL
