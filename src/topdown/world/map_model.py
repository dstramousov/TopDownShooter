from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
from numpy.typing import NDArray

from topdown.core.types import TileKind


@dataclass(slots=True, frozen=True)
class Room:
    """Rectangular room in tile coordinates."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        """Return the integer center point of the room."""
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass(slots=True, frozen=True)
class RegionZone:
    """Semantic macro-zone used by the procedural generator."""

    role: str
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        """Return the integer center point of the zone."""
        return (self.x + self.width // 2, self.y + self.height // 2)



@dataclass(slots=True, frozen=True)
class CoverNode:
    """Tactical position adjacent to a solid cover tile."""

    tile_x: int
    tile_y: int
    node_type: str
    cover_tile_x: int
    cover_tile_y: int
    facing_dx: int
    facing_dy: int


@dataclass(slots=True)
class TileMap:
    """Logical world map independent from the rendering backend."""

    width: int
    height: int
    tiles: NDArray[np.int8] = field(repr=False)
    spawn_tile: tuple[int, int]
    rooms: list[Room] = field(default_factory=list)
    regions: list[RegionZone] = field(default_factory=list)
    cover_tiles: set[tuple[int, int]] = field(default_factory=set)
    enemy_spawn_tiles: list[tuple[int, int]] = field(default_factory=list)
    cover_nodes: list[CoverNode] = field(default_factory=list)
    name: str = "unnamed"

    @classmethod
    def create_filled(
        cls,
        width: int,
        height: int,
        fill_value: TileKind,
        name: str,
    ) -> "TileMap":
        """Create a filled tile map.

        Args:
            width: Map width in tiles.
            height: Map height in tiles.
            fill_value: Initial tile kind.
            name: Human-readable map name.

        Returns:
            Initialized tile map.
        """
        tiles = np.full((height, width), int(fill_value), dtype=np.int8)
        return cls(width=width, height=height, tiles=tiles, spawn_tile=(1, 1), name=name)

    def in_bounds(self, x: int, y: int) -> bool:
        """Check whether tile coordinates are valid."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile(self, x: int, y: int) -> TileKind:
        """Read a tile value."""
        return TileKind(int(self.tiles[y, x]))

    def set_tile(self, x: int, y: int, tile_kind: TileKind) -> None:
        """Write a tile value if the position is valid."""
        if self.in_bounds(x, y):
            self.tiles[y, x] = int(tile_kind)

    def fill_rect(self, x: int, y: int, width: int, height: int, tile_kind: TileKind) -> None:
        """Fill an axis-aligned rectangle."""
        x_end = max(0, min(self.width, x + width))
        y_end = max(0, min(self.height, y + height))
        x_start = max(0, x)
        y_start = max(0, y)
        self.tiles[y_start:y_end, x_start:x_end] = int(tile_kind)

    def count_tiles(self, tile_kind: TileKind) -> int:
        """Count tiles of a specific type."""
        return int(np.count_nonzero(self.tiles == int(tile_kind)))

    def open_tile_ratio(self) -> float:
        """Compute the ratio of walkable tiles."""
        walkable = np.isin(
            self.tiles,
            np.array(
                [
                    int(TileKind.GRASS),
                    int(TileKind.DIRT),
                    int(TileKind.WOOD_FLOOR),
                    int(TileKind.TILE_FLOOR),
                ],
                dtype=np.int8,
            ),
        )
        open_tiles = float(np.count_nonzero(walkable)) - float(len(self.cover_tiles))
        return max(0.0, open_tiles / self.tiles.size)

    def is_walkable(self, x: int, y: int) -> bool:
        """Check whether the requested tile can be traversed."""
        if not self.in_bounds(x, y):
            return False
        if (x, y) in self.cover_tiles:
            return False
        return self.get_tile(x, y) in {
            TileKind.GRASS,
            TileKind.DIRT,
            TileKind.WOOD_FLOOR,
            TileKind.TILE_FLOOR,
        }

    def is_cover(self, x: int, y: int) -> bool:
        """Return whether a tile is occupied by tactical cover."""
        return (x, y) in self.cover_tiles

    def region_role_at(self, x: int, y: int) -> str | None:
        """Return the semantic region role that contains the tile."""
        for region in self.regions:
            if region.x <= x < region.x + region.width and region.y <= y < region.y + region.height:
                return region.role
        return None

    def cover_node_at(self, x: int, y: int) -> CoverNode | None:
        """Return the first cover node occupying the requested tile."""
        for node in self.cover_nodes:
            if node.tile_x == x and node.tile_y == y:
                return node
        return None

    def iter_walkable_tiles(self) -> Iterable[tuple[int, int]]:
        """Yield walkable tile coordinates."""
        for y in range(self.height):
            for x in range(self.width):
                if self.is_walkable(x, y):
                    yield x, y
