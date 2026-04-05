from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy import signal as scipy_signal

from rfsynth.native.atomic.common import scale_to_power
from rfsynth.native.atomic.nr5g_template import (
    BANDWIDTH_HZ,
    CP_LENGTHS,
    CYCLIC_PREFIX,
    GRID_COLS,
    GRID_ROWS,
    GRID_SIZE,
    MODULATION,
    NFFT,
    NUM_SUBFRAMES,
    RESAMPLE_DOWN,
    RESAMPLE_UP,
    SAMPLE_RATE_HZ,
    SUBCARRIER_SPACING_KHZ,
    SYMBOL_LENGTHS,
    SYMBOL_SAMPLE_RATE_HZ,
    channel_linear_indices,
    channel_symbols,
    dmrs_linear_indices,
    dmrs_symbols,
    symbol_phase_sequence,
)
from rfsynth.native.core import GeneratedBurst, Scene, Signal


@lru_cache(maxsize=1)
def _fr1_profile() -> dict:
    raw = json.loads(Path(__file__).with_name("nr5g_fr1_template.json").read_text())
    symbol_phases = np.asarray(raw["symbol_phases"], dtype=np.float64)
    first_symbol_offset = float(SYMBOL_LENGTHS[0] - NFFT)
    center_freq_hz = float(-symbol_phases[0] * SYMBOL_SAMPLE_RATE_HZ / (2.0 * np.pi * first_symbol_offset))
    return {
        "grid_rows": int(raw["grid_rows"]),
        "grid_cols": int(raw["grid_cols"]),
        "channel_indices": np.asarray(raw["channel_indices"], dtype=np.int64),
        "channel_symbols": (
            np.asarray(raw["channel_symbols_real"], dtype=np.float64)
            + 1j * np.asarray(raw["channel_symbols_imag"], dtype=np.float64)
        ).astype(np.complex128),
        "dmrs_indices": np.asarray(raw["dmrs_indices"], dtype=np.int64),
        "dmrs_symbols": (
            np.asarray(raw["dmrs_symbols_real"], dtype=np.float64)
            + 1j * np.asarray(raw["dmrs_symbols_imag"], dtype=np.float64)
        ).astype(np.complex128),
        "symbol_phases": symbol_phases,
        "center_freq_hz": center_freq_hz,
        "channel_bandwidth_hz": 5e6,
    }


@lru_cache(maxsize=None)
def _named_grid_template(filename: str) -> dict:
    raw = json.loads(Path(__file__).with_name(filename).read_text())
    return {
        "grid_rows": int(raw["grid_rows"]),
        "grid_cols": int(raw["grid_cols"]),
        "grid_indices": np.asarray(raw["grid_indices"], dtype=np.int64),
        "grid_symbols": (
            np.asarray(raw["grid_symbols_real"], dtype=np.float64)
            + 1j * np.asarray(raw["grid_symbols_imag"], dtype=np.float64)
        ).astype(np.complex128),
        "symbol_phases": np.asarray(raw["symbol_phases"], dtype=np.float64),
        "center_freq_hz": float(raw["center_freq_hz"]),
        "channel_bandwidth_hz": float(raw["channel_bandwidth_hz"]),
        "grid_size": int(raw["grid_size"]),
        "modulation": str(raw["modulation"]),
        "waveform_profile": str(raw["waveform_profile"]),
    }


def nr5g_burst(args: dict, *, apply_power: bool = True) -> GeneratedBurst:
    grid_size = int(args.get("gridSize", args.get("NDLRB", GRID_SIZE)))
    subcarrier_spacing_khz = float(args.get("subCarrierSpacing_kHz", args.get("subCarrierSpacing", SUBCARRIER_SPACING_KHZ)))
    cyclic_prefix = str(args.get("cyclicPrefix", args.get("CP", CYCLIC_PREFIX)))
    modulation = str(args.get("modulation", MODULATION))
    waveform_profile = str(args.get("waveformProfile", "control"))
    num_subframes = int(args.get("numSubframes", args.get("TotSubframes", NUM_SUBFRAMES)))
    sample_rate_hz = float(args.get("transmissionRate_Hz", args.get("sampleRate_Hz", SAMPLE_RATE_HZ)))
    channel_bandwidth_hz = float(args.get("bandwidth_Hz", BANDWIDTH_HZ))
    center_freq_hz = float(args.get("centerFreq_Hz", 3.8e9))

    if grid_size not in {15, GRID_SIZE}:
        raise ValueError(f"Python-native nr5g currently supports gridSize 15 or {GRID_SIZE}, not {grid_size}")
    if not math.isclose(subcarrier_spacing_khz, SUBCARRIER_SPACING_KHZ, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(f"Python-native nr5g currently supports subCarrierSpacing_kHz={SUBCARRIER_SPACING_KHZ}")
    if cyclic_prefix != CYCLIC_PREFIX:
        raise ValueError(f"Python-native nr5g currently supports cyclicPrefix={CYCLIC_PREFIX}")
    if not 1 <= num_subframes <= 5:
        raise ValueError("Python-native nr5g currently supports numSubframes in [1, 5]")
    if not math.isclose(sample_rate_hz, SAMPLE_RATE_HZ, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"Python-native nr5g currently supports transmissionRate_Hz={SAMPLE_RATE_HZ}")

    if waveform_profile == "control" and grid_size == GRID_SIZE:
        if modulation != MODULATION:
            raise ValueError(f"Python-native nr5g currently supports modulation={MODULATION} for waveformProfile=control")
        if not math.isclose(channel_bandwidth_hz, BANDWIDTH_HZ, rel_tol=0.0, abs_tol=1.0):
            raise ValueError(f"Python-native nr5g currently supports bandwidth_Hz={BANDWIDTH_HZ} for gridSize={GRID_SIZE}")
        grid_rows = GRID_ROWS
        grid_cols = GRID_COLS
        channel_indices = channel_linear_indices()
        channel_values = channel_symbols()
        dmrs_indices = dmrs_linear_indices()
        dmrs_values = dmrs_symbols()
        symbol_phases = symbol_phase_sequence(center_freq_hz)
        burst_bandwidth_hz = BANDWIDTH_HZ
        template_grid_indices = None
        template_grid_values = None
    elif waveform_profile == "control":
        profile = _fr1_profile()
        expected_center_freq_hz = float(profile["center_freq_hz"])
        expected_bandwidth_hz = float(profile["channel_bandwidth_hz"])
        if modulation != MODULATION:
            raise ValueError(f"Python-native nr5g currently supports modulation={MODULATION} for waveformProfile=control")
        if not math.isclose(center_freq_hz, expected_center_freq_hz, rel_tol=0.0, abs_tol=1.0):
            raise ValueError(
                "Python-native nr5g gridSize=15 currently supports only the oracle-backed FR1 preset "
                f"at centerFreq_Hz={expected_center_freq_hz}"
            )
        if not math.isclose(channel_bandwidth_hz, expected_bandwidth_hz, rel_tol=0.0, abs_tol=1.0):
            raise ValueError(
                "Python-native nr5g gridSize=15 currently supports only the oracle-backed FR1 preset "
                f"with bandwidth_Hz={expected_bandwidth_hz}"
            )
        grid_rows = int(profile["grid_rows"])
        grid_cols = int(profile["grid_cols"])
        channel_indices = profile["channel_indices"]
        channel_values = profile["channel_symbols"]
        dmrs_indices = profile["dmrs_indices"]
        dmrs_values = profile["dmrs_symbols"]
        symbol_phases = profile["symbol_phases"]
        burst_bandwidth_hz = expected_bandwidth_hz
        template_grid_indices = None
        template_grid_values = None
    elif waveform_profile == "pdsch":
        profile = _named_grid_template("nr5g_pdsch_16qam_template.json")
        expected_center_freq_hz = float(profile["center_freq_hz"])
        expected_bandwidth_hz = float(profile["channel_bandwidth_hz"])
        expected_grid_size = int(profile["grid_size"])
        expected_modulation = str(profile["modulation"])
        if grid_size != expected_grid_size:
            raise ValueError(
                "Python-native nr5g waveformProfile=pdsch currently supports only the oracle-backed preset "
                f"with gridSize={expected_grid_size}"
            )
        if modulation != expected_modulation:
            raise ValueError(
                "Python-native nr5g waveformProfile=pdsch currently supports only the oracle-backed preset "
                f"with modulation={expected_modulation}"
            )
        if not math.isclose(center_freq_hz, expected_center_freq_hz, rel_tol=0.0, abs_tol=1.0):
            raise ValueError(
                "Python-native nr5g waveformProfile=pdsch currently supports only the oracle-backed preset "
                f"at centerFreq_Hz={expected_center_freq_hz}"
            )
        if not math.isclose(channel_bandwidth_hz, expected_bandwidth_hz, rel_tol=0.0, abs_tol=1.0):
            raise ValueError(
                "Python-native nr5g waveformProfile=pdsch currently supports only the oracle-backed preset "
                f"with bandwidth_Hz={expected_bandwidth_hz}"
            )
        grid_rows = int(profile["grid_rows"])
        grid_cols = int(profile["grid_cols"])
        symbol_phases = profile["symbol_phases"]
        burst_bandwidth_hz = expected_bandwidth_hz
        template_grid_indices = profile["grid_indices"]
        template_grid_values = profile["grid_symbols"]
        channel_indices = None
        channel_values = None
        dmrs_indices = None
        dmrs_values = None
    else:
        raise ValueError(f"Unsupported Python-native nr5g waveformProfile={waveform_profile}")

    grid = np.zeros((grid_rows, grid_cols), dtype=np.complex128)
    if template_grid_indices is not None:
        rows, cols = np.unravel_index(template_grid_indices - 1, (grid_rows, grid_cols), order="F")
        grid[rows, cols] = template_grid_values
    else:
        rows, cols = np.unravel_index(channel_indices - 1, (grid_rows, grid_cols), order="F")
        grid[rows, cols] = channel_values
        rows, cols = np.unravel_index(dmrs_indices - 1, (grid_rows, grid_cols), order="F")
        grid[rows, cols] = dmrs_values
    fullband_symbols: list[np.ndarray] = []
    mid = NFFT // 2
    for symbol_idx in range(grid_cols):
        spectrum = np.zeros(NFFT, dtype=np.complex128)
        spectrum[mid - grid_rows // 2 : mid] = grid[: grid_rows // 2, symbol_idx]
        spectrum[mid : mid + grid_rows // 2] = grid[grid_rows // 2 :, symbol_idx]
        time_symbol = np.fft.ifft(np.fft.ifftshift(spectrum))
        time_symbol *= np.exp(1j * symbol_phases[symbol_idx])
        cp_len = int(CP_LENGTHS[symbol_idx])
        with_cp = np.concatenate([time_symbol[-cp_len:], time_symbol])
        expected_len = int(SYMBOL_LENGTHS[symbol_idx])
        if len(with_cp) != expected_len:
            raise ValueError(f"nr5g symbol length mismatch at symbol {symbol_idx}: expected {expected_len}, got {len(with_cp)}")
        fullband_symbols.append(with_cp)

    pre_resample = np.concatenate(fullband_symbols)
    if len(pre_resample) != int(np.sum(SYMBOL_LENGTHS)):
        raise ValueError("nr5g pre-resample waveform length mismatch")

    burst_1sf = scipy_signal.resample_poly(pre_resample, RESAMPLE_UP, RESAMPLE_DOWN)
    if len(burst_1sf) != int(round(SAMPLE_RATE_HZ * 1e-3 * NUM_SUBFRAMES)):
        raise ValueError("nr5g post-resample waveform length mismatch")
    if num_subframes == 1:
        burst = burst_1sf
    else:
        pad = np.zeros(int(round((num_subframes - 1) * SAMPLE_RATE_HZ * 1e-3)), dtype=np.complex128)
        burst = np.concatenate([burst_1sf, pad])

    if apply_power:
        burst = scale_to_power(burst, float(args.get("txPower_db", -68)))
    else:
        burst = burst.astype(np.complex64)

    return GeneratedBurst(
        samples=burst,
        sample_rate_hz=SAMPLE_RATE_HZ,
        bandwidth_hz=burst_bandwidth_hz,
        protocol="cellular",
        modality="multi_carrier",
        modulation="ofdm",
        extras={
            "family": "nr5g",
            "gridSize": grid_size,
            "subCarrierSpacing_kHz": SUBCARRIER_SPACING_KHZ,
            "cyclicPrefix": CYCLIC_PREFIX,
            "modulation": modulation,
            "waveformProfile": waveform_profile,
            "numSubframes": num_subframes,
            "nfft": NFFT,
            "grid_rows": grid_rows,
            "grid_cols": grid_cols,
            "symbol_sample_rate_hz": SYMBOL_SAMPLE_RATE_HZ,
            "centerFreq_Hz": center_freq_hz,
        },
    )


class Nr5gSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return nr5g_burst(self.args)
