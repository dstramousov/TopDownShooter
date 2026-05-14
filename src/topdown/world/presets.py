from __future__ import annotations

from topdown.core.config import GameConfig, GenerationSizeConfig
from topdown.core.types import MapMode


def get_generation_preset(config: GameConfig, map_mode: MapMode) -> GenerationSizeConfig:
    """Resolve generation preset for the requested map mode.

    Args:
        config: Game configuration.
        map_mode: Selected map mode.

    Returns:
        Generation preset.

    Raises:
        ValueError: If the map mode is not procedural.
    """
    if map_mode is MapMode.GENERATED_SMALL:
        return config.generation.small
    if map_mode is MapMode.GENERATED_MEDIUM:
        return config.generation.medium
    if map_mode is MapMode.GENERATED_LARGE:
        return config.generation.large
    raise ValueError(f"Map mode {map_mode!s} does not have a generation preset.")
