"""Tone atomic wrapper.

Call path:
`scene.build_signal(...) -> create_signal("Sine") -> SineSignal.generate_transmission()`
`-> common.sine_burst(args)`.
"""

from __future__ import annotations

from rfsynth.native.atomic.common import sine_burst
from rfsynth.native.core import Scene, Signal


class SineSignal(Signal):
    """Thin wrapper that dispatches to `common.sine_burst(...)`."""

    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return sine_burst(self.args)
