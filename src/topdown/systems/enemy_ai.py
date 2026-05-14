from __future__ import annotations

from dataclasses import dataclass
import math
import random

from topdown.entities.enemy import Enemy
from topdown.entities.player import Player
from topdown.systems.combat import CombatState, CombatSystem
from topdown.world.collision import CollisionResolver, MovementCommand
from topdown.world.map_model import TileMap
from topdown.world.raycast import RaycastHit, RaycastResolver


@dataclass(slots=True, frozen=True)
class VisionConePreview:
    """Debug preview for a single enemy vision cone."""

    origin_x: float
    origin_y: float
    center_hit: RaycastHit
    left_hit: RaycastHit
    right_hit: RaycastHit
    player_visible: bool


class EnemyAiSystem:
    """Drive enemy sensing, coordination, cover, and combat behavior."""

    def __init__(self, tile_size: int, collision_resolver: CollisionResolver) -> None:
        self._tile_size = tile_size
        self._raycast = RaycastResolver(tile_size=tile_size)
        self._collision_resolver = collision_resolver
        self._random = random.Random(1337)

    def update(
        self,
        enemies: list[Enemy],
        player: Player,
        tile_map: TileMap,
        delta_time: float,
        combat_system: CombatSystem | None = None,
        combat_state: CombatState | None = None,
    ) -> float:
        """Advance enemy state machines for one frame and return damage dealt to the player."""
        total_damage = 0.0
        alive_enemies = [enemy for enemy in enemies if not enemy.is_dead]
        visible_enemies: list[Enemy] = []
        for enemy in alive_enemies:
            enemy.update_timers(delta_time)
            player_visible = self.can_see_player(enemy=enemy, player=player, tile_map=tile_map)
            enemy.sees_player = player_visible
            if player_visible:
                enemy.remember_player(player.x, player.y)
                enemy.broadcast_alarm()
                enemy.update_facing_from_point(player.x, player.y)
                visible_enemies.append(enemy)

        if visible_enemies:
            self._broadcast_alarm(visible_enemies=visible_enemies, enemies=alive_enemies, player=player)
        self._assign_roles(enemies=alive_enemies, player=player)

        self._resolve_overlap(alive_enemies, tile_map, delta_time)
        for enemy in alive_enemies:
            if enemy.sees_player:
                total_damage += self._handle_visible_player(
                    enemy=enemy,
                    player=player,
                    tile_map=tile_map,
                    delta_time=delta_time,
                    alive_enemies=alive_enemies,
                    combat_system=combat_system,
                    combat_state=combat_state,
                )
                continue

            if enemy.has_memory or enemy.has_recent_alarm():
                enemy.state = "search"
                self._handle_search(enemy=enemy, tile_map=tile_map, delta_time=delta_time, alive_enemies=alive_enemies)
            else:
                enemy.clear_memory()
                enemy.role = "solo"
                enemy.state = "idle_guard"
                self._update_idle_scan(enemy=enemy, delta_time=delta_time)
        return total_damage

    def can_see_player(self, enemy: Enemy, player: Player, tile_map: TileMap) -> bool:
        to_player_x = player.x - enemy.x
        to_player_y = player.y - enemy.y
        distance = math.hypot(to_player_x, to_player_y)
        if distance == 0.0:
            return True
        if distance > enemy.vision_distance:
            return False

        facing_x = math.cos(math.radians(enemy.facing_angle_deg))
        facing_y = math.sin(math.radians(enemy.facing_angle_deg))
        direction_x = to_player_x / distance
        direction_y = to_player_y / distance
        dot = max(-1.0, min(1.0, facing_x * direction_x + facing_y * direction_y))
        angle_delta = math.degrees(math.acos(dot))
        if angle_delta > enemy.vision_fov_degrees / 2.0:
            return False

        hit = self._raycast.cast(
            tile_map=tile_map,
            origin_x=enemy.x,
            origin_y=enemy.y,
            direction_x=direction_x,
            direction_y=direction_y,
            max_distance=distance,
        )
        return not hit.hit or hit.distance >= distance - 8.0

    def build_vision_preview(self, enemy: Enemy, player: Player, tile_map: TileMap) -> VisionConePreview:
        center_angle = math.radians(enemy.facing_angle_deg)
        half_fov = math.radians(enemy.vision_fov_degrees / 2.0)
        center_hit = self._cast_angle(enemy, tile_map, center_angle)
        left_hit = self._cast_angle(enemy, tile_map, center_angle - half_fov)
        right_hit = self._cast_angle(enemy, tile_map, center_angle + half_fov)
        return VisionConePreview(
            origin_x=enemy.x,
            origin_y=enemy.y,
            center_hit=center_hit,
            left_hit=left_hit,
            right_hit=right_hit,
            player_visible=self.can_see_player(enemy=enemy, player=player, tile_map=tile_map),
        )

    def _cast_angle(self, enemy: Enemy, tile_map: TileMap, angle_radians: float) -> RaycastHit:
        direction_x = math.cos(angle_radians)
        direction_y = math.sin(angle_radians)
        return self._raycast.cast(
            tile_map=tile_map,
            origin_x=enemy.x,
            origin_y=enemy.y,
            direction_x=direction_x,
            direction_y=direction_y,
            max_distance=enemy.vision_distance,
        )

    def _broadcast_alarm(self, visible_enemies: list[Enemy], enemies: list[Enemy], player: Player) -> None:
        for spotter in visible_enemies:
            for ally in enemies:
                if ally is spotter:
                    continue
                distance = math.hypot(ally.x - spotter.x, ally.y - spotter.y)
                if distance > spotter.coordination_range:
                    continue
                ally.remember_player(player.x, player.y)
                ally.broadcast_alarm()

    def _assign_roles(self, enemies: list[Enemy], player: Player) -> None:
        active = [enemy for enemy in enemies if enemy.sees_player or enemy.has_memory or enemy.has_recent_alarm()]
        if not active:
            return
        active.sort(key=lambda enemy: math.hypot(enemy.x - player.x, enemy.y - player.y))
        for index, enemy in enumerate(active):
            if len(active) == 1:
                enemy.role = "solo"
            elif index == 0:
                enemy.role = "suppressor"
            elif index == 1:
                enemy.role = "flanker"
                enemy.strafe_sign = -1
            else:
                enemy.role = "anchor"

    def _handle_visible_player(
        self,
        enemy: Enemy,
        player: Player,
        tile_map: TileMap,
        delta_time: float,
        alive_enemies: list[Enemy],
        combat_system: CombatSystem | None = None,
        combat_state: CombatState | None = None,
    ) -> float:
        to_player_x = player.x - enemy.x
        to_player_y = player.y - enemy.y
        distance = math.hypot(to_player_x, to_player_y)
        if distance == 0.0:
            return 0.0
        direction_x = to_player_x / distance
        direction_y = to_player_y / distance

        if enemy.health_ratio() <= enemy.retreat_health_threshold:
            enemy.state = "combat_retreat"
            return self._move_to_cover_or_backstep(enemy, player, tile_map, delta_time, alive_enemies, retreat=True)

        if enemy.needs_reload():
            enemy.start_reload()
        if enemy.reload_remaining > 0.0:
            enemy.state = "reload"
            return self._move_to_cover_or_backstep(enemy, player, tile_map, delta_time, alive_enemies, retreat=True)

        if enemy.state in {"take_cover", "reposition"} and enemy.cover_anchor_x is not None and enemy.cover_anchor_y is not None:
            if self._move_to_anchor(enemy, enemy.cover_anchor_x, enemy.cover_anchor_y, tile_map, delta_time, alive_enemies, enemy.speed):
                enemy.cover_anchor_x = None
                enemy.cover_anchor_y = None
                enemy.hold_current_position()
            return 0.0

        if enemy.position_hold_remaining <= 0.0 and self._needs_cover(enemy, player, distance, tile_map):
            anchor = self._find_cover_anchor(enemy=enemy, player=player, tile_map=tile_map, alive_enemies=alive_enemies, prefer_flank=enemy.role == "flanker")
            if anchor is not None and self._should_start_reposition(enemy, anchor):
                enemy.cover_anchor_x, enemy.cover_anchor_y = anchor
                enemy.state = "take_cover" if enemy.role != "flanker" else "reposition"
                enemy.commit_reposition()
                self._move_to_anchor(enemy, anchor[0], anchor[1], tile_map, delta_time, alive_enemies, enemy.speed)
                return 0.0

        if distance <= enemy.attack_range:
            if enemy.can_attack():
                enemy.state = "attack"
                enemy.start_attack_cooldown()
                enemy.consume_ammo()
                return enemy.attack_damage
            return 0.0

        if distance <= enemy.fire_range:
            if combat_system is None or combat_state is None:
                return 0.0
            if enemy.state == "aim" and enemy.fire_reaction_remaining <= 0.0 and enemy.reload_remaining <= 0.0:
                shot = combat_system.enemy_fire(
                    state=combat_state,
                    tile_map=tile_map,
                    enemy=enemy,
                    target_x=player.x,
                    target_y=player.y,
                )
                enemy.start_attack_cooldown()
                enemy.consume_ammo()
                enemy.state = "combat_suppress" if enemy.role == "suppressor" else "combat_attack"
                return shot.damage
            if enemy.is_attack_winding_up():
                enemy.state = "aim"
                return 0.0
            if enemy.can_attack() and self._has_good_shot(enemy, player, tile_map):
                enemy.state = "aim"
                enemy.start_attack_windup()
                return 0.0

        if enemy.role == "flanker" and enemy.can_reposition() and self._random.random() <= enemy.reposition_chance:
            enemy.state = "reposition"
            enemy.commit_reposition()
            self._move_flank(enemy, direction_x, direction_y, tile_map, delta_time, alive_enemies)
        elif distance > enemy.stop_distance:
            enemy.state = "combat_advance"
            self._move_enemy(enemy, direction_x, direction_y, enemy.speed, delta_time, tile_map, alive_enemies)
        else:
            enemy.state = "strafe"
            move_x, move_y = self._compute_strafe_movement(enemy, direction_x, direction_y)
            self._move_enemy(enemy, move_x, move_y, enemy.speed, delta_time, tile_map, alive_enemies)
        return 0.0

    def _handle_search(self, enemy: Enemy, tile_map: TileMap, delta_time: float, alive_enemies: list[Enemy]) -> None:
        target_x, target_y = self._current_search_target(enemy)
        enemy.update_facing_from_point(target_x, target_y)
        to_target_x = target_x - enemy.x
        to_target_y = target_y - enemy.y
        distance = math.hypot(to_target_x, to_target_y)
        if distance <= 18.0:
            enemy.search_target_index = (enemy.search_target_index + 1) % 5
            if enemy.search_target_index == 0 and enemy.memory_remaining <= 0.0 and enemy.alarm_remaining <= 0.0:
                enemy.clear_memory()
                enemy.state = "return_to_post"
                return
            self._update_idle_scan(enemy=enemy, delta_time=delta_time)
            return
        move_x = to_target_x / distance
        move_y = to_target_y / distance
        enemy.state = "investigate"
        self._move_enemy(enemy, move_x, move_y, enemy.speed * 0.82, delta_time, tile_map, alive_enemies)

    def _current_search_target(self, enemy: Enemy) -> tuple[float, float]:
        if enemy.last_seen_x is None or enemy.last_seen_y is None:
            return enemy.x, enemy.y
        offsets = [
            (0.0, 0.0),
            (28.0, 0.0),
            (-28.0, 0.0),
            (0.0, 28.0),
            (0.0, -28.0),
        ]
        offset_x, offset_y = offsets[enemy.search_target_index % len(offsets)]
        return enemy.last_seen_x + offset_x, enemy.last_seen_y + offset_y

    def _update_idle_scan(self, enemy: Enemy, delta_time: float) -> None:
        enemy.facing_angle_deg += enemy.search_turn_speed_degrees * enemy.strafe_sign * delta_time
        if abs(enemy.facing_angle_deg) > 180.0:
            enemy.facing_angle_deg = ((enemy.facing_angle_deg + 180.0) % 360.0) - 180.0

    def _compute_strafe_movement(self, enemy: Enemy, dir_x: float, dir_y: float) -> tuple[float, float]:
        perpendicular_x = -dir_y * enemy.strafe_sign
        perpendicular_y = dir_x * enemy.strafe_sign
        return perpendicular_x * enemy.strafe_speed_multiplier, perpendicular_y * enemy.strafe_speed_multiplier

    def _should_start_reposition(self, enemy: Enemy, anchor: tuple[float, float]) -> bool:
        if not enemy.can_reposition():
            return False
        anchor_distance = math.hypot(anchor[0] - enemy.x, anchor[1] - enemy.y)
        if anchor_distance < enemy.reposition_min_distance:
            return False
        return self._random.random() <= enemy.reposition_chance

    def _needs_cover(self, enemy: Enemy, player: Player, distance: float, tile_map: TileMap) -> bool:
        if enemy.role == "anchor":
            return True
        if distance > enemy.fire_range * 0.55:
            return True
        return not self._is_position_near_cover(enemy.x, enemy.y, enemy, player, tile_map)

    def _has_good_shot(self, enemy: Enemy, player: Player, tile_map: TileMap) -> bool:
        to_player_x = player.x - enemy.x
        to_player_y = player.y - enemy.y
        distance = math.hypot(to_player_x, to_player_y)
        if distance <= 1e-6:
            return True
        direction_x = to_player_x / distance
        direction_y = to_player_y / distance
        hit = self._raycast.cast(tile_map, enemy.x, enemy.y, direction_x, direction_y, distance)
        return (not hit.hit) or hit.distance >= distance - 8.0

    def _move_flank(self, enemy: Enemy, dir_x: float, dir_y: float, tile_map: TileMap, delta_time: float, alive_enemies: list[Enemy]) -> None:
        side_x, side_y = self._compute_strafe_movement(enemy, dir_x, dir_y)
        self._move_enemy(enemy, dir_x * 0.35 + side_x, dir_y * 0.35 + side_y, enemy.speed, delta_time, tile_map, alive_enemies)

    def _move_to_cover_or_backstep(
        self,
        enemy: Enemy,
        player: Player,
        tile_map: TileMap,
        delta_time: float,
        alive_enemies: list[Enemy],
        retreat: bool,
    ) -> float:
        anchor = self._find_cover_anchor(enemy=enemy, player=player, tile_map=tile_map, alive_enemies=alive_enemies, prefer_flank=False, prefer_far=retreat)
        if anchor is not None:
            enemy.cover_anchor_x, enemy.cover_anchor_y = anchor
            self._move_to_anchor(enemy, anchor[0], anchor[1], tile_map, delta_time, alive_enemies, enemy.speed)
            return 0.0
        to_player_x = enemy.x - player.x
        to_player_y = enemy.y - player.y
        distance = math.hypot(to_player_x, to_player_y)
        if distance <= 1e-6:
            return 0.0
        self._move_enemy(enemy, to_player_x / distance, to_player_y / distance, enemy.speed * 0.8, delta_time, tile_map, alive_enemies)
        return 0.0

    def _find_cover_anchor(
        self,
        enemy: Enemy,
        player: Player,
        tile_map: TileMap,
        alive_enemies: list[Enemy],
        prefer_flank: bool,
        prefer_far: bool = False,
    ) -> tuple[float, float] | None:
        enemy_tile_x = int(enemy.x // self._tile_size)
        enemy_tile_y = int(enemy.y // self._tile_size)
        player_tile_x = int(player.x // self._tile_size)
        player_tile_y = int(player.y // self._tile_size)
        best_score = float("-inf")
        best_anchor: tuple[float, float] | None = None
        max_tiles = max(2, enemy.cover_search_radius_tiles)
        for node in tile_map.cover_nodes:
            if abs(node.tile_x - enemy_tile_x) > max_tiles or abs(node.tile_y - enemy_tile_y) > max_tiles:
                continue
            anchor_x = node.tile_x * self._tile_size + self._tile_size / 2.0
            anchor_y = node.tile_y * self._tile_size + self._tile_size / 2.0
            if self._anchor_occupied(anchor_x, anchor_y, enemy, alive_enemies):
                continue
            hit = self._raycast.cast(
                tile_map=tile_map,
                origin_x=player.x,
                origin_y=player.y,
                direction_x=anchor_x - player.x,
                direction_y=anchor_y - player.y,
                max_distance=math.hypot(anchor_x - player.x, anchor_y - player.y),
            )
            if not hit.hit:
                continue
            anchor_distance = math.hypot(anchor_x - enemy.x, anchor_y - enemy.y)
            score = -anchor_distance
            score += self._cover_node_score(node.node_type)
            if prefer_far:
                score += math.hypot(anchor_x - player.x, anchor_y - player.y) * 0.35
            if prefer_flank:
                score += abs(node.tile_y - player_tile_y) * 6.0 + abs(node.tile_x - player_tile_x) * 2.5
            else:
                score += abs(node.tile_x - player_tile_x) * 2.0
            if score > best_score:
                best_score = score
                best_anchor = (anchor_x, anchor_y)
        if best_anchor is not None:
            return best_anchor
        return None


    @staticmethod
    def _cover_node_score(node_type: str) -> float:
        scores = {
            "hold": 12.0,
            "left_peek": 10.0,
            "right_peek": 10.0,
            "transition": 7.0,
            "fallback": 4.0,
        }
        return scores.get(node_type, 0.0)

    def _anchor_occupied(self, anchor_x: float, anchor_y: float, enemy: Enemy, alive_enemies: list[Enemy]) -> bool:
        for other in alive_enemies:
            if other is enemy:
                continue
            if math.hypot(other.x - anchor_x, other.y - anchor_y) < max(enemy.radius, 10.0) * 1.6:
                return True
        return False

    def _is_position_near_cover(self, x: float, y: float, enemy: Enemy, player: Player, tile_map: TileMap) -> bool:
        current_tile_x = int(x // self._tile_size)
        current_tile_y = int(y // self._tile_size)
        player_tile_x = int(player.x // self._tile_size)
        player_tile_y = int(player.y // self._tile_size)
        search_radius = max(2, enemy.cover_search_radius_tiles // 2)
        best_distance = float("inf")
        for node in tile_map.cover_nodes:
            if abs(node.tile_x - current_tile_x) > search_radius or abs(node.tile_y - current_tile_y) > search_radius:
                continue
            if node.node_type == "fallback" and math.hypot(node.tile_x - player_tile_x, node.tile_y - player_tile_y) < 2.0:
                continue
            distance = math.hypot(node.tile_x - current_tile_x, node.tile_y - current_tile_y)
            if distance < best_distance:
                best_distance = distance
        return best_distance <= max(1.6, search_radius * 0.5)

    def _move_to_anchor(
        self,
        enemy: Enemy,
        anchor_x: float,
        anchor_y: float,
        tile_map: TileMap,
        delta_time: float,
        alive_enemies: list[Enemy],
        speed: float,
    ) -> bool:
        to_anchor_x = anchor_x - enemy.x
        to_anchor_y = anchor_y - enemy.y
        distance = math.hypot(to_anchor_x, to_anchor_y)
        if distance <= 10.0:
            return True
        self._move_enemy(enemy, to_anchor_x / distance, to_anchor_y / distance, speed, delta_time, tile_map, alive_enemies)
        enemy.update_facing_from_point(anchor_x, anchor_y)
        return False

    def _move_enemy(
        self,
        enemy: Enemy,
        desired_x: float,
        desired_y: float,
        speed: float,
        delta_time: float,
        tile_map: TileMap,
        alive_enemies: list[Enemy],
    ) -> None:
        sep_x, sep_y = self._compute_separation(enemy, alive_enemies)
        move_x = desired_x + sep_x
        move_y = desired_y + sep_y
        length = math.hypot(move_x, move_y)
        if length <= 1e-6:
            return
        move_x /= length
        move_y /= length
        movement = MovementCommand(dx=move_x * speed * delta_time, dy=move_y * speed * delta_time)
        self._collision_resolver.move_actor(enemy, movement, tile_map)


    def _resolve_overlap(self, alive_enemies: list[Enemy], tile_map: TileMap, delta_time: float) -> None:
        for enemy in alive_enemies:
            sep_x, sep_y = self._compute_separation(enemy, alive_enemies)
            strength = math.hypot(sep_x, sep_y)
            if strength <= 1e-6:
                continue
            movement = MovementCommand(
                dx=sep_x * self._tile_size * 0.04 * delta_time,
                dy=sep_y * self._tile_size * 0.04 * delta_time,
            )
            self._collision_resolver.move_actor(enemy, movement, tile_map)

    def _compute_separation(self, enemy: Enemy, alive_enemies: list[Enemy]) -> tuple[float, float]:
        push_x = 0.0
        push_y = 0.0
        for other in alive_enemies:
            if other is enemy:
                continue
            delta_x = enemy.x - other.x
            delta_y = enemy.y - other.y
            distance = math.hypot(delta_x, delta_y)
            if distance <= 1e-6 or distance >= enemy.separation_distance:
                continue
            strength = (1.0 - distance / enemy.separation_distance) * enemy.separation_strength
            push_x += (delta_x / distance) * strength
            push_y += (delta_y / distance) * strength
        return push_x, push_y
