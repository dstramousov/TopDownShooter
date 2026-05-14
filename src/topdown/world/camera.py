from __future__ import annotations

from dataclasses import dataclass
import math
import random


@dataclass(slots=True)
class CameraState:
    """Simple world camera represented by a top-left pixel offset."""

    x: float = 0.0
    y: float = 0.0
    shake_x: float = 0.0
    shake_y: float = 0.0
    shake_magnitude: float = 0.0
    shake_duration_seconds: float = 0.0
    shake_elapsed_seconds: float = 999.0


class CameraController:
    """Compute a clamped camera offset that follows a target."""

    def __init__(self, viewport_width: int, viewport_height: int, world_tile_size: int, rng_seed: int = 4242) -> None:
        self._viewport_width = viewport_width
        self._viewport_height = viewport_height
        self._world_tile_size = world_tile_size
        self._random = random.Random(rng_seed)

    def follow(
        self,
        state: CameraState,
        target_x: float,
        target_y: float,
        map_width_tiles: int,
        map_height_tiles: int,
    ) -> None:
        """Place the camera so that the target stays near the viewport center."""
        world_width = map_width_tiles * self._world_tile_size
        world_height = map_height_tiles * self._world_tile_size

        desired_x = target_x - self._viewport_width / 2.0
        desired_y = target_y - self._viewport_height / 2.0

        max_x = max(world_width - self._viewport_width, 0)
        max_y = max(world_height - self._viewport_height, 0)

        state.x = min(max(desired_x, 0.0), float(max_x))
        state.y = min(max(desired_y, 0.0), float(max_y))

    def add_shake(self, state: CameraState, magnitude: float, duration_seconds: float) -> None:
        """Trigger a short screen shake impulse."""
        if magnitude <= 0.0 or duration_seconds <= 0.0:
            return
        state.shake_magnitude = max(state.shake_magnitude, magnitude)
        state.shake_duration_seconds = max(state.shake_duration_seconds, duration_seconds)
        state.shake_elapsed_seconds = 0.0

    def update(self, state: CameraState, delta_time: float) -> None:
        """Advance transient camera feedback such as screen shake."""
        if state.shake_elapsed_seconds >= state.shake_duration_seconds or state.shake_duration_seconds <= 0.0:
            state.shake_x = 0.0
            state.shake_y = 0.0
            state.shake_elapsed_seconds = 999.0
            return
        state.shake_elapsed_seconds += delta_time
        alpha = max(0.0, 1.0 - state.shake_elapsed_seconds / state.shake_duration_seconds)
        magnitude = state.shake_magnitude * alpha
        angle = self._random.uniform(0.0, math.tau)
        state.shake_x = math.cos(angle) * magnitude
        state.shake_y = math.sin(angle) * magnitude
