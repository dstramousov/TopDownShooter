from __future__ import annotations

from topdown.core.types import TileKind
from topdown.world.map_model import Room, TileMap


def build_debug_static_map() -> TileMap:
    """Build a handcrafted house-and-yard test map.

    Returns:
        Static map suitable for early visual debugging.
    """
    tile_map = TileMap.create_filled(40, 28, TileKind.GRASS, name="debug_static")

    # Outer play area border.
    tile_map.fill_rect(0, 0, tile_map.width, 1, TileKind.WALL)
    tile_map.fill_rect(0, tile_map.height - 1, tile_map.width, 1, TileKind.WALL)
    tile_map.fill_rect(0, 0, 1, tile_map.height, TileKind.WALL)
    tile_map.fill_rect(tile_map.width - 1, 0, 1, tile_map.height, TileKind.WALL)

    # Dirt yard path.
    tile_map.fill_rect(3, 18, 10, 5, TileKind.DIRT)
    tile_map.fill_rect(13, 20, 7, 3, TileKind.DIRT)

    # Main house shell.
    house_x = 10
    house_y = 5
    house_w = 18
    house_h = 13
    tile_map.fill_rect(house_x, house_y, house_w, house_h, TileKind.WALL)
    tile_map.fill_rect(house_x + 1, house_y + 1, house_w - 2, house_h - 2, TileKind.WOOD_FLOOR)

    # Kitchen / utility room with tiled floor.
    tile_map.fill_rect(11, 6, 5, 5, TileKind.TILE_FLOOR)
    tile_map.fill_rect(16, 6, 1, 11, TileKind.WALL)
    tile_map.fill_rect(17, 10, 10, 1, TileKind.WALL)

    # Bedroom and storage partitions.
    tile_map.fill_rect(21, 6, 1, 4, TileKind.WALL)
    tile_map.fill_rect(22, 9, 5, 1, TileKind.WALL)

    # Doors / openings.
    for point in [(16, 8), (16, 13), (21, 8), (24, 10), (18, 17), (19, 17)]:
        tile_map.set_tile(point[0], point[1], TileKind.WOOD_FLOOR)

    # Spawn and room metadata.
    tile_map.spawn_tile = (8, 20)
    tile_map.rooms = [
        Room(11, 6, 5, 5),
        Room(17, 6, 4, 4),
        Room(22, 6, 5, 4),
        Room(17, 11, 10, 6),
    ]
    return tile_map
