from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

from topdown.entities.player import Player
from topdown.world.map_model import TileMap


class RectBody(Protocol):
    """Minimal movable body used by the collision resolver."""

    x: float
    y: float
    width: float
    height: float


@dataclass(slots=True, frozen=True)
class MovementCommand:
    """Desired movement in world space for a single frame."""

    dx: float
    dy: float


class CollisionResolver:
    """Resolve movement against an axis-aligned tile grid."""

    def __init__(self, tile_size: int) -> None:
        self._tile_size = tile_size

    def move_player(self, player: Player, command: MovementCommand, tile_map: TileMap) -> None:
        """Backward-compatible player movement wrapper."""
        self.move_actor(player, command, tile_map)

    def move_actor(self, actor: RectBody, command: MovementCommand, tile_map: TileMap) -> None:
        """Move any rectangle body while preventing wall penetration."""
        if command.dx != 0.0:
            target_x = actor.x + command.dx
            if self._is_rect_walkable(tile_map=tile_map, center_x=target_x, center_y=actor.y, width=actor.width, height=actor.height):
                actor.x = target_x

        if command.dy != 0.0:
            target_y = actor.y + command.dy
            if self._is_rect_walkable(tile_map=tile_map, center_x=actor.x, center_y=target_y, width=actor.width, height=actor.height):
                actor.y = target_y

    def _is_rect_walkable(self, tile_map: TileMap, center_x: float, center_y: float, width: float, height: float) -> bool:
        epsilon = 0.001
        left = center_x - width / 2.0 + epsilon
        right = center_x + width / 2.0 - epsilon
        top = center_y - height / 2.0 + epsilon
        bottom = center_y + height / 2.0 - epsilon

        tile_left = int(math.floor(left / self._tile_size))
        tile_right = int(math.floor(right / self._tile_size))
        tile_top = int(math.floor(top / self._tile_size))
        tile_bottom = int(math.floor(bottom / self._tile_size))

        for tile_y in range(tile_top, tile_bottom + 1):
            for tile_x in range(tile_left, tile_right + 1):
                if not tile_map.is_walkable(tile_x, tile_y):
                    return False
        return True
