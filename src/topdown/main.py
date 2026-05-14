from __future__ import annotations

import argparse
from pathlib import Path

from topdown.app.game_app import GameApp
from topdown.core.config import load_config
from topdown.core.logging_ext import configure_logging
from topdown.core.types import MapMode


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Top-down shooter step 6 viewer.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Path to the TOML configuration file.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default=None,
        choices=[member.value for member in MapMode],
        help="Map mode to load on startup.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for procedural generation modes.",
    )
    return parser


def main() -> None:
    """Run the application from the command line."""
    parser = build_argument_parser()
    args = parser.parse_args()
    config = load_config(args.config)
    logger = configure_logging(config.logging, config.project_root)

    if args.mode is not None:
        config = config.__class__(
            project_root=config.project_root,
            app=config.app.__class__(
                name=config.app.name,
                default_map_mode=args.mode,
                default_seed=args.seed if args.seed is not None else config.app.default_seed,
            ),
            window=config.window,
            world=config.world,
            player=config.player,
            weapons=config.weapons,
            enemies=config.enemies,
            generation=config.generation,
            render=config.render,
            effects=config.effects,
            logging=config.logging,
            i18n=config.i18n,
        )
    elif args.seed is not None:
        config = config.__class__(
            project_root=config.project_root,
            app=config.app.__class__(
                name=config.app.name,
                default_map_mode=config.app.default_map_mode,
                default_seed=args.seed,
            ),
            window=config.window,
            world=config.world,
            player=config.player,
            weapons=config.weapons,
            enemies=config.enemies,
            generation=config.generation,
            render=config.render,
            effects=config.effects,
            logging=config.logging,
            i18n=config.i18n,
        )

    logger.info("Loaded configuration from %s", args.config.resolve())
    GameApp(config=config, logger=logger).run()


if __name__ == "__main__":
    main()
