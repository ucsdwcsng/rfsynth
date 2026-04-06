"""PSK atomic wrapper."""

from __future__ import annotations

from rfsynth.native.atomic.common import psk_burst
from rfsynth.native.core import Scene, Signal


class PskSignal(Signal):
    """Dispatch `generate_transmission(...)` to `common.psk_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene
        return psk_burst(self.args, rng)
