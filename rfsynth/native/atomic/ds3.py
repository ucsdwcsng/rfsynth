"""DS3 atomic wrapper over the shared spread-spectrum helper."""

from __future__ import annotations

from rfsynth.native.atomic.common import ds3_burst
from rfsynth.native.core import Scene, Signal


class Ds3Signal(Signal):
    """Dispatch `generate_transmission(...)` to `common.ds3_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene
        return ds3_burst(self.args, rng)
