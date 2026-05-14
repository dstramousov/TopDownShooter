from __future__ import annotations

from pathlib import Path

from topdown.core.config import load_config


def test_weapon_definitions_are_loaded_from_toml() -> None:
    config = load_config(Path(__file__).resolve().parents[1] / "config.toml")

    assert config.player.starting_weapon == "smg"
    assert {"shotgun", "pistol", "smg"}.issubset(config.weapons.keys())
    assert config.weapons["smg"].fire_interval_seconds < config.weapons["pistol"].fire_interval_seconds
    assert config.weapons["shotgun"].tracer_every_n_shot == 3
    assert config.weapons["shotgun"].bullet_hole_diameter > 0.0
    assert config.effects.impact_debris.enabled is True
    assert 0.1 <= config.effects.impact_debris.intensity <= 1.0
    assert config.weapons["shotgun"].damage > 0.0
    assert config.enemies["grunt"].vision_fov_degrees > 0.0
    assert config.player.health > 0.0
    assert config.enemies["grunt"].attack_damage > 0.0
    assert config.enemies["grunt"].reposition_cooldown_seconds > 0.0
    assert config.enemies["grunt"].min_hold_position_seconds > 0.0
