from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(slots=True)
class Bullet:
    """Mutable projectile state independent from the rendering backend."""

    x: float
    y: float
    velocity_x: float
    velocity_y: float
    radius: float
    lifetime_seconds: float
    traveled_seconds: float = 0.0
    is_alive: bool = True

    def update(self, delta_time: float) -> None:
        """Advance the projectile by the provided frame time.

        Args:
            delta_time: Frame time in seconds.
        """
        self.x += self.velocity_x * delta_time
        self.y += self.velocity_y * delta_time
        self.traveled_seconds += delta_time
        if self.traveled_seconds >= self.lifetime_seconds:
            self.is_alive = False

    @property
    def angle_deg(self) -> float:
        """Return the current projectile heading in degrees."""
        return math.degrees(math.atan2(self.velocity_y, self.velocity_x))
