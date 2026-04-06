"""FSK atomic wrapper over the shared FSK-family builder."""

from __future__ import annotations

from rfsynth.native.atomic.common import fsk_like_burst
from rfsynth.native.core import Scene, Signal


class FskSignal(Signal):
    """Dispatch `generate_transmission(...)` to `common.fsk_like_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene
        mod_order = int(self.args.get("modOrder", 2))
        symbol_rate = float(self.args.get("transmissionRate_Hz", 250e3))
        bandwidth = float(self.args.get("bandwidth_Hz", symbol_rate * (1 + 2 * float(self.args.get("freqDev", 0.25)) * (mod_order - 1))))
        modulation = {2: "fsk2", 4: "fsk4", 8: "fsk8", 16: "fsk16", 32: "fsk32", 64: "fsk64", 128: "fsk128"}.get(mod_order, "fsk2")
        return fsk_like_burst(self.args, rng, continuous=False, bandwidth_hz=bandwidth, modulation=modulation)
