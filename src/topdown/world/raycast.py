from __future__ import annotations

from dataclasses import dataclass
import math

from topdown.core.types import TileKind
from topdown.world.map_model import TileMap


@dataclass(slots=True, frozen=True)
class RaycastHit:
    """Result of a raycast against the logical tile map."""

    hit: bool
    x: float
    y: float
    distance: float
    tile_x: int
    tile_y: int
    surface_kind: TileKind


class RaycastResolver:
    """Resolve hitscan shots against a tile map."""

    def __init__(self, tile_size: int, step_size: float = 6.0) -> None:
        self._tile_size = tile_size
        self._step_size = step_size

    def cast(
        self,
        tile_map: TileMap,
        origin_x: float,
        origin_y: float,
        direction_x: float,
        direction_y: float,
        max_distance: float,
    ) -> RaycastHit:
        """Cast a ray until it hits a non-walkable tile or reaches max distance."""
        if direction_x == 0.0 and direction_y == 0.0:
            tile_x = int(origin_x // self._tile_size)
            tile_y = int(origin_y // self._tile_size)
            return RaycastHit(False, origin_x, origin_y, 0.0, tile_x, tile_y, TileKind.VOID)

        distance = 0.0
        current_x = origin_x
        current_y = origin_y
        while distance < max_distance:
            current_x += direction_x * self._step_size
            current_y += direction_y * self._step_size
            distance += self._step_size
            tile_x = int(current_x // self._tile_size)
            tile_y = int(current_y // self._tile_size)
            if not tile_map.in_bounds(tile_x, tile_y):
                clamped_distance = min(distance, max_distance)
                return RaycastHit(True, current_x, current_y, clamped_distance, tile_x, tile_y, TileKind.VOID)
            surface = tile_map.get_tile(tile_x, tile_y)
            if not tile_map.is_walkable(tile_x, tile_y):
                return RaycastHit(True, current_x, current_y, min(distance, max_distance), tile_x, tile_y, surface)

        final_x = origin_x + direction_x * max_distance
        final_y = origin_y + direction_y * max_distance
        tile_x = int(final_x // self._tile_size)
        tile_y = int(final_y // self._tile_size)
        surface = tile_map.get_tile(tile_x, tile_y) if tile_map.in_bounds(tile_x, tile_y) else TileKind.VOID
        return RaycastHit(False, final_x, final_y, max_distance, tile_x, tile_y, surface)

    @staticmethod
    def build_partial_segment(
        origin_x: float,
        origin_y: float,
        hit_x: float,
        hit_y: float,
        min_fraction: float,
        max_fraction: float,
        random_value: float,
    ) -> tuple[float, float]:
        """Return an end-point for a shortened tracer segment."""
        clamped_min = max(0.0, min(1.0, min_fraction))
        clamped_max = max(clamped_min, min(1.0, max_fraction))
        fraction = clamped_min + (clamped_max - clamped_min) * random_value
        return (
            origin_x + (hit_x - origin_x) * fraction,
            origin_y + (hit_y - origin_y) * fraction,
        )
