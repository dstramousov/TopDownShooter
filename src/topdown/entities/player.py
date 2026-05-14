from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(slots=True)
class Player:
    """Mutable player state independent from the rendering backend."""

    x: float
    y: float
    width: float
    height: float
    speed: float
    health: float
    max_health: float
    hurt_flash_seconds: float
    facing_angle_deg: float = 0.0
    hurt_elapsed_seconds: float = 999.0
    recoil_angle_deg: float = 0.0
    recoil_distance: float = 0.0
    recoil_recovery_seconds: float = 0.0
    recoil_elapsed_seconds: float = 999.0

    @property
    def left(self) -> float:
        """Return the left edge of the hitbox."""
        return self.x - self.width / 2.0

    @property
    def right(self) -> float:
        """Return the right edge of the hitbox."""
        return self.x + self.width / 2.0

    @property
    def top(self) -> float:
        """Return the top edge of the hitbox."""
        return self.y - self.height / 2.0

    @property
    def bottom(self) -> float:
        """Return the bottom edge of the hitbox."""
        return self.y + self.height / 2.0

    @property
    def center(self) -> tuple[float, float]:
        """Return the player center in world coordinates."""
        return self.x, self.y

    @property
    def is_dead(self) -> bool:
        """Return whether the player has no remaining health."""
        return self.health <= 0.0

    @property
    def health_ratio(self) -> float:
        """Return normalized health in the range [0, 1]."""
        if self.max_health <= 0.0:
            return 0.0
        return max(0.0, min(1.0, self.health / self.max_health))

    @property
    def hurt_alpha(self) -> float:
        """Return normalized damage flash opacity."""
        if self.hurt_flash_seconds <= 0.0:
            return 0.0
        return max(0.0, 1.0 - self.hurt_elapsed_seconds / self.hurt_flash_seconds)

    @property
    def recoil_alpha(self) -> float:
        """Return normalized recoil amount for presentation."""
        if self.recoil_recovery_seconds <= 0.0:
            return 0.0
        return max(0.0, 1.0 - self.recoil_elapsed_seconds / self.recoil_recovery_seconds)

    @property
    def recoil_offset(self) -> tuple[float, float]:
        """Return current visual recoil offset in world coordinates."""
        alpha = self.recoil_alpha
        if alpha <= 0.0 or self.recoil_distance <= 0.0:
            return 0.0, 0.0
        angle_rad = math.radians(self.recoil_angle_deg)
        return -math.cos(angle_rad) * self.recoil_distance * alpha, -math.sin(angle_rad) * self.recoil_distance * alpha

    def move(self, dx: float, dy: float) -> None:
        """Apply a relative movement to the player position."""
        self.x += dx
        self.y += dy

    def set_world_position(self, x: float, y: float) -> None:
        """Assign an absolute position in world coordinates."""
        self.x = x
        self.y = y

    def update_facing_from_point(self, target_x: float, target_y: float) -> None:
        """Update the facing angle from a world-space target point.

        Args:
            target_x: Target x in world space.
            target_y: Target y in world space.
        """
        delta_x = target_x - self.x
        delta_y = target_y - self.y
        if delta_x == 0.0 and delta_y == 0.0:
            return
        self.facing_angle_deg = math.degrees(math.atan2(delta_y, delta_x))

    def apply_damage(self, damage: float) -> None:
        """Apply incoming damage and start the hurt flash."""
        if damage <= 0.0 or self.is_dead:
            return
        self.health = max(0.0, self.health - damage)
        self.hurt_elapsed_seconds = 0.0

    def apply_recoil(self, angle_deg: float, distance: float, recovery_seconds: float) -> None:
        """Apply short-lived presentation recoil to the player sprite."""
        if distance <= 0.0 or recovery_seconds <= 0.0:
            return
        self.recoil_angle_deg = angle_deg
        self.recoil_distance = distance
        self.recoil_recovery_seconds = recovery_seconds
        self.recoil_elapsed_seconds = 0.0

    def heal_to_full(self) -> None:
        """Restore the player to full health."""
        self.health = self.max_health
        self.hurt_elapsed_seconds = 999.0
        self.recoil_elapsed_seconds = 999.0

    def update_timers(self, delta_time: float) -> None:
        """Advance short-lived visual timers."""
        self.hurt_elapsed_seconds += delta_time
        self.recoil_elapsed_seconds += delta_time
