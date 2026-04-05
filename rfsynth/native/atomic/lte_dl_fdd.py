from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from rfsynth.native.atomic.common import scale_to_power
from rfsynth.native.core import GeneratedBurst, Scene, Signal

LTE_PRESET_RATES = {
    6: (1.4e6, 1.92e6),
    15: (3.0e6, 3.84e6),
    25: (5.0e6, 7.68e6),
    50: (10.0e6, 15.36e6),
    75: (15.0e6, 23.04e6),
    100: (20.0e6, 30.72e6),
}

LTE_PRESET_NFFT = {
    6: 128,
    15: 256,
    25: 512,
    50: 1024,
    75: 1536,
    100: 2048,
}

LTE_DIRECT_NCELLID = 10
LTE_DIRECT_CFI = 2


def _lte_control_symbol_count(ndlrb: int) -> int:
    # In 1.4 MHz LTE, CFI values {1,2,3} map to {2,3,4} control symbols.
    if ndlrb == 6:
        return LTE_DIRECT_CFI + 1
    return LTE_DIRECT_CFI


def _central_subcarriers(width: int) -> np.ndarray:
    half = width // 2
    return np.concatenate([np.arange(-half, 0, dtype=np.int64), np.arange(1, half + 1, dtype=np.int64)])


def _pn_qpsk_sequence(length: int, seed: int) -> np.ndarray:
    if length <= 0:
        return np.empty(0, dtype=np.complex128)
    rng = np.random.Generator(np.random.MT19937(seed))
    bits = rng.integers(0, 2, size=2 * length, dtype=np.int8)
    i = 1.0 - 2.0 * bits[0::2].astype(np.float64)
    q = 1.0 - 2.0 * bits[1::2].astype(np.float64)
    return ((i + 1j * q) / math.sqrt(2.0)).astype(np.complex128)


def _lte_pss_sequence(ncellid: int) -> np.ndarray:
    roots = (25, 29, 34)
    root = roots[ncellid % 3]
    n = np.arange(63, dtype=np.float64)
    zc = np.exp(-1j * math.pi * root * n * (n + 1.0) / 63.0)
    return np.delete(zc, 31).astype(np.complex128)


def _lte_sss_sequence(ncellid: int, subframe_idx: int) -> np.ndarray:
    signs = np.random.Generator(np.random.MT19937(1000 + 17 * ncellid + subframe_idx)).integers(0, 2, size=62, dtype=np.int8)
    return (1.0 - 2.0 * signs.astype(np.float64)).astype(np.complex128)


def _lte_reserved_values(symbol_idx: int, subframe_idx: int, active_subcarriers: np.ndarray, ref_carriers: set[int]) -> dict[int, complex]:
    reserved: dict[int, complex] = {}
    subframe_mod = subframe_idx % 10
    if subframe_mod in {0, 5} and symbol_idx == 5:
        sss_carriers = _central_subcarriers(62)
        sss_values = _lte_sss_sequence(LTE_DIRECT_NCELLID, subframe_idx)
        for carrier, value in zip(sss_carriers.tolist(), sss_values.tolist(), strict=True):
            reserved[int(carrier)] = complex(value)
    if subframe_mod in {0, 5} and symbol_idx == 6:
        pss_carriers = _central_subcarriers(62)
        pss_values = _lte_pss_sequence(LTE_DIRECT_NCELLID)
        for carrier, value in zip(pss_carriers.tolist(), pss_values.tolist(), strict=True):
            reserved[int(carrier)] = complex(value)
    if subframe_mod == 0 and symbol_idx in {7, 8, 9, 10}:
        pbch_carriers = _central_subcarriers(min(72, active_subcarriers.size))
        pbch_seed = 4000 + LTE_DIRECT_NCELLID * 31 + symbol_idx
        pbch_values = _pn_qpsk_sequence(len(pbch_carriers), pbch_seed)
        for carrier, value in zip(pbch_carriers.tolist(), pbch_values.tolist(), strict=True):
            carrier_i = int(carrier)
            if carrier_i in ref_carriers:
                continue
            reserved[carrier_i] = complex(value)
    return reserved


def _lte_payload_re_count(ndlrb: int, cp: str, subframe_idx: int) -> int:
    active_subcarriers = _active_subcarriers(ndlrb)
    ref_symbols = set(_reference_symbol_indices(cp))
    control_symbols = _lte_control_symbol_count(ndlrb)
    total = 0
    for symbol_idx in range(len(_cp_lengths(LTE_PRESET_NFFT[ndlrb], cp))):
        if symbol_idx < control_symbols:
            continue
        ref_carriers = set()
        if symbol_idx in ref_symbols:
            ref_carriers = set(_reference_subcarriers(active_subcarriers, symbol_idx, cp))
        reserved = _lte_reserved_values(symbol_idx, subframe_idx, active_subcarriers, ref_carriers)
        total += sum(1 for carrier in active_subcarriers.tolist() if int(carrier) not in ref_carriers and int(carrier) not in reserved)
    return total


def _lte_expected_payload_bits(args: dict[str, Any]) -> int:
    modulation = str(args.get("modulation", "QPSK")).upper()
    bits_per_symbol = 2 if modulation == "QPSK" else 4
    ndlrb = int(args.get("NDLRB", 6))
    cp = str(args.get("CP", "Normal")).capitalize()
    tot_subframes = int(args.get("TotSubframes", 1))
    payload_re = sum(_lte_payload_re_count(ndlrb, cp, subframe_idx) for subframe_idx in range(tot_subframes))
    return max(bits_per_symbol, payload_re * bits_per_symbol)


def _load_message_bits_from_path(message_path: str) -> list[int]:
    raw = json.loads(Path(message_path).read_text())
    if "message_bits" in raw:
        bits = raw["message_bits"]
    elif "payload" in raw and "message_bits" in raw["payload"]:
        bits = raw["payload"]["message_bits"]
    else:
        raise ValueError(f"Unsupported LTE message payload in {message_path}")
    return [int(bit) & 1 for bit in bits]


def _lte_message_bits(args: dict[str, Any], rng: np.random.Generator) -> np.ndarray:
    if "message" in args and args["message"] not in (None, []):
        return np.asarray(args["message"], dtype=np.int8).reshape(-1) & 1
    message_path = args.get("messagePath")
    if message_path and Path(str(message_path)).exists():
        return np.asarray(_load_message_bits_from_path(str(message_path)), dtype=np.int8)
    fallback_length = _lte_expected_payload_bits(args)
    return rng.integers(0, 2, size=fallback_length, dtype=np.int8)


def _gray_qpsk(bits: np.ndarray) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.int8).reshape(-1)
    if bits.size % 2:
        bits = np.append(bits, 0)
    b0 = bits[0::2]
    b1 = bits[1::2]
    i = 1.0 - 2.0 * b1.astype(np.float64)
    q = 1.0 - 2.0 * b0.astype(np.float64)
    return ((i + 1j * q) / math.sqrt(2.0)).astype(np.complex128)


def _gray_16qam(bits: np.ndarray) -> np.ndarray:
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


def _modulation_symbols(bits: np.ndarray, modulation: str) -> np.ndarray:
    modulation_u = modulation.upper()
    if modulation_u == "QPSK":
        return _gray_qpsk(bits)
    if modulation_u == "16QAM":
        return _gray_16qam(bits)
    raise ValueError(f"Unsupported direct LTE modulation {modulation}")


def _lte_gold_sequence(length: int, cinit: int) -> np.ndarray:
    if length <= 0:
        return np.empty(0, dtype=np.int8)
    state_len = 31
    total = 1600 + length + state_len
    x1 = np.zeros(total, dtype=np.int8)
    x2 = np.zeros(total, dtype=np.int8)
    x1[0] = 1
    for idx in range(state_len):
        x2[idx] = (cinit >> idx) & 1
    for idx in range(total - state_len):
        x1[idx + state_len] = (x1[idx + 3] + x1[idx]) & 1
        x2[idx + state_len] = (x2[idx + 3] + x2[idx + 2] + x2[idx + 1] + x2[idx]) & 1
    return (x1[1600 : 1600 + length] + x2[1600 : 1600 + length]) & 1


def _lte_pdsch_scramble(bits: np.ndarray, subframe_idx: int, *, rnti: int = 1, q: int = 0) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.int8).reshape(-1) & 1
    cinit = ((rnti & 0xFFFF) << 14) + ((q & 1) << 13) + ((2 * subframe_idx) << 9) + LTE_DIRECT_NCELLID
    seq = _lte_gold_sequence(bits.size, cinit)
    return bits ^ seq


def _active_subcarriers(ndlrb: int) -> np.ndarray:
    half = 6 * ndlrb
    return np.concatenate([np.arange(-half, 0, dtype=np.int64), np.arange(1, half + 1, dtype=np.int64)])


def _cp_lengths(nfft: int, cp: str) -> tuple[int, ...]:
    cp_u = cp.capitalize()
    if cp_u == "Normal":
        first = int(round(nfft * 160 / 2048))
        other = int(round(nfft * 144 / 2048))
        return (first, *([other] * 6), first, *([other] * 6))
    if cp_u == "Extended":
        extended = int(round(nfft * 512 / 2048))
        return tuple([extended] * 12)
    raise ValueError(f"Unsupported direct LTE cyclic prefix {cp}")


def _reference_symbol_indices(cp: str) -> tuple[int, ...]:
    if cp.capitalize() == "Normal":
        return (0, 4, 7, 11)
    return (0, 3, 6, 9)


def _lte_bin(subcarrier: int, nfft: int) -> int:
    return subcarrier % nfft


def _reference_subcarriers(active_subcarriers: np.ndarray, symbol_idx: int, cp: str) -> tuple[int, ...]:
    shift = LTE_DIRECT_NCELLID % 6
    if cp.capitalize() == "Normal" and symbol_idx >= 7:
        shift = (shift + 3) % 6
    return tuple(int(sc) for idx, sc in enumerate(active_subcarriers.tolist()) if idx % 6 == shift)


def _reference_values(count: int, symbol_idx: int) -> np.ndarray:
    return _pn_qpsk_sequence(count, 700 + LTE_DIRECT_NCELLID * 19 + symbol_idx)


def _control_values(count: int, symbol_idx: int) -> np.ndarray:
    return _pn_qpsk_sequence(count, 900 + LTE_DIRECT_NCELLID * 23 + symbol_idx)


def _lte_direct_supported(args: dict[str, Any]) -> bool:
    ndlrb = int(args.get("NDLRB", 6))
    cp = str(args.get("CP", "Normal")).capitalize()
    modulation = str(args.get("modulation", "QPSK")).upper()
    tot_subframes = int(args.get("TotSubframes", 1))
    n_packet = int(args.get("nPacket", 1))
    idle_time = float(args.get("idleTime", 0.0))
    if ndlrb not in LTE_PRESET_RATES:
        return False
    if cp not in {"Normal", "Extended"}:
        return False
    if modulation not in {"QPSK", "16QAM"}:
        return False
    if tot_subframes < 1:
        return False
    if n_packet != 1 or not math.isclose(idle_time, 0.0, rel_tol=0.0, abs_tol=1e-12):
        return False
    bandwidth_hz, sample_rate_hz = LTE_PRESET_RATES[ndlrb]
    want_bw = float(args.get("bandwidth_Hz", bandwidth_hz))
    want_fs = float(args.get("transmissionRate_Hz", sample_rate_hz))
    return math.isclose(want_bw, bandwidth_hz, rel_tol=0.0, abs_tol=1.0) and math.isclose(want_fs, sample_rate_hz, rel_tol=0.0, abs_tol=1e-6)


def _lte_direct_burst(args: dict[str, Any], rng: np.random.Generator, *, apply_power: bool = True) -> GeneratedBurst:
    ndlrb = int(args.get("NDLRB", 6))
    cp = str(args.get("CP", "Normal")).capitalize()
    modulation = str(args.get("modulation", "QPSK")).upper()
    tot_subframes = int(args.get("TotSubframes", 1))
    bandwidth_hz, sample_rate_hz = LTE_PRESET_RATES[ndlrb]
    nfft = LTE_PRESET_NFFT[ndlrb]
    cp_lengths = _cp_lengths(nfft, cp)
    active_subcarriers = _active_subcarriers(ndlrb)
    ref_symbols = set(_reference_symbol_indices(cp))
    control_symbols = _lte_control_symbol_count(ndlrb)
    symbols_per_subframe = len(cp_lengths)
    bits = _lte_message_bits(args, rng)
    wave_symbols: list[np.ndarray] = []
    bit_cursor = 0
    bits_per_symbol = 2 if modulation == "QPSK" else 4
    for subframe_idx in range(tot_subframes):
        subframe_re_count = _lte_payload_re_count(ndlrb, cp, subframe_idx)
        subframe_bit_count = subframe_re_count * bits_per_symbol
        subframe_bits = bits[bit_cursor : bit_cursor + subframe_bit_count]
        bit_cursor += min(subframe_bit_count, max(0, bits.size - bit_cursor))
        if subframe_bits.size < subframe_bit_count:
            subframe_bits = np.concatenate([subframe_bits, np.zeros(subframe_bit_count - subframe_bits.size, dtype=np.int8)])
        subframe_bits = _lte_pdsch_scramble(subframe_bits, subframe_idx)
        subframe_payload_symbols = _modulation_symbols(subframe_bits, modulation)
        payload_cursor = 0
        for sym_local_idx, cp_len in enumerate(cp_lengths):
            freq = np.zeros(nfft, dtype=np.complex128)
            control_symbol = sym_local_idx < control_symbols
            ref_carriers = set()
            ref_values = np.empty(0, dtype=np.complex128)
            if sym_local_idx in ref_symbols:
                ref_carriers = set(_reference_subcarriers(active_subcarriers, sym_local_idx, cp))
                ref_values = _reference_values(len(ref_carriers), subframe_idx * symbols_per_subframe + sym_local_idx)
            ref_index_map = {carrier: idx for idx, carrier in enumerate(sorted(ref_carriers))}
            reserved_values = _lte_reserved_values(sym_local_idx, subframe_idx, active_subcarriers, ref_carriers)

            if control_symbol:
                control_vals = _control_values(active_subcarriers.size - len(ref_carriers) - len(reserved_values), subframe_idx * symbols_per_subframe + sym_local_idx)
                ctrl_idx = 0
                for carrier in active_subcarriers:
                    carrier_i = int(carrier)
                    if carrier_i in ref_carriers:
                        continue
                    if carrier_i in reserved_values:
                        continue
                    freq[_lte_bin(carrier_i, nfft)] = control_vals[ctrl_idx]
                    ctrl_idx += 1
            else:
                for carrier in active_subcarriers:
                    carrier_i = int(carrier)
                    if carrier_i in ref_carriers:
                        continue
                    if carrier_i in reserved_values:
                        continue
                    if payload_cursor < subframe_payload_symbols.size:
                        freq[_lte_bin(carrier_i, nfft)] = subframe_payload_symbols[payload_cursor]
                        payload_cursor += 1

            for carrier in sorted(ref_carriers):
                freq[_lte_bin(carrier, nfft)] = ref_values[ref_index_map[carrier]]
            for carrier, value in reserved_values.items():
                freq[_lte_bin(carrier, nfft)] = value

            symbol_td = np.fft.ifft(freq)
            wave_symbols.append(np.concatenate([symbol_td[-cp_len:], symbol_td]))

    samples = np.concatenate(wave_symbols).astype(np.complex128)
    if apply_power:
        samples = scale_to_power(samples, float(args.get("txPower_db", -68)))
    else:
        samples = samples.astype(np.complex64)

    return GeneratedBurst(
        samples=samples,
        sample_rate_hz=sample_rate_hz,
        bandwidth_hz=bandwidth_hz,
        protocol="cellular",
        modality="multi_carrier",
        modulation="ofdm",
        extras={
            "family": "lte_dl_fdd",
            "runtimeMode": "direct",
            "NDLRB": ndlrb,
            "TotSubframes": tot_subframes,
            "CP": cp,
            "modulation": modulation,
            "centerFreq_Hz": float(args.get("centerFreq_Hz", 763e6)),
            "NCellID": LTE_DIRECT_NCELLID,
            "CFI": LTE_DIRECT_CFI,
            "controlSymbols": control_symbols,
            "nfft": nfft,
        },
    )


def lte_dl_fdd_burst(args: dict[str, Any], rng: np.random.Generator | None = None, *, apply_power: bool = True) -> GeneratedBurst:
    if rng is None:
        rng = np.random.Generator(np.random.MT19937(1234))
    if _lte_direct_supported(args):
        return _lte_direct_burst(args, rng, apply_power=apply_power)
    ndlrb = int(args.get("NDLRB", 6))
    cp = str(args.get("CP", "Normal")).capitalize()
    modulation = str(args.get("modulation", "QPSK")).upper()
    tot_subframes = int(args.get("TotSubframes", 1))
    raise ValueError(
        "Python-native LTE_DL_FDD currently supports only the direct matrix surface: "
        "NDLRB in {6,15,25,50,75,100}, CP in {Normal,Extended}, modulation in {QPSK,16QAM}, "
        f"TotSubframes >= 1 with nPacket=1 and idleTime=0. Got NDLRB={ndlrb}, CP={cp}, modulation={modulation}, TotSubframes={tot_subframes}."
    )


class LteDlFddSignal(Signal):
    def generate_transmission(self, scene: Scene, rng):
        del scene
        return lte_dl_fdd_burst(self.args, rng)
