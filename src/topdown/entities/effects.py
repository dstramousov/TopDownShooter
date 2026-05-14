from __future__ import annotations

from dataclasses import dataclass

from topdown.core.types import TileKind


@dataclass(slots=True)
class TracerEffect:
    """Short-lived visual line hint for a subset of shots."""

    start_x: float
    start_y: float
    end_x: float
    end_y: float
    width: float
    core_width: float
    lifetime_seconds: float
    elapsed_seconds: float = 0.0

    @property
    def is_alive(self) -> bool:
        """Return whether the tracer should still be rendered."""
        return self.elapsed_seconds < self.lifetime_seconds

    @property
    def alpha(self) -> float:
        """Return normalized remaining opacity."""
        if self.lifetime_seconds <= 0.0:
            return 0.0
        remaining = max(0.0, self.lifetime_seconds - self.elapsed_seconds)
        return remaining / self.lifetime_seconds

    def update(self, delta_time: float) -> None:
        """Advance the tracer lifetime."""
        self.elapsed_seconds += delta_time


@dataclass(slots=True)
class ImpactMark:
    """Short-lived world-space impact marker for environment hits."""

    x: float
    y: float
    surface_kind: TileKind
    angle_deg: float
    size: float
    hole_diameter: float
    lifetime_seconds: float
    elapsed_seconds: float = 0.0

    @property
    def is_alive(self) -> bool:
        """Return whether the impact marker should still be rendered."""
        return self.elapsed_seconds < self.lifetime_seconds

    @property
    def alpha(self) -> float:
        """Return normalized remaining opacity."""
        if self.lifetime_seconds <= 0.0:
            return 0.0
        remaining = max(0.0, self.lifetime_seconds - self.elapsed_seconds)
        return remaining / self.lifetime_seconds

    def update(self, delta_time: float) -> None:
        """Advance the impact lifetime."""
        self.elapsed_seconds += delta_time


@dataclass(slots=True)
class ImpactDebrisParticle:
    """Tiny debris shard emitted from an environment hit."""

    x: float
    y: float
    velocity_x: float
    velocity_y: float
    size: float
    angle_deg: float
    surface_kind: TileKind
    lifetime_seconds: float
    drag: float
    elapsed_seconds: float = 0.0

    @property
    def is_alive(self) -> bool:
        """Return whether the particle should still be rendered."""
        return self.elapsed_seconds < self.lifetime_seconds

    @property
    def alpha(self) -> float:
        """Return normalized remaining opacity."""
        if self.lifetime_seconds <= 0.0:
            return 0.0
        remaining = max(0.0, self.lifetime_seconds - self.elapsed_seconds)
        return remaining / self.lifetime_seconds

    def update(self, delta_time: float) -> None:
        """Advance the particle simulation."""
        self.elapsed_seconds += delta_time
        damping = max(0.0, 1.0 - self.drag * delta_time)
        self.x += self.velocity_x * delta_time
        self.y += self.velocity_y * delta_time
        self.velocity_x *= damping
        self.velocity_y *= damping


@dataclass(slots=True)
class BloodParticle:
    """Short-lived blood burst particle for lethal enemy hits."""

    x: float
    y: float
    velocity_x: float
    velocity_y: float
    size: float
    lifetime_seconds: float
    elapsed_seconds: float = 0.0

    @property
    def is_alive(self) -> bool:
        return self.elapsed_seconds < self.lifetime_seconds

    @property
    def alpha(self) -> float:
        if self.lifetime_seconds <= 0.0:
            return 0.0
        remaining = max(0.0, self.lifetime_seconds - self.elapsed_seconds)
        return remaining / self.lifetime_seconds

    def update(self, delta_time: float) -> None:
        self.elapsed_seconds += delta_time
        damping = max(0.0, 1.0 - 3.8 * delta_time)
        self.x += self.velocity_x * delta_time
        self.y += self.velocity_y * delta_time
        self.velocity_x *= damping
        self.velocity_y *= damping


@dataclass(slots=True)
class BloodPool:
    """Persistent blood pool that grows slightly after a lethal hit."""

    x: float
    y: float
    size: float
    growth_seconds: float
    elapsed_seconds: float = 0.0

    @property
    def is_alive(self) -> bool:
        return True

    @property
    def growth_alpha(self) -> float:
        if self.growth_seconds <= 0.0:
            return 1.0
        return min(1.0, self.elapsed_seconds / self.growth_seconds)

    def update(self, delta_time: float) -> None:
        self.elapsed_seconds += delta_time


@dataclass(slots=True)
class BloodDecal:
    """Blood stain applied to walls behind a lethal hit."""

    x: float
    y: float
    angle_deg: float
    size: float
    lifetime_seconds: float
    elapsed_seconds: float = 0.0

    @property
    def is_alive(self) -> bool:
        return self.elapsed_seconds < self.lifetime_seconds

    @property
    def alpha(self) -> float:
        if self.lifetime_seconds <= 0.0:
            return 0.0
        remaining = max(0.0, self.lifetime_seconds - self.elapsed_seconds)
        return remaining / self.lifetime_seconds

    def update(self, delta_time: float) -> None:
        self.elapsed_seconds += delta_time


@dataclass(slots=True)
class MuzzleFlashEffect:
    """Short-lived oversized muzzle flash emitted from the weapon barrel."""

    x: float
    y: float
    angle_deg: float
    size: float
    lifetime_seconds: float
    variant: int = 0
    elapsed_seconds: float = 0.0

    @property
    def is_alive(self) -> bool:
        """Return whether the muzzle flash should still be rendered."""
        return self.elapsed_seconds < self.lifetime_seconds

    @property
    def alpha(self) -> float:
        """Return normalized remaining opacity."""
        if self.lifetime_seconds <= 0.0:
            return 0.0
        remaining = max(0.0, self.lifetime_seconds - self.elapsed_seconds)
        return remaining / self.lifetime_seconds

    def update(self, delta_time: float) -> None:
        """Advance the flash lifetime."""
        self.elapsed_seconds += delta_time


@dataclass(slots=True)
class MuzzleSmokeParticle:
    """Short-lived smoke particle emitted from the weapon barrel."""

    x: float
    y: float
    velocity_x: float
    velocity_y: float
    size: float
    lifetime_seconds: float
    elapsed_seconds: float = 0.0

    @property
    def is_alive(self) -> bool:
        """Return whether the smoke particle should still be rendered."""
        return self.elapsed_seconds < self.lifetime_seconds

    @property
    def alpha(self) -> float:
        """Return normalized remaining opacity."""
        if self.lifetime_seconds <= 0.0:
            return 0.0
        remaining = max(0.0, self.lifetime_seconds - self.elapsed_seconds)
        return remaining / self.lifetime_seconds

    def update(self, delta_time: float) -> None:
        """Advance the smoke particle simulation."""
        self.elapsed_seconds += delta_time
        damping = max(0.0, 1.0 - 2.8 * delta_time)
        self.x += self.velocity_x * delta_time
        self.y += self.velocity_y * delta_time
        self.velocity_x *= damping
        self.velocity_y *= damping


@dataclass(slots=True)
class ShellCasing:
    """Large arcade-style shell casing ejected from the weapon."""

    x: float
    y: float
    velocity_x: float
    velocity_y: float
    angle_deg: float
    angular_velocity_deg: float
    size: float
    lifetime_seconds: float
    bounce_damping: float
    max_bounces: int
    elapsed_seconds: float = 0.0
    bounce_count: int = 0

    @property
    def is_alive(self) -> bool:
        """Return whether the shell casing should still be rendered."""
        return self.elapsed_seconds < self.lifetime_seconds

    @property
    def alpha(self) -> float:
        """Return normalized remaining opacity."""
        if self.lifetime_seconds <= 0.0:
            return 0.0
        remaining = max(0.0, self.lifetime_seconds - self.elapsed_seconds)
        return remaining / self.lifetime_seconds

    def update(self, delta_time: float) -> None:
        """Advance shell casing physics."""
        self.elapsed_seconds += delta_time
        damping = max(0.0, 1.0 - 1.9 * delta_time)
        self.x += self.velocity_x * delta_time
        self.y += self.velocity_y * delta_time
        self.velocity_x *= damping
        self.velocity_y *= damping
        self.angular_velocity_deg *= max(0.0, 1.0 - 2.5 * delta_time)
        self.angle_deg += self.angular_velocity_deg * delta_time
