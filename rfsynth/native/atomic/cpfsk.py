from __future__ import annotations

from rfsynth.native.atomic.common import fsk_like_burst
from rfsynth.native.core import Scene, Signal


class CpfskSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene
        mod_order = int(self.args.get("modOrder", 2))
        modulation = {2: "cpfsk2", 4: "cpfsk4", 8: "cpfsk8", 16: "cpfsk16", 32: "cpfsk32", 64: "cpfsk64"}.get(mod_order, "cpfsk")
        return fsk_like_burst(
            self.args,
            rng,
            continuous=True,
            modulation_index=float(self.args.get("modulationIndex", 0.5)),
            bandwidth_hz=float(self.args.get("bandwidth_Hz", 2 * float(self.args.get("transmissionRate_Hz", 250e3)))),
            modulation=modulation,
        )
