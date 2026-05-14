from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(slots=True)
class Enemy:
    """Mutable enemy state independent from the rendering backend."""

    x: float
    y: float
    width: float
    height: float
    speed: float
    health: float
    max_health: float
    vision_distance: float
    vision_fov_degrees: float
    stop_distance: float
    attack_damage: float
    attack_interval_seconds: float
    attack_range: float
    corpse_lifetime_seconds: float
    memory_seconds: float = 1.35
    strafe_speed_multiplier: float = 0.55
    separation_distance: float = 42.0
    separation_strength: float = 0.9
    search_turn_speed_degrees: float = 180.0
    fire_weapon_name: str = "pistol"
    fire_reaction_seconds: float = 0.18
    coordination_range: float = 220.0
    cover_search_radius_tiles: int = 6
    reload_seconds: float = 1.1
    magazine_size: int = 8
    retreat_health_threshold: float = 0.35
    fire_range: float = 260.0
    reposition_cooldown_seconds: float = 1.6
    min_hold_position_seconds: float = 1.2
    reposition_min_distance: float = 96.0
    reposition_chance: float = 0.35
    facing_angle_deg: float = 180.0
    state: str = "idle"
    sees_player: bool = False
    hurt_elapsed_seconds: float = 0.0
    corpse_elapsed_seconds: float = 0.0
    attack_cooldown_remaining: float = 0.0
    fire_reaction_remaining: float = 0.0
    reload_remaining: float = 0.0
    alarm_remaining: float = 0.0
    reposition_cooldown_remaining: float = 0.0
    position_hold_remaining: float = 0.0
    corpse_velocity_x: float = 0.0
    corpse_velocity_y: float = 0.0
    last_seen_x: float | None = None
    last_seen_y: float | None = None
    memory_remaining: float = 0.0
    strafe_sign: int = 1
    search_target_index: int = 0
    ammo_in_magazine: int = 0
    role: str = "solo"
    cover_anchor_x: float | None = None
    cover_anchor_y: float | None = None


    def __post_init__(self) -> None:
        if self.ammo_in_magazine <= 0:
            self.ammo_in_magazine = self.magazine_size

    @property
    def left(self) -> float:
        return self.x - self.width / 2.0

    @property
    def right(self) -> float:
        return self.x + self.width / 2.0

    @property
    def top(self) -> float:
        return self.y - self.height / 2.0

    @property
    def bottom(self) -> float:
        return self.y + self.height / 2.0

    @property
    def center(self) -> tuple[float, float]:
        return self.x, self.y

    @property
    def radius(self) -> float:
        return min(self.width, self.height) / 2.0

    @property
    def is_dead(self) -> bool:
        return self.state == "dead"

    @property
    def is_corpse_visible(self) -> bool:
        return self.is_dead and self.corpse_elapsed_seconds < self.corpse_lifetime_seconds

    @property
    def hurt_alpha(self) -> float:
        return max(0.0, 1.0 - self.hurt_elapsed_seconds / 0.12)

    @property
    def corpse_alpha(self) -> float:
        if self.corpse_lifetime_seconds <= 0.0:
            return 0.0
        return max(0.0, 1.0 - self.corpse_elapsed_seconds / self.corpse_lifetime_seconds)

    def move(self, dx: float, dy: float) -> None:
        self.x += dx
        self.y += dy

    def update_facing_from_point(self, target_x: float, target_y: float) -> None:
        delta_x = target_x - self.x
        delta_y = target_y - self.y
        if delta_x == 0.0 and delta_y == 0.0:
            return
        self.facing_angle_deg = math.degrees(math.atan2(delta_y, delta_x))

    def apply_damage(self, damage: float, impulse_x: float = 0.0, impulse_y: float = 0.0) -> bool:
        """Apply damage and return True if this hit killed the enemy."""

        self.health = max(0.0, self.health - damage)
        self.hurt_elapsed_seconds = 0.0
        if self.health > 0.0:
            self.state = "hurt"
            return False
        self.state = "dead"
        self.sees_player = False
        self.corpse_elapsed_seconds = 0.0
        self.attack_cooldown_remaining = 0.0
        self.corpse_velocity_x = impulse_x
        self.corpse_velocity_y = impulse_y
        return True

    def remember_player(self, x: float, y: float) -> None:
        self.last_seen_x = x
        self.last_seen_y = y
        self.memory_remaining = self.memory_seconds
        self.search_target_index = 0

    @property
    def has_memory(self) -> bool:
        return self.memory_remaining > 0.0 and self.last_seen_x is not None and self.last_seen_y is not None

    def clear_memory(self) -> None:
        self.last_seen_x = None
        self.last_seen_y = None
        self.memory_remaining = 0.0
        self.search_target_index = 0

    def can_attack(self) -> bool:
        return (
            (not self.is_dead)
            and self.attack_cooldown_remaining <= 0.0
            and self.fire_reaction_remaining <= 0.0
            and self.reload_remaining <= 0.0
            and self.ammo_in_magazine > 0
        )

    def start_attack_windup(self) -> None:
        self.fire_reaction_remaining = self.fire_reaction_seconds

    def is_attack_winding_up(self) -> bool:
        return self.fire_reaction_remaining > 0.0

    def start_attack_cooldown(self) -> None:
        self.attack_cooldown_remaining = self.attack_interval_seconds
        self.fire_reaction_remaining = 0.0

    def consume_ammo(self) -> None:
        self.ammo_in_magazine = max(0, self.ammo_in_magazine - 1)

    def needs_reload(self) -> bool:
        return self.reload_remaining <= 0.0 and self.ammo_in_magazine <= 0

    def start_reload(self) -> None:
        self.reload_remaining = self.reload_seconds
        self.fire_reaction_remaining = 0.0
        self.attack_cooldown_remaining = 0.0
        self.state = "reload"

    def broadcast_alarm(self) -> None:
        self.alarm_remaining = max(self.alarm_remaining, self.memory_seconds)

    def has_recent_alarm(self) -> bool:
        return self.alarm_remaining > 0.0

    def can_reposition(self) -> bool:
        return self.reposition_cooldown_remaining <= 0.0 and self.position_hold_remaining <= 0.0

    def commit_reposition(self) -> None:
        self.reposition_cooldown_remaining = self.reposition_cooldown_seconds
        self.position_hold_remaining = self.min_hold_position_seconds

    def hold_current_position(self) -> None:
        self.position_hold_remaining = max(self.position_hold_remaining, self.min_hold_position_seconds)

    def health_ratio(self) -> float:
        if self.max_health <= 0.0:
            return 0.0
        return self.health / self.max_health

    def update_timers(self, delta_time: float) -> None:
        self.hurt_elapsed_seconds += delta_time
        self.attack_cooldown_remaining = max(0.0, self.attack_cooldown_remaining - delta_time)
        self.fire_reaction_remaining = max(0.0, self.fire_reaction_remaining - delta_time)
        self.reload_remaining = max(0.0, self.reload_remaining - delta_time)
        self.alarm_remaining = max(0.0, self.alarm_remaining - delta_time)
        self.memory_remaining = max(0.0, self.memory_remaining - delta_time)
        self.reposition_cooldown_remaining = max(0.0, self.reposition_cooldown_remaining - delta_time)
        self.position_hold_remaining = max(0.0, self.position_hold_remaining - delta_time)
        if self.reload_remaining <= 0.0 and self.ammo_in_magazine <= 0 and not self.is_dead:
            self.ammo_in_magazine = self.magazine_size
        if self.is_dead:
            self.corpse_elapsed_seconds += delta_time
            damping = max(0.0, 1.0 - 5.0 * delta_time)
            self.x += self.corpse_velocity_x * delta_time
            self.y += self.corpse_velocity_y * delta_time
            self.corpse_velocity_x *= damping
            self.corpse_velocity_y *= damping
