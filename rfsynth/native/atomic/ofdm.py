"""Generic OFDM atomic wrapper."""

from __future__ import annotations

from rfsynth.native.atomic.common import ofdm_burst
from rfsynth.native.core import Scene, Signal


class OfdmSignal(Signal):
    """Dispatch `generate_transmission(...)` to `common.ofdm_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene
        return ofdm_burst(self.args, rng)
