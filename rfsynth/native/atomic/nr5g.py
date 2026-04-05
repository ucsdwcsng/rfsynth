from __future__ import annotations

import math

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
    SYMBOL_PHASES,
    SYMBOL_SAMPLE_RATE_HZ,
    channel_linear_indices,
    channel_symbols,
    dmrs_linear_indices,
    dmrs_symbols,
)
from rfsynth.native.core import GeneratedBurst, Scene, Signal


def nr5g_burst(args: dict, *, apply_power: bool = True) -> GeneratedBurst:
    grid_size = int(args.get("gridSize", args.get("NDLRB", GRID_SIZE)))
    subcarrier_spacing_khz = float(args.get("subCarrierSpacing_kHz", args.get("subCarrierSpacing", SUBCARRIER_SPACING_KHZ)))
    cyclic_prefix = str(args.get("cyclicPrefix", args.get("CP", CYCLIC_PREFIX)))
    modulation = str(args.get("modulation", MODULATION))
    num_subframes = int(args.get("numSubframes", args.get("TotSubframes", NUM_SUBFRAMES)))
    sample_rate_hz = float(args.get("transmissionRate_Hz", args.get("sampleRate_Hz", SAMPLE_RATE_HZ)))
    channel_bandwidth_hz = float(args.get("bandwidth_Hz", BANDWIDTH_HZ))

    if grid_size != GRID_SIZE:
        raise ValueError(f"Python-native nr5g currently supports gridSize={GRID_SIZE}, not {grid_size}")
    if not math.isclose(subcarrier_spacing_khz, SUBCARRIER_SPACING_KHZ, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(f"Python-native nr5g currently supports subCarrierSpacing_kHz={SUBCARRIER_SPACING_KHZ}")
    if cyclic_prefix != CYCLIC_PREFIX:
        raise ValueError(f"Python-native nr5g currently supports cyclicPrefix={CYCLIC_PREFIX}")
    if modulation != MODULATION:
        raise ValueError(f"Python-native nr5g currently supports modulation={MODULATION}")
    if num_subframes != NUM_SUBFRAMES:
        raise ValueError(f"Python-native nr5g currently supports numSubframes={NUM_SUBFRAMES}")
    if not math.isclose(sample_rate_hz, SAMPLE_RATE_HZ, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"Python-native nr5g currently supports transmissionRate_Hz={SAMPLE_RATE_HZ}")
    if not math.isclose(channel_bandwidth_hz, BANDWIDTH_HZ, rel_tol=0.0, abs_tol=1.0):
        raise ValueError(f"Python-native nr5g currently supports bandwidth_Hz={BANDWIDTH_HZ}")

    grid = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.complex128)
    rows, cols = np.unravel_index(channel_linear_indices() - 1, (GRID_ROWS, GRID_COLS), order="F")
    grid[rows, cols] = channel_symbols()
    rows, cols = np.unravel_index(dmrs_linear_indices() - 1, (GRID_ROWS, GRID_COLS), order="F")
    grid[rows, cols] = dmrs_symbols()

    fullband_symbols: list[np.ndarray] = []
    mid = NFFT // 2
    for symbol_idx in range(GRID_COLS):
        spectrum = np.zeros(NFFT, dtype=np.complex128)
        spectrum[mid - GRID_ROWS // 2 : mid] = grid[: GRID_ROWS // 2, symbol_idx]
        spectrum[mid : mid + GRID_ROWS // 2] = grid[GRID_ROWS // 2 :, symbol_idx]
        time_symbol = np.fft.ifft(np.fft.ifftshift(spectrum))
        time_symbol *= np.exp(1j * SYMBOL_PHASES[symbol_idx])
        cp_len = int(CP_LENGTHS[symbol_idx])
        with_cp = np.concatenate([time_symbol[-cp_len:], time_symbol])
        expected_len = int(SYMBOL_LENGTHS[symbol_idx])
        if len(with_cp) != expected_len:
            raise ValueError(f"nr5g symbol length mismatch at symbol {symbol_idx}: expected {expected_len}, got {len(with_cp)}")
        fullband_symbols.append(with_cp)

    pre_resample = np.concatenate(fullband_symbols)
    if len(pre_resample) != int(np.sum(SYMBOL_LENGTHS)):
        raise ValueError("nr5g pre-resample waveform length mismatch")

    burst = scipy_signal.resample_poly(pre_resample, RESAMPLE_UP, RESAMPLE_DOWN)
    if len(burst) != int(round(SAMPLE_RATE_HZ * 1e-3 * NUM_SUBFRAMES)):
        raise ValueError("nr5g post-resample waveform length mismatch")

    if apply_power:
        burst = scale_to_power(burst, float(args.get("txPower_db", -68)))
    else:
        burst = burst.astype(np.complex64)

    return GeneratedBurst(
        samples=burst,
        sample_rate_hz=SAMPLE_RATE_HZ,
        bandwidth_hz=BANDWIDTH_HZ,
        protocol="cellular",
        modality="multi_carrier",
        modulation="ofdm",
        extras={
            "family": "nr5g",
            "gridSize": GRID_SIZE,
            "subCarrierSpacing_kHz": SUBCARRIER_SPACING_KHZ,
            "cyclicPrefix": CYCLIC_PREFIX,
            "modulation": MODULATION,
            "numSubframes": NUM_SUBFRAMES,
            "nfft": NFFT,
            "grid_rows": GRID_ROWS,
            "grid_cols": GRID_COLS,
            "symbol_sample_rate_hz": SYMBOL_SAMPLE_RATE_HZ,
        },
    )


class Nr5gSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene, rng
        return nr5g_burst(self.args)
