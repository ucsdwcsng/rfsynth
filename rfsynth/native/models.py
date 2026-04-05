from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(slots=True)
class GenerationSpec:
    total_time_s: float
    output_folder: Path
    output_base: str
    flag_output_iq_samples: bool = True


@dataclass(slots=True)
class TransmissionWindow:
    start_time: float
    stop_time: float


@dataclass(slots=True)
class SignalRenderResult:
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
    base_path: Path
    paths: dict[str, Path]


@dataclass(slots=True)
class ReplayEvent:
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
    scene_id: str
    sample_rate_hz: float
    center_freq_hz: float
    events: list[ReplayEvent]
    base_path: Path | None = None


@dataclass(slots=True)
class ReplayRunReport:
    backend: str
    event_count: int
    output_path: Path | None
    details: dict[str, Any]
