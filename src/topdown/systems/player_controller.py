from __future__ import annotations

from dataclasses import dataclass
import math

from topdown.world.collision import MovementCommand


@dataclass(slots=True, frozen=True)
class InputState:
    """Directional input state independent from the input backend."""

    move_left: bool
    move_right: bool
    move_up: bool
    move_down: bool


class PlayerController:
    """Translate abstract input into normalized movement commands."""

    @staticmethod
    def build_movement(input_state: InputState, speed: float, delta_time: float) -> MovementCommand:
        """Convert directional input into frame movement.

        Args:
            input_state: Current abstract input state.
            speed: Player speed in pixels per second.
            delta_time: Frame time in seconds.

        Returns:
            Desired movement command for the current frame.
        """
        axis_x = float(input_state.move_right) - float(input_state.move_left)
        axis_y = float(input_state.move_down) - float(input_state.move_up)
        length = math.hypot(axis_x, axis_y)
        if length == 0.0:
            return MovementCommand(dx=0.0, dy=0.0)
        normalized_x = axis_x / length
        normalized_y = axis_y / length
        distance = speed * delta_time
        return MovementCommand(dx=normalized_x * distance, dy=normalized_y * distance)
