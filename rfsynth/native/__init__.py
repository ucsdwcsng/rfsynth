"""Convenience exports for the Python-native synthetic path.

The implementation lives across `scene.py`, `core.py`, `plotting.py`, and
`replay.py`; this package surface keeps those entrypoints available from a
single import location.
"""

from rfsynth.native.core import Rx, Scene, Signal, Source, Traffic, VirtualSignalEngine
from rfsynth.native.plotting import plot_artifacts, verify_artifacts
from rfsynth.native.replay import compile_replay, run_replay
from rfsynth.native.render import render_synthetic
from rfsynth.native.scene import load_scene

__all__ = [
    "Rx",
    "Scene",
    "Signal",
    "Source",
    "Traffic",
    "VirtualSignalEngine",
    "compile_replay",
    "load_scene",
    "plot_artifacts",
    "render_synthetic",
    "run_replay",
    "verify_artifacts",
]
