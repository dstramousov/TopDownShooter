from __future__ import annotations

from enum import IntEnum, StrEnum


class TileKind(IntEnum):
    """Logical tile categories used by the world model."""

    VOID = 0
    GRASS = 1
    DIRT = 2
    WOOD_FLOOR = 3
    TILE_FLOOR = 4
    WALL = 5


class MapMode(StrEnum):
    """Supported map sources for the first iteration."""

    DEBUG_STATIC = "debug_static"
    GENERATED_SMALL = "generated_small"
    GENERATED_MEDIUM = "generated_medium"
    GENERATED_LARGE = "generated_large"


class LanguageCode(StrEnum):
    """Supported UI language identifiers."""

    EN = "en"
    UA = "ua"
