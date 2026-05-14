from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random

from topdown.core.config import GameConfig, GenerationSizeConfig
from topdown.core.types import TileKind
from topdown.world.map_model import CoverNode, RegionZone, Room, TileMap


@dataclass(slots=True, frozen=True)
class GenerationResult:
    """Procedural generation result wrapper."""

    tile_map: TileMap
    seed: int


class MapGenerator:
    """Macro-zone level generator used in step 7."""

    def __init__(self, config: GameConfig) -> None:
        self._config = config

    def generate(self, preset: GenerationSizeConfig, seed: int, name: str) -> GenerationResult:
        """Generate a validated map."""
        for attempt_index in range(self._config.generation.retry_count):
            current_seed = seed + attempt_index
            randomizer = random.Random(current_seed)
            tile_map = self._generate_once(preset, randomizer, name=name)
            if self._validate(tile_map):
                return GenerationResult(tile_map=tile_map, seed=current_seed)
        raise RuntimeError("Failed to generate a valid map after all retries.")

    def _generate_once(self, preset: GenerationSizeConfig, randomizer: random.Random, name: str) -> TileMap:
        tile_map = TileMap.create_filled(preset.width, preset.height, TileKind.WALL, name=name)
        regions = self._build_regions(preset)
        rooms: list[Room] = []
        tile_map.regions = regions

        for region in regions:
            room = Room(region.x, region.y, region.width, region.height)
            rooms.append(room)
            floor_kind = self._choose_floor(region.role, randomizer)
            tile_map.fill_rect(region.x, region.y, region.width, region.height, floor_kind)

        ordered = [
            self._find_region(regions, "player_start"),
            self._find_region(regions, "transition"),
            self._find_region(regions, "combat_alpha"),
            self._find_region(regions, "pressure"),
            self._find_region(regions, "combat_beta"),
        ]
        corridor_half_width = self._config.generation.corridor_half_width
        for region_a, region_b in zip(ordered, ordered[1:], strict=False):
            self._carve_corridor(tile_map, region_a.center, region_b.center, corridor_half_width)
        self._carve_corridor(tile_map, ordered[0].center, ordered[2].center, corridor_half_width)
        self._carve_corridor(tile_map, ordered[2].center, ordered[4].center, corridor_half_width)

        self._place_cover(tile_map, randomizer)
        tile_map.cover_nodes = self._build_cover_nodes(tile_map)
        tile_map.spawn_tile = self._find_region(regions, "player_start").center
        tile_map.enemy_spawn_tiles = self._build_enemy_spawns(tile_map, randomizer)
        tile_map.rooms = rooms
        return tile_map

    def _build_regions(self, preset: GenerationSizeConfig) -> list[RegionZone]:
        width = preset.width
        height = preset.height
        margin = 4
        left_band = max(10, width // 5)
        right_band = max(10, width // 5)
        center_x = width // 2
        center_y = height // 2
        top_y = max(margin + 3, height // 5)
        bottom_y = min(height - margin - 10, (height * 3) // 5)
        room_w = max(8, min(width // 4, preset.room_max_size + 4))
        room_h = max(8, min(height // 4, preset.room_max_size + 4))
        long_w = max(8, min(width // 5, preset.room_max_size + 3))
        long_h = max(8, min(height // 5, preset.room_max_size + 2))
        start = RegionZone("player_start", margin + 2, center_y - room_h // 2, room_w, room_h)
        transition = RegionZone("transition", center_x - long_w // 2 - 4, center_y - 4, long_w + 8, 8)
        combat_alpha = RegionZone("combat_alpha", center_x - room_w // 2, top_y, room_w + 4, room_h + 2)
        combat_beta = RegionZone("combat_beta", center_x - room_w // 2 + 2, bottom_y, room_w + 2, room_h)
        pressure = RegionZone("pressure", width - right_band - room_w - 2, center_y - room_h // 2, room_w + 2, room_h + 2)
        return [start, transition, combat_alpha, combat_beta, pressure]

    @staticmethod
    def _find_region(regions: list[RegionZone], role: str) -> RegionZone:
        for region in regions:
            if region.role == role:
                return region
        raise ValueError(f"Region with role {role} not found")

    @staticmethod
    def _choose_floor(role: str, randomizer: random.Random) -> TileKind:
        if role == "player_start":
            return TileKind.WOOD_FLOOR
        if role.startswith("combat"):
            return TileKind.TILE_FLOOR if randomizer.random() < 0.5 else TileKind.WOOD_FLOOR
        if role == "pressure":
            return TileKind.WOOD_FLOOR
        return TileKind.DIRT

    @staticmethod
    def _carve_corridor(tile_map: TileMap, start: tuple[int, int], end: tuple[int, int], corridor_half_width: int) -> None:
        x1, y1 = start
        x2, y2 = end
        for x in range(min(x1, x2), max(x1, x2) + 1):
            tile_map.fill_rect(x, y1 - corridor_half_width, 1, corridor_half_width * 2 + 1, TileKind.DIRT)
        for y in range(min(y1, y2), max(y1, y2) + 1):
            tile_map.fill_rect(x2 - corridor_half_width, y, corridor_half_width * 2 + 1, 1, TileKind.DIRT)

    def _place_cover(self, tile_map: TileMap, randomizer: random.Random) -> None:
        for region in tile_map.regions:
            if not region.role.startswith("combat") and region.role != "pressure":
                continue
            cover_candidates: list[tuple[int, int]] = []
            center_x, center_y = region.center
            cover_candidates.extend(
                [
                    (center_x - 2, center_y),
                    (center_x + 2, center_y),
                    (center_x, center_y - 2),
                    (center_x, center_y + 2),
                ]
            )
            entry_side_x = region.x + 2
            entry_side_y = center_y
            cover_candidates.extend([(entry_side_x, entry_side_y - 2), (entry_side_x, entry_side_y + 2)])
            if region.role == "pressure":
                cover_candidates.extend([(region.x + region.width - 4, center_y - 2), (region.x + region.width - 4, center_y + 2)])
            for tile_x, tile_y in cover_candidates:
                if not tile_map.in_bounds(tile_x, tile_y):
                    continue
                if tile_map.get_tile(tile_x, tile_y) is TileKind.WALL:
                    continue
                if randomizer.random() < 0.85:
                    tile_map.cover_tiles.add((tile_x, tile_y))
            self._place_split_barrier(tile_map, region)

    @staticmethod
    def _place_split_barrier(tile_map: TileMap, region: RegionZone) -> None:
        if region.role not in {"combat_alpha", "combat_beta"}:
            return
        center_x, center_y = region.center
        for offset in (-1, 0, 1):
            point = (center_x + offset, center_y)
            if tile_map.in_bounds(*point):
                tile_map.cover_tiles.add(point)


    def _build_cover_nodes(self, tile_map: TileMap) -> list[CoverNode]:
        """Create tactical cover nodes around placed cover tiles."""
        node_map: dict[tuple[int, int], CoverNode] = {}
        for cover_x, cover_y in sorted(tile_map.cover_tiles):
            region_role = tile_map.region_role_at(cover_x, cover_y)
            for offset_x, offset_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                node_x = cover_x + offset_x
                node_y = cover_y + offset_y
                if not tile_map.is_walkable(node_x, node_y):
                    continue
                if region_role == "player_start":
                    node_type = "fallback"
                elif region_role == "transition":
                    node_type = "transition"
                elif offset_x == -1:
                    node_type = "left_peek"
                elif offset_x == 1:
                    node_type = "right_peek"
                else:
                    node_type = "hold"
                key = (node_x, node_y)
                candidate = CoverNode(
                    tile_x=node_x,
                    tile_y=node_y,
                    node_type=node_type,
                    cover_tile_x=cover_x,
                    cover_tile_y=cover_y,
                    facing_dx=-offset_x,
                    facing_dy=-offset_y,
                )
                existing = node_map.get(key)
                if existing is None or self._cover_node_priority(candidate.node_type) > self._cover_node_priority(existing.node_type):
                    node_map[key] = candidate
        return sorted(node_map.values(), key=lambda node: (node.tile_y, node.tile_x, node.node_type))

    @staticmethod
    def _cover_node_priority(node_type: str) -> int:
        priorities = {
            "fallback": 5,
            "transition": 4,
            "hold": 3,
            "left_peek": 2,
            "right_peek": 2,
        }
        return priorities.get(node_type, 0)

    def _build_enemy_spawns(self, tile_map: TileMap, randomizer: random.Random) -> list[tuple[int, int]]:
        spawn = tile_map.spawn_tile
        weighted_regions = [
            self._find_region(tile_map.regions, "pressure"),
            self._find_region(tile_map.regions, "combat_beta"),
            self._find_region(tile_map.regions, "combat_alpha"),
        ]
        points: list[tuple[int, int]] = []
        for region in weighted_regions:
            cx, cy = region.center
            candidates = [
                (cx, cy),
                (cx - 2, cy - 1),
                (cx + 2, cy + 1),
                (cx - 3, cy + 2),
                (cx + 3, cy - 2),
            ]
            for candidate in candidates:
                if not tile_map.in_bounds(*candidate):
                    continue
                if not tile_map.is_walkable(*candidate):
                    continue
                distance = abs(candidate[0] - spawn[0]) + abs(candidate[1] - spawn[1])
                if distance < max(8, tile_map.width // 6):
                    continue
                if candidate not in points:
                    points.append(candidate)
            randomizer.shuffle(points)
        points.sort(key=lambda tile: abs(tile[0] - spawn[0]) + abs(tile[1] - spawn[1]), reverse=True)
        return points

    def _validate(self, tile_map: TileMap) -> bool:
        if not tile_map.rooms:
            return False
        if len(tile_map.enemy_spawn_tiles) < 3:
            return False
        open_ratio = tile_map.open_tile_ratio()
        if open_ratio < self._config.generation.min_open_ratio:
            return False
        if open_ratio > self._config.generation.max_open_ratio:
            return False
        return self._is_fully_connected(tile_map)

    @staticmethod
    def _is_fully_connected(tile_map: TileMap) -> bool:
        walkable_tiles = set(tile_map.iter_walkable_tiles())
        if tile_map.spawn_tile not in walkable_tiles:
            return False
        visited: set[tuple[int, int]] = set()
        queue: deque[tuple[int, int]] = deque([tile_map.spawn_tile])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            x, y = current
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                nxt = (x + dx, y + dy)
                if nxt in walkable_tiles and nxt not in visited:
                    queue.append(nxt)
        return visited == walkable_tiles
