from pathlib import Path

from topdown.core.config import load_config
from topdown.core.types import MapMode
from topdown.world.generation import MapGenerator
from topdown.world.presets import get_generation_preset


def test_generated_map_has_cover_nodes() -> None:
    config = load_config(Path(__file__).resolve().parents[1] / "config.toml")
    generator = MapGenerator(config)
    result = generator.generate(get_generation_preset(config, MapMode.GENERATED_MEDIUM), seed=42, name="test")
    assert result.tile_map.cover_nodes
    assert any(node.node_type in {"hold", "left_peek", "right_peek"} for node in result.tile_map.cover_nodes)


def test_cover_nodes_stand_on_walkable_tiles() -> None:
    config = load_config(Path(__file__).resolve().parents[1] / "config.toml")
    generator = MapGenerator(config)
    result = generator.generate(get_generation_preset(config, MapMode.GENERATED_SMALL), seed=7, name="test")
    for node in result.tile_map.cover_nodes:
        assert result.tile_map.is_walkable(node.tile_x, node.tile_y)
        assert result.tile_map.is_cover(node.cover_tile_x, node.cover_tile_y)
