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
    CHANNEL_IMAG_SIGNS,
    CHANNEL_REAL_SIGNS,
    CP_LENGTHS,
    CYCLIC_PREFIX,
    DMRS_IMAG_SIGNS,
    DMRS_REAL_SIGNS,
    GRID_COLS,
    GRID_ROWS,
    GRID_SIZE,
    MODULATION,
    NFFT,
    NUM_SUBFRAMES,
    QPSK_MAGNITUDE,
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


def _control_rows_for_block(start: int, block_len: int) -> tuple[np.ndarray, np.ndarray]:
    all_rows = np.arange(start, start + block_len, dtype=np.int64)
    dmrs_rows = np.arange(start + 1, start + block_len, 4, dtype=np.int64)
    mask = np.ones_like(all_rows, dtype=bool)
    mask[(dmrs_rows - start)] = False
    channel_rows = all_rows[mask]
    return channel_rows, dmrs_rows


def _fr1_control_indices() -> tuple[np.ndarray, np.ndarray]:
    rows: list[np.ndarray] = []
    dmrs_rows: list[np.ndarray] = []
    for start in (1, 73):
        ch, dm = _control_rows_for_block(start, 48)
        rows.append(ch)
        dmrs_rows.append(dm)
    base_ch = np.concatenate(rows)
    base_dm = np.concatenate(dmrs_rows)
    channel_idx = np.concatenate([base_ch + (symbol_idx * 180) for symbol_idx in range(3)]).astype(np.int64)
    dmrs_idx = np.concatenate([base_dm + (symbol_idx * 180) for symbol_idx in range(3)]).astype(np.int64)
    return channel_idx, dmrs_idx


def _fr1_control_symbols() -> tuple[np.ndarray, np.ndarray]:
    channel_count = 216
    dmrs_count = 72
    channel = (QPSK_MAGNITUDE * (CHANNEL_REAL_SIGNS[:channel_count] + 1j * CHANNEL_IMAG_SIGNS[:channel_count])).astype(np.complex128)
    dmrs = (QPSK_MAGNITUDE * (DMRS_REAL_SIGNS[:dmrs_count] + 1j * DMRS_IMAG_SIGNS[:dmrs_count])).astype(np.complex128)
    return channel, dmrs


def _gray_16qam_symbols(bits: np.ndarray) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.int8).reshape(-1)
    pad = (-bits.size) % 4
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.int8)])
    b0 = bits[0::4]
    b1 = bits[1::4]
    b2 = bits[2::4]
    b3 = bits[3::4]
    i = (1.0 - 2.0 * b1.astype(np.float64)) * (2.0 - (1.0 - 2.0 * b0.astype(np.float64)))
    q = (1.0 - 2.0 * b3.astype(np.float64)) * (2.0 - (1.0 - 2.0 * b2.astype(np.float64)))
    return ((i + 1j * q) / math.sqrt(10.0)).astype(np.complex128)


def _load_test_vector_bits(args: dict) -> np.ndarray | None:
    path = args.get("testVectorPath")
    if not path:
        return None
    payload = json.loads(Path(str(path)).read_text()).get("payload", {})
    if "message_bits" not in payload:
        return None
    return np.asarray(payload["message_bits"], dtype=np.int8).reshape(-1) & 1


def _qpsk_from_bits(bits: np.ndarray, count: int) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.int8).reshape(-1) & 1
    if bits.size == 0:
        bits = np.zeros(2 * count, dtype=np.int8)
    need = 2 * count
    if bits.size < need:
        reps = int(math.ceil(need / bits.size))
        bits = np.tile(bits, reps)
    bits = bits[:need]
    i = 1.0 - 2.0 * bits[0::2].astype(np.float64)
    q = 1.0 - 2.0 * bits[1::2].astype(np.float64)
    return ((i + 1j * q) / math.sqrt(2.0)).astype(np.complex128)


def nr5g_burst(args: dict, rng: np.random.Generator | None = None, *, apply_power: bool = True) -> GeneratedBurst:
    if rng is None:
        rng = np.random.Generator(np.random.MT19937(1234))
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
        runtime_mode = "direct"
    elif waveform_profile == "control":
        if modulation != MODULATION:
            raise ValueError(f"Python-native nr5g currently supports modulation={MODULATION} for waveformProfile=control")
        if not math.isclose(channel_bandwidth_hz, 5e6, rel_tol=0.0, abs_tol=1.0):
            raise ValueError("Python-native nr5g gridSize=15 currently supports bandwidth_Hz=5000000.0")
        grid_rows = 180
        grid_cols = GRID_COLS
        channel_indices, dmrs_indices = _fr1_control_indices()
        channel_values, dmrs_values = _fr1_control_symbols()
        symbol_phases = symbol_phase_sequence(center_freq_hz)
        burst_bandwidth_hz = 5e6
        runtime_mode = "direct"
    elif waveform_profile == "pdsch":
        if grid_size != GRID_SIZE:
            raise ValueError(f"Python-native nr5g waveformProfile=pdsch currently supports gridSize={GRID_SIZE}")
        if modulation != "16QAM":
            raise ValueError("Python-native nr5g waveformProfile=pdsch currently supports modulation=16QAM")
        if not math.isclose(channel_bandwidth_hz, BANDWIDTH_HZ, rel_tol=0.0, abs_tol=1.0):
            raise ValueError(f"Python-native nr5g waveformProfile=pdsch currently supports bandwidth_Hz={BANDWIDTH_HZ}")
        grid_rows = GRID_ROWS
        grid_cols = GRID_COLS
        symbol_phases = symbol_phase_sequence(center_freq_hz)
        burst_bandwidth_hz = BANDWIDTH_HZ
        message_bits = _load_test_vector_bits(args)
        if message_bits is None:
            message_bits = np.asarray(args.get("messageBits", []), dtype=np.int8).reshape(-1)
        if message_bits.size == 0:
            message_bits = rng.integers(0, 2, size=grid_rows * grid_cols * 4, dtype=np.int8)
        data_symbols = _gray_16qam_symbols(message_bits)
        dmrs_len = 150
        dmrs_real = np.resize(DMRS_REAL_SIGNS, dmrs_len)
        dmrs_imag = np.resize(DMRS_IMAG_SIGNS, dmrs_len)
        dmrs_symbols_pdsch = (QPSK_MAGNITUDE * (dmrs_real + 1j * dmrs_imag)).astype(np.complex128)
        grid = np.zeros((grid_rows, grid_cols), dtype=np.complex128)
        cursor = 0
        for col in range(grid_cols):
            if col == 2:
                grid[0::2, col] = data_symbols[cursor : cursor + (grid_rows // 2)]
                cursor += grid_rows // 2
                grid[1::4, col] = dmrs_symbols_pdsch[: grid[1::4, col].size]
                grid[3::4, col] = dmrs_symbols_pdsch[: grid[3::4, col].size]
            else:
                need = grid_rows
                grid[:, col] = data_symbols[cursor : cursor + need]
                cursor += need
        channel_indices = None
        channel_values = None
        dmrs_indices = None
        dmrs_values = None
        runtime_mode = "direct"
    else:
        raise ValueError(f"Unsupported Python-native nr5g waveformProfile={waveform_profile}")

    if waveform_profile == "control":
        message_bits = _load_test_vector_bits(args)
        if message_bits is not None and message_bits.size > 0:
            channel_len = channel_values.size
            qpsk = _qpsk_from_bits(message_bits, channel_len)
            channel_values = qpsk

    if waveform_profile != "pdsch":
        grid = np.zeros((grid_rows, grid_cols), dtype=np.complex128)
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
            "runtimeMode": runtime_mode,
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
        del scene
        return nr5g_burst(self.args, rng)
