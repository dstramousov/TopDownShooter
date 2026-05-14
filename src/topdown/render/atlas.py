from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pyray as pr

from topdown.core.types import TileKind


@dataclass(slots=True)
class TextureAtlas:
    """Loads and serves project textures."""

    root_dir: Path
    tile_size: int
    _textures: dict[str, pr.Texture] = field(default_factory=dict, init=False, repr=False)

    def load(self) -> None:
        """Load required textures from disk."""
        texture_files = {
            "grass_a": self.root_dir / "assets/kenney/png/tiles/tile_01.png",
            "grass_b": self.root_dir / "assets/kenney/png/tiles/tile_02.png",
            "dirt_a": self.root_dir / "assets/kenney/png/tiles/tile_05.png",
            "dirt_b": self.root_dir / "assets/kenney/png/tiles/tile_06.png",
            "tile_floor_a": self.root_dir / "assets/kenney/png/tiles/tile_07.png",
            "tile_floor_b": self.root_dir / "assets/kenney/png/tiles/tile_08.png",
            "wood_floor_a": self.root_dir / "assets/kenney/png/tiles/tile_100.png",
            "wood_floor_b": self.root_dir / "assets/kenney/png/tiles/tile_101.png",
            "wall_center": self.root_dir / "assets/kenney/png/tiles/tile_113.png",
            "wall_vertical": self.root_dir / "assets/kenney/png/tiles/tile_111.png",
            "wall_horizontal": self.root_dir / "assets/kenney/png/tiles/tile_120.png",
            "wall_top_left": self.root_dir / "assets/kenney/png/tiles/tile_109.png",
            "wall_top_right": self.root_dir / "assets/kenney/png/tiles/tile_112.png",
            "wall_bottom_left": self.root_dir / "assets/kenney/png/tiles/tile_118.png",
            "wall_bottom_right": self.root_dir / "assets/kenney/png/tiles/tile_122.png",
            "player": self.root_dir / "assets/kenney/png/characters/survivor1/survivor1_gun.png",
        }
        for key, texture_path in texture_files.items():
            self._textures[key] = pr.load_texture(str(texture_path))

    def unload(self) -> None:
        """Release loaded textures."""
        for texture in self._textures.values():
            pr.unload_texture(texture)
        self._textures.clear()

    def get(self, key: str) -> pr.Texture:
        """Get a named texture.

        Args:
            key: Texture identifier.

        Returns:
            Loaded Pyray texture.
        """
        return self._textures[key]

    def get_floor_texture(self, tile_kind: TileKind, x: int, y: int) -> pr.Texture:
        """Select a floor texture variation based on coordinates."""
        even = (x + y) % 2 == 0
        if tile_kind is TileKind.GRASS:
            return self.get("grass_a" if even else "grass_b")
        if tile_kind is TileKind.DIRT:
            return self.get("dirt_a" if even else "dirt_b")
        if tile_kind is TileKind.WOOD_FLOOR:
            return self.get("wood_floor_a" if even else "wood_floor_b")
        return self.get("tile_floor_a" if even else "tile_floor_b")

    @property
    def keys(self) -> Iterable[str]:
        """Return texture keys for diagnostics."""
        return self._textures.keys()
