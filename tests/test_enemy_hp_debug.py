from topdown.entities.enemy import Enemy


def build_enemy(health: float = 40.0) -> Enemy:
    return Enemy(
        x=64.0,
        y=64.0,
        width=32.0,
        height=32.0,
        speed=100.0,
        health=health,
        max_health=health,
        vision_distance=300.0,
        vision_fov_degrees=75.0,
        stop_distance=80.0,
        attack_damage=10.0,
        attack_interval_seconds=1.0,
        attack_range=48.0,
        corpse_lifetime_seconds=10.0,
    )


def test_enemy_damage_is_not_always_lethal() -> None:
    enemy = build_enemy()

    killed = enemy.apply_damage(14.0)

    assert killed is False
    assert enemy.is_dead is False
    assert enemy.health == 26.0


def test_enemy_dies_when_health_reaches_zero() -> None:
    enemy = build_enemy()

    killed = enemy.apply_damage(40.0, impulse_x=10.0, impulse_y=5.0)

    assert killed is True
    assert enemy.is_dead is True
    assert enemy.health == 0.0
    assert enemy.corpse_velocity_x == 10.0
