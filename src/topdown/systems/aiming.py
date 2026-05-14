from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(slots=True, frozen=True)
class AimState:
    """World-space aiming information derived from the cursor."""

    target_x: float
    target_y: float
    angle_deg: float
    direction_x: float
    direction_y: float


class AimController:
    """Convert world-space cursor positions into aiming data."""

    @staticmethod
    def build(player_x: float, player_y: float, target_x: float, target_y: float) -> AimState:
        """Build normalized aiming information.

        Args:
            player_x: Player center x in world space.
            player_y: Player center y in world space.
            target_x: Cursor x in world space.
            target_y: Cursor y in world space.

        Returns:
            Immutable aiming state.
        """
        delta_x = target_x - player_x
        delta_y = target_y - player_y
        length = math.hypot(delta_x, delta_y)
        if length == 0.0:
            return AimState(
                target_x=target_x,
                target_y=target_y,
                angle_deg=0.0,
                direction_x=1.0,
                direction_y=0.0,
            )
        direction_x = delta_x / length
        direction_y = delta_y / length
        angle_deg = math.degrees(math.atan2(direction_y, direction_x))
        return AimState(
            target_x=target_x,
            target_y=target_y,
            angle_deg=angle_deg,
            direction_x=direction_x,
            direction_y=direction_y,
        )
