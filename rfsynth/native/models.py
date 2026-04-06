"""Small data containers shared across the Python-native runtime.

These classes intentionally carry very little behavior. They let the runtime
pass around a normalized scene, per-signal render results, plot outputs, and
replay plans without depending on MATLAB structs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(slots=True)
class GenerationSpec:
    """Normalized generation-level output settings for one scene."""

    total_time_s: float
    output_folder: Path
    output_base: str
    flag_output_iq_samples: bool = True


@dataclass(slots=True)
class TransmissionWindow:
    """One [start, stop] interval where a burst should be placed in the scene."""

    start_time: float
    stop_time: float


@dataclass(slots=True)
class SignalRenderResult:
    """Per-signal metadata assembled after the burst has been rendered."""

    instance_name: str
    source_name: str
    source_origin: str
    source_location: tuple[float, float, float]
    channel_model: str
    signal_type: str
    protocol: str
    modality: str
    modulation: str
    center_freq_hz: float
    bandwidth_hz: float
    tx_power_db: float
    burst_sample_rate_hz: float
    transmissions: list[TransmissionWindow]
    required_metadata: dict[str, Any]
    transmission_reports: list[dict[str, Any]]
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ArtifactBundle:
    """The complete output of one synthetic render invocation."""

    scene: Any
    base_path: Path
    iq_path: Path
    metadata_path: Path
    scoring_path: Path
    metadata: dict[str, Any]
    scoring: dict[str, Any]
    signals: list[SignalRenderResult]
    iq: np.ndarray


@dataclass(slots=True)
class PlotBundle:
    """Paths to the PNG plots generated from one rendered artifact bundle."""

    base_path: Path
    paths: dict[str, Path]


@dataclass(slots=True)
class ReplayEvent:
    """One timed replay event derived from rendered transmission metadata."""

    instance_name: str
    source_name: str
    signal_name: str
    time_start: float
    time_stop: float
    center_freq_hz: float
    bandwidth_hz: float
    freq_lo_hz: float
    freq_hi_hz: float


@dataclass(slots=True)
class ReplayPlan:
    """Flattened replay schedule produced from rendered metadata."""

    scene_id: str
    sample_rate_hz: float
    center_freq_hz: float
    events: list[ReplayEvent]
    base_path: Path | None = None


@dataclass(slots=True)
class ReplayRunReport:
    """Backend-specific summary for one replay execution attempt."""

    backend: str
    event_count: int
    output_path: Path | None
    details: dict[str, Any]
