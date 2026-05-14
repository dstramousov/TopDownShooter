from __future__ import annotations

from pathlib import Path

from topdown.core.config import load_config
from topdown.core.types import MapMode, TileKind
from topdown.world.generation import MapGenerator
from topdown.world.presets import get_generation_preset


def test_procedural_generator_produces_connected_medium_map() -> None:
    config = load_config(Path(__file__).resolve().parents[1] / "config.toml")
    generator = MapGenerator(config)
    preset = get_generation_preset(config, MapMode.GENERATED_MEDIUM)

    result = generator.generate(preset=preset, seed=42, name="test_medium")

    assert result.tile_map.width == preset.width
    assert result.tile_map.height == preset.height
    assert result.tile_map.rooms
    assert result.tile_map.regions
    assert result.tile_map.enemy_spawn_tiles
    assert result.tile_map.get_tile(*result.tile_map.spawn_tile) != TileKind.WALL
    assert config.generation.min_open_ratio <= result.tile_map.open_tile_ratio() <= config.generation.max_open_ratio


def test_generated_map_has_tactical_covers_outside_start_room() -> None:
    config = load_config(Path(__file__).resolve().parents[1] / "config.toml")
    generator = MapGenerator(config)
    preset = get_generation_preset(config, MapMode.GENERATED_SMALL)

    result = generator.generate(preset=preset, seed=7, name="test_small")

    assert len(result.tile_map.cover_tiles) >= 6
    start_x, start_y = result.tile_map.spawn_tile
    assert all(abs(x - start_x) + abs(y - start_y) >= 3 for x, y in result.tile_map.enemy_spawn_tiles)
