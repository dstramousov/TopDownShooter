from __future__ import annotations

from topdown.world.camera import CameraController, CameraState


def test_camera_clamps_to_world_bounds() -> None:
    controller = CameraController(viewport_width=300, viewport_height=200, world_tile_size=64)
    state = CameraState()

    controller.follow(
        state=state,
        target_x=5000.0,
        target_y=5000.0,
        map_width_tiles=10,
        map_height_tiles=8,
    )

    assert state.x == 340.0
    assert state.y == 312.0
