from __future__ import annotations

from rfsynth.native.atomic.common import noise_burst
from rfsynth.native.core import Scene, Signal


class WidebandThermalWgnSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        return noise_burst(
            self.args,
            total_time_s=scene.generation.total_time_s,
            rx_sample_rate_hz=scene.rx.sample_rate_hz,
            rng=rng,
        )
