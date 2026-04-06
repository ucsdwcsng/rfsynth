"""GMSK atomic wrapper over the shared FSK-family builder."""

from __future__ import annotations

from rfsynth.native.atomic.common import fsk_like_burst
from rfsynth.native.core import Scene, Signal


class GmskSignal(Signal):
    """Dispatch `generate_transmission(...)` to `common.fsk_like_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene
        return fsk_like_burst(
            self.args,
            rng,
            continuous=True,
            gaussian_bt=float(self.args.get("bandwidthTimeProduct", 0.35)),
            modulation_index=0.5,
            bandwidth_hz=float(self.args.get("bandwidth_Hz", 1.5 * float(self.args.get("transmissionRate_Hz", 250e3)))),
            modulation="gmsk",
        )
