"""Public Python API for the JSON-first native runtime.

This module re-exports the entrypoints that the CLI and external callers use:

- `load_scene(...)` to normalize config into a `Scene`
- `render_synthetic(...)` to produce IQ and metadata artifacts
- `plot_artifacts(...)` / `verify_artifacts(...)` for post-render inspection
- `compile_replay(...)` / `run_replay(...)` for replay planning
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
