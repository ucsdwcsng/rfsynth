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
LTE_DIRECT_RNTI = 1
LTE_DIRECT_PDCCH_FORMAT = 2
LTE_DIRECT_PDCCH_AGGREGATION_LEVEL = 2**LTE_DIRECT_PDCCH_FORMAT
LTE_TURBO_SUBBLOCK_INTERLEAVER_PATTERN = np.array(
    [0, 16, 8, 24, 4, 20, 12, 28, 2, 18, 10, 26, 6, 22, 14, 30, 1, 17, 9, 25, 5, 21, 13, 29, 3, 19, 11, 27, 7, 23, 15, 31],
    dtype=np.int64,
)
LTE_SUBBLOCK_INTERLEAVER_PATTERN = np.array(
    [1, 17, 9, 25, 5, 21, 13, 29, 3, 19, 11, 27, 7, 23, 15, 31, 0, 16, 8, 24, 4, 20, 12, 28, 2, 18, 10, 26, 6, 22, 14, 30],
    dtype=np.int64,
)
LTE_TURBO_PARITY2_INTERLEAVER_PATTERN = np.mod(LTE_TURBO_SUBBLOCK_INTERLEAVER_PATTERN + 1, 32).astype(np.int64)
LTE_DIRECT_PCFICH_CODEWORDS = {
    1: np.asarray([0, 1, 1] * 10 + [0, 1], dtype=np.int8),
    2: np.asarray([1, 0, 1] * 10 + [1, 0], dtype=np.int8),
    3: np.asarray([1, 1, 0] * 10 + [1, 1], dtype=np.int8),
}
LTE_DIRECT_PDSCH_MODCODING = {
    6: {"QPSK": 3, "16QAM": 10},
    15: {"QPSK": 6, "16QAM": 13},
    25: {"QPSK": 7, "16QAM": 13},
    50: {"QPSK": 7, "16QAM": 14},
    75: {"QPSK": 7, "16QAM": 14},
    100: {"QPSK": 8, "16QAM": 14},
}
LTE_DIRECT_SUBFRAME_MODCODING = {
    # Narrow direct RMC schedule as decoded from lteRMCDLTool over subframes 0..9.
    (6, "Normal", "QPSK"): (3, 7, 7, 7, 7, 6, 7, 7, 7, 7),
}
LTE_DIRECT_DCI_PAYLOAD_LENGTHS = {
    6: 19,
    15: 23,
    25: 27,
    50: 31,
    75: 33,
    100: 39,
}
LTE_QPP_PARAMS = {
    40: (3, 10),
    48: (7, 12),
    56: (19, 42),
    64: (7, 16),
    72: (7, 18),
    80: (11, 20),
    88: (5, 22),
    96: (11, 24),
    104: (7, 26),
    112: (41, 84),
    120: (103, 90),
    128: (15, 32),
    136: (9, 34),
    144: (17, 108),
    152: (9, 38),
    160: (21, 120),
    168: (101, 84),
    176: (21, 44),
    184: (57, 46),
    192: (23, 48),
    200: (13, 50),
    208: (27, 52),
    216: (11, 36),
    224: (27, 56),
    232: (85, 58),
    240: (29, 60),
    248: (33, 62),
    256: (15, 32),
    264: (17, 198),
    272: (33, 68),
    280: (103, 210),
    288: (19, 36),
    296: (19, 74),
    304: (37, 76),
    312: (19, 78),
    320: (21, 120),
    328: (21, 82),
    336: (115, 84),
    344: (193, 86),
    352: (21, 44),
    360: (133, 90),
    368: (81, 46),
    376: (45, 94),
    384: (23, 48),
    392: (243, 98),
    400: (151, 40),
    408: (155, 102),
    416: (25, 52),
    424: (51, 106),
    432: (47, 72),
    440: (91, 110),
    448: (29, 168),
    456: (29, 114),
    464: (247, 58),
    472: (29, 118),
    480: (89, 180),
    488: (91, 122),
    496: (157, 62),
    504: (55, 84),
    512: (31, 64),
    528: (17, 66),
    544: (35, 68),
    560: (227, 420),
    576: (65, 96),
    592: (19, 74),
    608: (37, 76),
    624: (41, 234),
    640: (39, 80),
    656: (185, 82),
    672: (43, 252),
    688: (21, 86),
    704: (155, 44),
    720: (79, 120),
    736: (139, 92),
    752: (23, 94),
    768: (217, 48),
    784: (25, 98),
    800: (17, 80),
    816: (127, 102),
    832: (25, 52),
    848: (239, 106),
    864: (17, 48),
    880: (137, 110),
    896: (215, 112),
    912: (29, 114),
    928: (15, 58),
    944: (147, 118),
    960: (29, 60),
    976: (59, 122),
    992: (65, 124),
    1008: (55, 84),
    1024: (31, 64),
    1056: (17, 66),
    1088: (171, 204),
    1120: (67, 140),
    1152: (35, 72),
    1184: (19, 74),
    1216: (39, 76),
    1248: (19, 78),
    1280: (199, 240),
    1312: (21, 82),
    1344: (211, 252),
    1376: (21, 86),
    1408: (43, 88),
    1440: (149, 60),
    1472: (45, 92),
    1504: (49, 846),
    1536: (71, 48),
    1568: (13, 28),
    1600: (17, 80),
    1632: (25, 102),
    1664: (183, 104),
    1696: (55, 954),
    1728: (127, 96),
    1760: (27, 110),
    1792: (29, 112),
    1824: (29, 114),
    1856: (57, 116),
    1888: (45, 354),
    1920: (31, 120),
    1952: (59, 610),
    1984: (185, 124),
    2016: (113, 420),
    2048: (31, 64),
    2112: (17, 66),
    2176: (171, 136),
    2240: (209, 420),
    2304: (253, 216),
    2368: (367, 444),
    2432: (265, 456),
    2496: (181, 468),
    2560: (39, 80),
    2624: (27, 164),
    2688: (127, 504),
    2752: (143, 172),
    2816: (43, 88),
    2880: (29, 300),
    2944: (45, 92),
    3008: (157, 188),
    3072: (47, 96),
    3136: (13, 28),
    3200: (111, 240),
    3264: (443, 204),
    3328: (51, 104),
    3392: (51, 212),
    3456: (451, 192),
    3520: (257, 220),
    3584: (57, 336),
    3648: (313, 228),
    3712: (271, 232),
    3776: (179, 236),
    3840: (331, 120),
    3904: (363, 244),
    3968: (375, 248),
    4032: (127, 168),
    4096: (31, 64),
    4160: (33, 130),
    4224: (43, 264),
    4288: (33, 134),
    4352: (477, 408),
    4416: (35, 138),
    4480: (233, 280),
    4544: (357, 142),
    4608: (337, 480),
    4672: (37, 146),
    4736: (71, 444),
    4800: (71, 120),
    4864: (37, 152),
    4928: (39, 462),
    4992: (127, 234),
    5056: (39, 158),
    5120: (39, 80),
    5184: (31, 96),
    5248: (113, 902),
    5312: (41, 166),
    5376: (251, 336),
    5440: (43, 170),
    5504: (21, 86),
    5568: (43, 174),
    5632: (45, 176),
    5696: (45, 178),
    5760: (161, 120),
    5824: (89, 182),
    5888: (323, 184),
    5952: (47, 186),
    6016: (23, 94),
    6080: (47, 190),
    6144: (263, 480),
}
LTE_DIRECT_TRBLK_SCHEDULES: dict[tuple[int, str, str], tuple[int, ...]] = {
    # Reference-model transport-block schedules returned by lteRMCDLTool for
    # the direct single-codeword Port0 surface used here.
    (6, "Normal", "QPSK"): (328, 712, 712, 712, 712, 600, 712, 712, 712, 712),
    (6, "Extended", "QPSK"): (208, 600, 600, 600, 600, 408, 600, 600, 600, 600),
    (15, "Normal", "QPSK"): (1544, 2088, 2088, 2088, 2088, 1800, 2088, 2088, 2088, 2088),
    (25, "Normal", "QPSK"): (3112, 3496, 3496, 3496, 3496, 3112, 3496, 3496, 3496, 3496),
    (50, "Normal", "QPSK"): (6200, 6968, 6968, 6968, 6968, 6968, 6968, 6968, 6968, 6968),
    (75, "Normal", "QPSK"): (9144, 10680, 10680, 10680, 10680, 10680, 10680, 10680, 10680, 10680),
    (100, "Normal", "QPSK"): (14112, 14112, 14112, 14112, 14112, 14112, 14112, 14112, 14112, 14112),
    (6, "Normal", "16QAM"): (936, 1544, 1544, 1544, 1544, 1192, 1544, 1544, 1544, 1544),
    (15, "Normal", "16QAM"): (3368, 4264, 4264, 4264, 4264, 3880, 4264, 4264, 4264, 4264),
    (25, "Normal", "16QAM"): (5736, 6456, 6456, 6456, 6456, 6456, 6456, 6456, 6456, 6456),
    (50, "Normal", "16QAM"): (12960, 14112, 14112, 14112, 14112, 12960, 14112, 14112, 14112, 14112),
    (75, "Normal", "16QAM"): (19080, 21384, 21384, 21384, 21384, 21384, 21384, 21384, 21384, 21384),
    (100, "Normal", "16QAM"): (25456, 28336, 28336, 28336, 28336, 28336, 28336, 28336, 28336, 28336),
}
LTE_QPP_BLOCK_SIZES = tuple(sorted(LTE_QPP_PARAMS))


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
    n_id_1 = ncellid // 3
    n_id_2 = ncellid % 3
    q_prime = n_id_1 // 30
    q = (n_id_1 + (q_prime * (q_prime + 1)) // 2) // 30
    m_prime = n_id_1 + (q * (q + 1)) // 2
    m0 = m_prime % 31
    m1 = (m0 + m_prime // 31 + 1) % 31

    def mseq(taps: tuple[int, ...]) -> np.ndarray:
        state = [0, 0, 0, 0, 1]
        for n in range(31):
            state.append(sum(state[n + tap] for tap in taps) & 1)
        return (1.0 - 2.0 * np.asarray(state[:31], dtype=np.float64)).astype(np.float64)

    s_tilde = mseq((0, 2))
    c_tilde = mseq((0, 3))
    z_tilde = mseq((0, 1, 2, 4))

    seq = np.zeros(62, dtype=np.float64)
    if subframe_idx % 10 == 0:
        for n in range(31):
            seq[2 * n] = s_tilde[(n + m0) % 31] * c_tilde[(n + n_id_2) % 31]
            seq[2 * n + 1] = s_tilde[(n + m1) % 31] * c_tilde[(n + n_id_2 + 3) % 31] * z_tilde[(n + (m0 % 8)) % 31]
        return seq.astype(np.complex128)

    signs = np.random.Generator(np.random.MT19937(1000 + 17 * ncellid + subframe_idx)).integers(0, 2, size=62, dtype=np.int8)
    return (1.0 - 2.0 * signs.astype(np.float64)).astype(np.complex128)


def _lte_bw_index(ndlrb: int) -> int:
    mapping = {6: 0, 15: 1, 25: 2, 50: 3, 75: 4, 100: 5}
    return mapping.get(ndlrb, 7)


def _lte_pdsch_modcoding_index(ndlrb: int, modulation: str, cp: str) -> int:
    modulation_u = str(modulation).upper()
    cp_u = str(cp).capitalize()
    if cp_u == "Extended" and ndlrb == 6 and modulation_u == "QPSK":
        return 1
    return LTE_DIRECT_PDSCH_MODCODING[ndlrb][modulation_u]


def _lte_subframe_modcoding_index(args: dict[str, Any], subframe_idx: int) -> int:
    ndlrb = int(args.get("NDLRB", 6))
    modulation = str(args.get("modulation", "QPSK")).upper()
    cp = str(args.get("CP", "Normal")).capitalize()
    schedule = LTE_DIRECT_SUBFRAME_MODCODING.get((ndlrb, cp, modulation))
    if schedule is not None:
        return int(schedule[int(subframe_idx) % len(schedule)])
    return _lte_pdsch_modcoding_index(ndlrb, modulation, cp)


def _lte_qpp_interleaver_params(block_size: int) -> tuple[int, int]:
    try:
        return LTE_QPP_PARAMS[int(block_size)]
    except KeyError as exc:
        raise ValueError(f"Unsupported LTE turbo interleaver block size {block_size}.") from exc


def _lte_qpp_interleaver_indices(block_size: int) -> np.ndarray:
    f1, f2 = _lte_qpp_interleaver_params(block_size)
    idx = np.arange(block_size, dtype=np.int64)
    return np.mod(f1 * idx + f2 * idx * idx, block_size).astype(np.int64)


def _lte_crc_attach(bits: np.ndarray, poly: str) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.int8).reshape(-1)
    data = (bits >= 0).astype(np.int8) & bits.clip(min=0, max=1)
    if poly == "24A":
        taps = [24, 23, 18, 17, 14, 11, 10, 7, 6, 5, 4, 3, 1, 0]
        width = 24
    elif poly == "24B":
        taps = [24, 23, 6, 5, 1, 0]
        width = 24
    else:
        raise ValueError(f"Unsupported LTE CRC polynomial {poly}")
    work = np.concatenate([data, np.zeros(width, dtype=np.int8)])
    poly_bits = np.zeros(width + 1, dtype=np.int8)
    for tap in taps:
        poly_bits[width - tap] = 1
    for idx in range(data.size):
        if work[idx]:
            work[idx : idx + width + 1] ^= poly_bits
    return np.concatenate([bits, work[-width:]])


def _lte_dlsch_info(block_len: int) -> dict[str, int]:
    block_len_i = int(block_len)
    if block_len_i < 0:
        raise ValueError("LTE DL-SCH block length must be non-negative.")
    if block_len_i <= 6144:
        kp = next(k for k in LTE_QPP_BLOCK_SIZES if k >= block_len_i)
        return {
            "C": 1,
            "Km": 0,
            "Cm": 0,
            "Kp": kp,
            "Cp": 1,
            "F": kp - block_len_i,
            "L": 0,
            "Bout": kp,
        }
    l_seg = 24
    c = int(math.ceil(block_len_i / (6144 - l_seg)))
    b_prime = block_len_i + c * l_seg
    avg = b_prime / c
    kp = next(k for k in LTE_QPP_BLOCK_SIZES if k >= avg)
    kp_index = LTE_QPP_BLOCK_SIZES.index(kp)
    if kp_index == 0:
        raise ValueError(f"Unsupported LTE DL-SCH segmentation average block size {avg}.")
    km = LTE_QPP_BLOCK_SIZES[kp_index - 1]
    cm = int(math.floor((c * kp - b_prime) / (kp - km)))
    cp = c - cm
    filler = cm * km + cp * kp - b_prime
    return {
        "C": c,
        "Km": km,
        "Cm": cm,
        "Kp": kp,
        "Cp": cp,
        "F": filler,
        "L": l_seg,
        "Bout": cm * km + cp * kp,
    }


def _lte_code_block_segment(bits: np.ndarray) -> list[np.ndarray]:
    bits = np.asarray(bits, dtype=np.int8).reshape(-1)
    info = _lte_dlsch_info(bits.size)
    block_sizes = [info["Km"]] * info["Cm"] + [info["Kp"]] * info["Cp"]
    data_sizes = [block_size - info["L"] for block_size in block_sizes]
    work = np.concatenate([np.full(info["F"], -1, dtype=np.int8), bits])
    blocks: list[np.ndarray] = []
    cursor = 0
    for data_size in data_sizes:
        block_data = work[cursor : cursor + data_size]
        if block_data.size != data_size:
            raise ValueError("LTE code-block segmentation produced a truncated block.")
        cursor += data_size
        if info["C"] > 1:
            blocks.append(_lte_crc_attach(block_data, "24B"))
        else:
            blocks.append(block_data)
    if cursor != work.size:
        raise ValueError("LTE code-block segmentation did not consume the full transport block.")
    return blocks


def _uint_to_bits(value: int, width: int) -> np.ndarray:
    return np.array([(value >> shift) & 1 for shift in range(width - 1, -1, -1)], dtype=np.int8)


def _lte_turbo_constituent_encode(bits: np.ndarray) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int]]:
    bits_i = np.asarray(bits, dtype=np.int8).reshape(-1)
    systematic = np.zeros(bits_i.size, dtype=np.int8)
    parity = np.zeros(bits_i.size, dtype=np.int8)
    s0 = s1 = s2 = 0
    for idx, raw_bit in enumerate(bits_i):
        bit = 0 if int(raw_bit) < 0 else int(raw_bit) & 1
        feedback = (bit ^ s1 ^ s2) & 1
        parity_bit = (feedback ^ s0 ^ s2) & 1
        systematic[idx] = raw_bit if int(raw_bit) < 0 else bit
        parity[idx] = raw_bit if int(raw_bit) < 0 else parity_bit
        s0, s1, s2 = feedback, s0, s1
    return systematic, parity, (s0, s1, s2)


def _lte_turbo_termination_chunks(state1: tuple[int, int, int], state2: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    a = np.array([(state1[1] ^ state1[2]) & 1, state1[1] & 1, (state2[1] ^ state2[2]) & 1, state2[1] & 1], dtype=np.int8)
    b = np.array([(state1[0] ^ state1[2]) & 1, state1[0] & 1, (state2[0] ^ state2[2]) & 1, state2[0] & 1], dtype=np.int8)
    c = np.array([(state1[0] ^ state1[1]) & 1, state1[0] & 1, (state2[0] ^ state2[1]) & 1, state2[0] & 1], dtype=np.int8)
    return a, b, c


def _lte_turbo_encode_block(bits: np.ndarray) -> np.ndarray:
    bits_i = np.asarray(bits, dtype=np.int8).reshape(-1)
    interleaved = bits_i[_lte_qpp_interleaver_indices(bits_i.size)]
    systematic, parity1, state1 = _lte_turbo_constituent_encode(bits_i)
    _, parity2, state2 = _lte_turbo_constituent_encode(interleaved)
    tail_a, tail_b, tail_c = _lte_turbo_termination_chunks(state1, state2)
    return np.concatenate([systematic, tail_a, parity1, tail_b, parity2, tail_c])


def _lte_mib_bits(args: dict[str, Any]) -> np.ndarray:
    ndlrb = int(args.get("NDLRB", 6))
    phich_duration = str(args.get("PHICHDuration", "Normal")).capitalize()
    ng = str(args.get("Ng", "Sixth")).capitalize()
    nframe = int(args.get("NFrame", 0))
    ng_map = {"Sixth": 0, "Half": 1, "One": 2, "Two": 3}
    bits = np.zeros(24, dtype=np.int8)
    bits[0:3] = _uint_to_bits(_lte_bw_index(ndlrb), 3)
    bits[3] = 1 if phich_duration == "Extended" else 0
    bits[4:6] = _uint_to_bits(ng_map.get(ng, 0), 2)
    bits[6:14] = _uint_to_bits((nframe // 4) & 0xFF, 8)
    return bits


def _lte_crc16_attach(bits: np.ndarray, mask: int = 0) -> np.ndarray:
    data = np.concatenate([np.asarray(bits, dtype=np.int8).reshape(-1) & 1, np.zeros(16, dtype=np.int8)])
    poly = np.array([1 if idx in {0, 4, 11, 16} else 0 for idx in range(17)], dtype=np.int8)
    for idx in range(data.size - 16):
        if data[idx]:
            data[idx : idx + 17] ^= poly
    crc = data[-16:]
    if mask:
        crc ^= _uint_to_bits(mask, 16)
    return np.concatenate([np.asarray(bits, dtype=np.int8).reshape(-1) & 1, crc])


def _lte_conv_encode(bits: np.ndarray) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.int8).reshape(-1) & 1
    if bits.size == 0:
        return np.empty(0, dtype=np.int8)
    g0 = np.array([1, 0, 1, 1, 0, 1, 1], dtype=np.int8)
    g1 = np.array([1, 1, 1, 1, 0, 0, 1], dtype=np.int8)
    g2 = np.array([1, 1, 1, 0, 1, 0, 1], dtype=np.int8)
    reg = np.zeros(7, dtype=np.int8)
    reg[1 : 1 + min(6, bits.size)] = bits[-6:][::-1]
    d0 = np.zeros(bits.size, dtype=np.int8)
    d1 = np.zeros(bits.size, dtype=np.int8)
    d2 = np.zeros(bits.size, dtype=np.int8)
    for idx, bit in enumerate(bits):
        reg[0] = bit
        d0[idx] = int(np.sum(reg * g0) & 1)
        d1[idx] = int(np.sum(reg * g1) & 1)
        d2[idx] = int(np.sum(reg * g2) & 1)
        reg[1:] = reg[:-1]
    return np.concatenate([d0, d1, d2])


def _lte_subblock_interleave(stream: np.ndarray, pattern: np.ndarray) -> np.ndarray:
    stream = np.asarray(stream, dtype=np.int8).reshape(-1)
    c = 32
    r = int(math.ceil(stream.size / c))
    k_pi = r * c
    dummy = np.full(k_pi - stream.size, -1, dtype=np.int8)
    matrix = np.concatenate([dummy, stream]).reshape(r, c)
    return matrix[:, pattern].T.reshape(-1)


def _lte_conv_subblock_interleave(stream: np.ndarray) -> np.ndarray:
    return _lte_subblock_interleave(stream, LTE_SUBBLOCK_INTERLEAVER_PATTERN)


def _lte_rate_match_convolutional(encoded: np.ndarray, out_len: int) -> np.ndarray:
    encoded = np.asarray(encoded, dtype=np.int8).reshape(-1)
    if encoded.size % 3 != 0:
        raise ValueError("LTE convolutional encoder output must be divisible by 3.")
    d = encoded.size // 3
    streams = [encoded[i * d : (i + 1) * d] for i in range(3)]
    circular = np.concatenate([_lte_conv_subblock_interleave(stream) for stream in streams])
    out = np.zeros(out_len, dtype=np.int8)
    cursor = 0
    for idx in range(out_len):
        while circular[cursor % circular.size] < 0:
            cursor += 1
        out[idx] = circular[cursor % circular.size]
        cursor += 1
    return out


def _lte_rate_match_turbo_block(encoded: np.ndarray, out_len: int, rv: int = 0) -> np.ndarray:
    encoded_i = np.asarray(encoded, dtype=np.int8).reshape(-1)
    if encoded_i.size % 3 != 0:
        raise ValueError("LTE turbo encoder output must be divisible by 3.")
    d = encoded_i.size // 3
    r_subblock = int(math.ceil(d / 32.0))
    k_pi = r_subblock * 32
    systematic = encoded_i[:d]
    parity1 = encoded_i[d : 2 * d]
    parity2 = encoded_i[2 * d :]
    v0 = _lte_subblock_interleave(systematic, LTE_TURBO_SUBBLOCK_INTERLEAVER_PATTERN)
    v1 = _lte_subblock_interleave(parity1, LTE_TURBO_SUBBLOCK_INTERLEAVER_PATTERN)
    v2 = _lte_subblock_interleave(parity2, LTE_TURBO_PARITY2_INTERLEAVER_PATTERN)
    circular = np.full(3 * k_pi, -1, dtype=np.int8)
    circular[:k_pi] = v0
    for idx in range(k_pi):
        circular[k_pi + 2 * idx] = v1[idx]
        circular[k_pi + 2 * idx + 1] = v2[idx]
    n_cb = circular.size
    k0 = r_subblock * (2 * int(math.ceil(n_cb / (8.0 * r_subblock))) * int(rv) + 2)
    out = np.zeros(out_len, dtype=np.int8)
    out_idx = 0
    cursor = 0
    while out_idx < out_len:
        value = circular[(k0 + cursor) % n_cb]
        if value >= 0:
            out[out_idx] = value
            out_idx += 1
        cursor += 1
    return out


def _lte_dlsch_rate_match_lengths(out_len: int, code_block_count: int, modulation: str, n_layers: int = 1) -> list[int]:
    q_m = {"QPSK": 2, "16QAM": 4, "64QAM": 6}.get(str(modulation).upper())
    if q_m is None:
        raise ValueError(f"Unsupported LTE DL-SCH modulation {modulation}")
    if code_block_count < 1:
        return []
    g_prime = int(out_len // (n_layers * q_m))
    gamma = g_prime % code_block_count
    base = g_prime // code_block_count
    lengths: list[int] = []
    for block_idx in range(code_block_count):
        if gamma > 0 and block_idx >= code_block_count - gamma:
            e_prime = base + 1
        else:
            e_prime = base
        lengths.append(n_layers * q_m * e_prime)
    if sum(lengths) != out_len:
        raise ValueError("LTE DL-SCH rate-match split does not sum to the requested output length.")
    return lengths


def _lte_dlsch_encode_transport_block(bits: np.ndarray, out_len: int, rv: int = 0, modulation: str = "QPSK", n_layers: int = 1) -> np.ndarray:
    transport = np.asarray(bits, dtype=np.int8).reshape(-1)
    crc_block = _lte_crc_attach(transport, "24A")
    segments = _lte_code_block_segment(crc_block)
    lengths = _lte_dlsch_rate_match_lengths(out_len, len(segments), modulation, n_layers=n_layers)
    coded_blocks: list[np.ndarray] = []
    for segment, length in zip(segments, lengths, strict=True):
        turbo = _lte_turbo_encode_block(segment)
        coded_blocks.append(_lte_rate_match_turbo_block(turbo, length, rv=rv))
    return np.concatenate(coded_blocks) if coded_blocks else np.empty(0, dtype=np.int8)


def _lte_pbch_qpsk_symbols(args: dict[str, Any]) -> np.ndarray:
    mib = _lte_mib_bits(args)
    coded = _lte_crc16_attach(mib)
    conv = _lte_conv_encode(coded)
    cp = str(args.get("CP", "Normal")).capitalize()
    out_len = 1920 if cp == "Normal" else 1728
    rate_matched = _lte_rate_match_convolutional(conv, out_len)
    scrambled = rate_matched ^ _lte_gold_sequence(out_len, LTE_DIRECT_NCELLID)
    quarter_len = out_len // 4
    nframe = int(args.get("NFrame", 0))
    start = (nframe % 4) * quarter_len
    return _gray_qpsk(scrambled[start : start + quarter_len])


def _lte_pbch_symbol_indices(cp: str) -> tuple[int, int, int, int]:
    if cp.capitalize() == "Normal":
        return (7, 8, 9, 10)
    return (6, 7, 8, 9)


def _lte_sync_symbol_indices(cp: str) -> tuple[int, int]:
    if cp.capitalize() == "Normal":
        return (5, 6)
    return (4, 5)


def _lte_pbch_carriers(active_subcarriers: np.ndarray, sym_local_idx: int, cp: str, ref_carriers: set[int]) -> np.ndarray:
    sparse_symbols = {7, 8} if cp.capitalize() == "Normal" else {6, 7, 9}
    if sym_local_idx in sparse_symbols:
        pbch_rows = (
            [0, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18, 20, 21, 23, 24, 26, 27, 29, 30, 32, 33, 35,
             36, 38, 39, 41, 42, 44, 45, 47, 48, 50, 51, 53, 54, 56, 57, 59, 60, 62, 63, 65, 66, 68, 69, 71]
        )
        center_start = (active_subcarriers.size - 72) // 2
        carriers = np.asarray([active_subcarriers[center_start + row] for row in pbch_rows], dtype=np.int64)
    else:
        carriers = _central_subcarriers(min(72, active_subcarriers.size))
    if not ref_carriers:
        return carriers
    return np.asarray([carrier for carrier in carriers.tolist() if int(carrier) not in ref_carriers], dtype=np.int64)


def _lte_reserved_values(
    symbol_idx: int,
    subframe_idx: int,
    active_subcarriers: np.ndarray,
    ref_carriers: set[int],
    args: dict[str, Any] | None = None,
) -> dict[int, complex]:
    reserved: dict[int, complex] = {}
    subframe_mod = subframe_idx % 10
    sss_symbol_idx, pss_symbol_idx = _lte_sync_symbol_indices(str(args.get("CP", "Normal")) if args is not None else "Normal")
    if subframe_mod in {0, 5} and symbol_idx == sss_symbol_idx:
        sync_width = 62 if active_subcarriers.size <= 72 else 72
        sss_carriers = _central_subcarriers(sync_width)
        sss_values = _lte_sss_sequence(LTE_DIRECT_NCELLID, subframe_idx)
        sss_center = (sync_width - sss_values.size) // 2
        sss_symbols = np.zeros(sync_width, dtype=np.complex128)
        sss_symbols[sss_center : sss_center + sss_values.size] = sss_values
        for carrier, value in zip(sss_carriers.tolist(), sss_symbols.tolist(), strict=True):
            reserved[int(carrier)] = complex(value)
    if subframe_mod in {0, 5} and symbol_idx == pss_symbol_idx:
        sync_width = 62 if active_subcarriers.size <= 72 else 72
        pss_carriers = _central_subcarriers(sync_width)
        pss_values = _lte_pss_sequence(LTE_DIRECT_NCELLID)
        pss_center = (sync_width - pss_values.size) // 2
        pss_symbols = np.zeros(sync_width, dtype=np.complex128)
        pss_symbols[pss_center : pss_center + pss_values.size] = pss_values
        for carrier, value in zip(pss_carriers.tolist(), pss_symbols.tolist(), strict=True):
            reserved[int(carrier)] = complex(value)
    if args is None:
        pbch_symbols_local = (7, 8, 9, 10)
    else:
        pbch_symbols_local = _lte_pbch_symbol_indices(str(args.get("CP", "Normal")))
    if subframe_mod == 0 and symbol_idx in pbch_symbols_local:
        if args is None:
            pbch_values = _pn_qpsk_sequence(len(_lte_pbch_carriers(active_subcarriers, symbol_idx, "Normal", ref_carriers)), 4000 + LTE_DIRECT_NCELLID * 31 + symbol_idx)
            pbch_carriers = _lte_pbch_carriers(active_subcarriers, symbol_idx, "Normal", ref_carriers)
        else:
            pbch_symbols = _lte_pbch_qpsk_symbols(args)
            cp = str(args.get("CP", "Normal")).capitalize()
            counts: list[int] = []
            for local_symbol in _lte_pbch_symbol_indices(cp):
                counts.append(len(_lte_pbch_carriers(active_subcarriers, local_symbol, cp, set())))
            offsets = np.cumsum([0, *counts[:-1]])
            current_idx = _lte_pbch_symbol_indices(cp).index(symbol_idx)
            start = int(offsets[current_idx])
            stop = start + counts[current_idx]
            pbch_carriers = _lte_pbch_carriers(active_subcarriers, symbol_idx, cp, set())
            pbch_values = pbch_symbols[start:stop]
        for carrier, value in zip(pbch_carriers.tolist(), pbch_values.tolist(), strict=True):
            carrier_i = int(carrier)
            if carrier_i in ref_carriers:
                continue
            reserved[carrier_i] = complex(value)
        sparse_symbols = {7, 8} if cp.capitalize() == "Normal" else {6, 7, 9}
        if symbol_idx in sparse_symbols:
            full_pbch_region = set(_central_subcarriers(min(72, active_subcarriers.size)).tolist())
            null_carriers = full_pbch_region.difference(int(carrier) for carrier in pbch_carriers.tolist()).difference(ref_carriers)
            for carrier_i in null_carriers:
                reserved[int(carrier_i)] = 0.0j
    return reserved


def _lte_payload_re_count(ndlrb: int, cp: str, subframe_idx: int, args: dict[str, Any] | None = None) -> int:
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
        reserved = _lte_reserved_values(symbol_idx, subframe_idx, active_subcarriers, ref_carriers, args)
        allowed_rows = _lte_narrow_allowed_rows(ndlrb, cp, symbol_idx, subframe_idx)
        total += sum(
            1
            for row_idx, carrier in enumerate(active_subcarriers.tolist())
            if (allowed_rows is None or row_idx in allowed_rows)
            and int(carrier) not in ref_carriers
            and int(carrier) not in reserved
        )
    return total


def _lte_narrow_allowed_rows(ndlrb: int, cp: str, symbol_idx: int, subframe_idx: int) -> set[int] | None:
    if ndlrb != 6:
        return None
    subframe_mod = subframe_idx % 10
    if subframe_mod not in {0, 5}:
        return None
    sss_symbol_idx, pss_symbol_idx = _lte_sync_symbol_indices(cp)
    if symbol_idx == 0:
        return set(idx for idx in range(72) if idx % 6 != 1)
    if symbol_idx == 1:
        return set(idx for idx in range(72) if idx not in set(range(16, 20)) | set(range(52, 56)))
    if symbol_idx == 2:
        blocked = set(range(4, 8)) | set(range(32, 36)) | set(range(68, 72))
        return set(idx for idx in range(72) if idx not in blocked)
    if symbol_idx in {sss_symbol_idx, pss_symbol_idx}:
        return set(range(5, 67))
    if symbol_idx == 7:
        if subframe_mod == 0:
            blocked = {1, 7, 13, 19, 25, 31, 37, 43, 49, 55, 61, 67}
            return set(idx for idx in range(72) if idx not in blocked)
        return None
    if symbol_idx == 8:
        if subframe_mod == 0:
            blocked = {1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43, 46, 49, 52, 55, 58, 61, 64, 67, 70}
            return set(idx for idx in range(72) if idx not in blocked)
        return None
    return None


def _lte_expected_payload_bits(args: dict[str, Any]) -> int:
    modulation = str(args.get("modulation", "QPSK")).upper()
    bits_per_symbol = 2 if modulation == "QPSK" else 4
    ndlrb = int(args.get("NDLRB", 6))
    cp = str(args.get("CP", "Normal")).capitalize()
    tot_subframes = int(args.get("TotSubframes", 1))
    payload_re = sum(_lte_payload_re_count(ndlrb, cp, subframe_idx, args) for subframe_idx in range(tot_subframes))
    return max(bits_per_symbol, payload_re * bits_per_symbol)


def _lte_transport_block_schedule(args: dict[str, Any]) -> tuple[int, ...] | None:
    ndlrb = int(args.get("NDLRB", 6))
    cp = str(args.get("CP", "Normal")).capitalize()
    modulation = str(args.get("modulation", "QPSK")).upper()
    return LTE_DIRECT_TRBLK_SCHEDULES.get((ndlrb, cp, modulation))


def _lte_transport_block_bits_total(args: dict[str, Any]) -> int | None:
    schedule = _lte_transport_block_schedule(args)
    if schedule is None:
        return None
    tot_subframes = int(args.get("TotSubframes", 1))
    if tot_subframes < 1:
        return 0
    return int(sum(schedule[subframe_idx % len(schedule)] for subframe_idx in range(tot_subframes)))


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
    transport_length = _lte_transport_block_bits_total(args)
    fallback_length = transport_length
    if fallback_length is None:
        fallback_length = _lte_expected_payload_bits(args)
    return rng.integers(0, 2, size=fallback_length, dtype=np.int8)


def _lte_transport_stream_window(stream_bits: np.ndarray, cursor: int, length: int) -> tuple[np.ndarray, int]:
    stream = np.asarray(stream_bits, dtype=np.int8).reshape(-1) & 1
    if length <= 0:
        return np.empty(0, dtype=np.int8), int(cursor)
    if stream.size == 0:
        return np.zeros(length, dtype=np.int8), int(cursor)
    start = int(cursor)
    take_idx = (np.arange(length, dtype=np.int64) + start) % stream.size
    return stream[take_idx], start + length


def _gray_qpsk(bits: np.ndarray) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.int8).reshape(-1)
    if bits.size % 2:
        bits = np.append(bits, 0)
    b0 = bits[0::2]
    b1 = bits[1::2]
    i = 1.0 - 2.0 * b0.astype(np.float64)
    q = 1.0 - 2.0 * b1.astype(np.float64)
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
    i = (1.0 - 2.0 * b0.astype(np.float64)) * (2.0 - (1.0 - 2.0 * b2.astype(np.float64)))
    q = (1.0 - 2.0 * b1.astype(np.float64)) * (2.0 - (1.0 - 2.0 * b3.astype(np.float64)))
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
    cinit = ((rnti & 0xFFFF) << 14) + ((q & 1) << 13) + (int(subframe_idx) << 9) + LTE_DIRECT_NCELLID
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
    cp_norm = cp.capitalize()
    if cp_norm == "Normal" and symbol_idx in {4, 11}:
        shift = (shift + 3) % 6
    if cp_norm == "Extended" and symbol_idx in {3, 9}:
        shift = (shift + 3) % 6
    return tuple(int(sc) for idx, sc in enumerate(active_subcarriers.tolist()) if idx % 6 == shift)


def _reference_values(ndlrb: int, cp: str, subframe_idx: int, sym_local_idx: int) -> np.ndarray:
    symbols_per_slot = 7 if cp.capitalize() == "Normal" else 6
    slot_in_subframe = sym_local_idx // symbols_per_slot
    l_in_slot = sym_local_idx % symbols_per_slot
    ns = 2 * subframe_idx + slot_in_subframe
    ncp = 1 if cp.capitalize() == "Normal" else 0
    cinit = (1 << 10) * (7 * (ns + 1) + l_in_slot + 1) * (2 * LTE_DIRECT_NCELLID + 1)
    cinit += 2 * LTE_DIRECT_NCELLID + ncp
    max_dlrb = 110
    full_length = 2 * max_dlrb
    seq_bits = _lte_gold_sequence(2 * full_length, cinit)
    i = 1.0 - 2.0 * seq_bits[0::2].astype(np.float64)
    q = 1.0 - 2.0 * seq_bits[1::2].astype(np.float64)
    full_seq = ((i + 1j * q) / math.sqrt(2.0)).astype(np.complex128)
    start = max_dlrb - ndlrb
    end = start + 2 * ndlrb
    return full_seq[start:end]


def _control_values(count: int, symbol_idx: int) -> np.ndarray:
    return _pn_qpsk_sequence(count, 900 + LTE_DIRECT_NCELLID * 23 + symbol_idx)


def _lte_control_cinit(subframe_idx: int) -> int:
    return (((subframe_idx + 1) * (2 * LTE_DIRECT_NCELLID + 1)) << 9) + LTE_DIRECT_NCELLID


def _lte_control_prbs(length: int, subframe_idx: int) -> np.ndarray:
    return _lte_gold_sequence(length, _lte_control_cinit(subframe_idx))


def _lte_pdcch_prbs(length: int, subframe_idx: int = 0) -> np.ndarray:
    return _lte_gold_sequence(length, LTE_DIRECT_NCELLID + (int(subframe_idx) << 9))


def _lte_type0_rbg_size(ndlrb: int) -> int:
    if ndlrb <= 10:
        return 1
    if ndlrb <= 26:
        return 2
    if ndlrb <= 63:
        return 3
    return 4


def _lte_full_allocation_bitmap(ndlrb: int) -> np.ndarray:
    p = _lte_type0_rbg_size(ndlrb)
    n_rbg = int(math.ceil(ndlrb / p))
    return np.ones(n_rbg, dtype=np.int8)


def _lte_harq_process_number(subframe_idx: int) -> int:
    # Downlink FDD HARQ processes advance with subframe number over an 8-process window.
    return int(subframe_idx) % 8


def _lte_default_dci_bits(args: dict[str, Any], subframe_idx: int | None = None) -> np.ndarray:
    ndlrb = int(args.get("NDLRB", 6))
    modulation = str(args.get("modulation", "QPSK")).upper()
    cp = str(args.get("CP", "Normal")).capitalize()
    if subframe_idx is None:
        subframe_idx = int(args.get("NSubframe", 0))
    bitmap = _lte_full_allocation_bitmap(ndlrb)
    modcoding = _lte_subframe_modcoding_index(args, int(subframe_idx))
    payload = []
    if ndlrb > 10:
        payload.append(0)  # AllocationType=0
    payload.extend(bitmap.tolist())
    payload.extend(_uint_to_bits(modcoding, 5).tolist())
    payload.extend(_uint_to_bits(_lte_harq_process_number(int(subframe_idx)), 3).tolist())
    payload.append(1)  # New data
    payload.extend([0, 0])  # RV
    payload.extend([0, 0])  # TPCPUCCH
    payload_bits = np.asarray(payload, dtype=np.int8)
    want_len = LTE_DIRECT_DCI_PAYLOAD_LENGTHS[ndlrb]
    if payload_bits.size < want_len:
        payload_bits = np.concatenate([payload_bits, np.zeros(want_len - payload_bits.size, dtype=np.int8)])
    return payload_bits[:want_len]


def _lte_dci_encode(bits: np.ndarray, out_len: int = 288) -> np.ndarray:
    coded = _lte_crc16_attach(np.asarray(bits, dtype=np.int8), mask=LTE_DIRECT_RNTI)
    conv = _lte_conv_encode(coded)
    return _lte_rate_match_convolutional(conv, out_len)


def _lte_qpsk_with_nil(bits: np.ndarray) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.int16).reshape(-1)
    if bits.size % 2:
        bits = np.append(bits, -1)
    out = np.zeros(bits.size // 2, dtype=np.complex128)
    for idx in range(out.size):
        pair = bits[2 * idx : 2 * idx + 2]
        if np.any(pair < 0):
            continue
        out[idx] = _gray_qpsk(pair.astype(np.int8))[0]
    return out


def _symbol0_reg_rows(rb_idx: int) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    base = 12 * rb_idx
    return (
        (base + 0, base + 2, base + 3, base + 5),
        (base + 6, base + 8, base + 9, base + 11),
    )


def _symbol_full_reg_rows(rb_idx: int) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int]]:
    base = 12 * rb_idx
    return (
        (base + 0, base + 1, base + 2, base + 3),
        (base + 4, base + 5, base + 6, base + 7),
        (base + 8, base + 9, base + 10, base + 11),
    )


def _lte_pcfich_reg_starts(ndlrb: int) -> tuple[int, int, int, int]:
    kbar = 6 * (LTE_DIRECT_NCELLID % (2 * ndlrb))
    return tuple(int((kbar + 6 * math.floor(i * ndlrb / 2.0)) % (12 * ndlrb)) for i in range(4))


def _lte_pcfich_rows(ndlrb: int) -> list[tuple[int, int, int, int]]:
    return [(start, start + 2, start + 3, start + 5) for start in _lte_pcfich_reg_starts(ndlrb)]


def _lte_phich_rows(ndlrb: int) -> list[tuple[int, int, int, int]]:
    # Current direct surface uses Ng='Sixth', Normal duration, CellRefP=1.
    presets = {
        6: [18, 36, 66],
        15: [72, 126, 6],
        25: [66, 162, 258],
        50: [66, 264, 462, 72, 270, 468],
        75: [66, 360, 660, 72, 366, 666],
        100: [66, 462, 858, 72, 468, 864, 78, 474, 870],
    }
    starts = presets[ndlrb]
    return [(start, start + 2, start + 3, start + 5) for start in starts]


def _lte_control_region_regs(ndlrb: int, cp: str, subframe_idx: int) -> list[tuple[int, tuple[int, int, int, int]]]:
    del subframe_idx
    control_symbols = _lte_control_symbol_count(ndlrb)
    regs: list[tuple[int, tuple[int, int, int, int]]] = []
    for rb_idx in range(ndlrb):
        symbol0_regs = _symbol0_reg_rows(rb_idx)
        later_symbol_regs = [_symbol_full_reg_rows(rb_idx) for _ in range(max(0, control_symbols - 1))]
        regs.append((0, symbol0_regs[0]))
        for reg_idx in range(3):
            for sym_local_idx in range(1, control_symbols):
                regs.append((sym_local_idx, later_symbol_regs[sym_local_idx - 1][reg_idx]))
        regs.append((0, symbol0_regs[1]))
    return regs


def _lte_pdcch_available_regs(ndlrb: int, cp: str, subframe_idx: int) -> list[tuple[int, tuple[int, int, int, int]]]:
    del cp, subframe_idx
    excluded = {
        (0, tuple(rows)) for rows in _lte_pcfich_rows(ndlrb)
    } | {
        (0, tuple(rows)) for rows in _lte_phich_rows(ndlrb)
    }
    control_symbols = _lte_control_symbol_count(ndlrb)
    ordered: list[tuple[int, tuple[int, int, int, int]]] = []
    for rb_idx in range(ndlrb):
        symbol0_a, symbol0_b = _symbol0_reg_rows(rb_idx)
        later = [
            [
                (sym_local_idx, _symbol_full_reg_rows(rb_idx)[reg_idx])
                for sym_local_idx in range(1, control_symbols)
            ]
            for reg_idx in range(3)
        ]
        has_a = (0, symbol0_a) not in excluded
        has_b = (0, symbol0_b) not in excluded
        if has_a:
            ordered.append((0, symbol0_a))
        ordered.extend(reg for reg in later[0] if reg not in excluded)
        ordered.extend(reg for reg in later[1] if reg not in excluded)
        if has_b:
            ordered.append((0, symbol0_b))
        ordered.extend(reg for reg in later[2] if reg not in excluded)
    return ordered


def _lte_pdcch_interleave(reg_symbols: np.ndarray) -> np.ndarray:
    n_reg = reg_symbols.shape[0]
    rows = int(math.ceil(n_reg / 32.0))
    k_pi = rows * 32
    reg_indices = np.arange(n_reg, dtype=np.int64)
    padded = np.full(k_pi, -1, dtype=np.int64)
    padded[-n_reg:] = reg_indices
    matrix = padded.reshape(rows, 32)
    interleaved_idx = matrix[:, LTE_SUBBLOCK_INTERLEAVER_PATTERN].T.reshape(k_pi)
    interleaved_idx = interleaved_idx[interleaved_idx >= 0]
    shift = LTE_DIRECT_NCELLID % n_reg
    return reg_symbols[np.roll(interleaved_idx, -shift)]


def _lte_pdcch_n_cce(total_regs: int) -> int:
    return int(total_regs) // 9


def _lte_pdcch_yk(subframe_idx: int, rnti: int = LTE_DIRECT_RNTI) -> int:
    yk = int(rnti)
    for _ in range(int(subframe_idx) + 1):
        yk = (39827 * yk) % 65537
    return yk


def _lte_pdcch_candidate_starts(
    total_regs: int,
    subframe_idx: int,
    *,
    aggregation_level: int = LTE_DIRECT_PDCCH_AGGREGATION_LEVEL,
    rnti: int = LTE_DIRECT_RNTI,
) -> list[int]:
    n_cce = _lte_pdcch_n_cce(total_regs)
    if n_cce <= 0:
        return [0]
    level = max(1, int(aggregation_level))
    n_slots = max(1, n_cce // level)
    candidate_count = 6 if level in {1, 2} else 2
    yk = _lte_pdcch_yk(subframe_idx, rnti=rnti)
    return [level * ((yk + m_idx) % n_slots) for m_idx in range(candidate_count)]


def _lte_pcfich_symbols(subframe_idx: int) -> np.ndarray:
    codeword = LTE_DIRECT_PCFICH_CODEWORDS[LTE_DIRECT_CFI].copy()
    scrambled = codeword ^ _lte_control_prbs(codeword.size, subframe_idx)
    return _gray_qpsk(scrambled)


def _lte_phich_symbols(subframe_idx: int, n_mapping_units: int, cp: str) -> np.ndarray:
    if n_mapping_units <= 0:
        return np.empty(0, dtype=np.complex128)
    if cp.capitalize() == "Extended":
        # The current direct surface uses the first ACK sequence in each PHICH
        # group. With extended CP, each mapping unit carries two PHICH groups
        # in disjoint RE pairs.
        base_signs = np.asarray(
            [-1.0, 1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0, -1.0, 1.0, -1.0, 1.0],
            dtype=np.float64,
        )
        base = ((base_signs + 1j * base_signs) / math.sqrt(2.0)).astype(np.complex128)
        return np.tile(base, int(n_mapping_units))
    prbs = _lte_control_prbs(12, subframe_idx)
    signs = -(1.0 - 2.0 * prbs.astype(np.float64))
    group_symbols = ((signs + 1j * signs) / math.sqrt(2.0)).astype(np.complex128)
    return np.tile(group_symbols, int(max(0, n_mapping_units)))


def _lte_pdcch_symbols(args: dict[str, Any], subframe_idx: int, total_regs: int) -> np.ndarray:
    payload_bits = _lte_default_dci_bits(args, subframe_idx=subframe_idx)
    aggregation_level = LTE_DIRECT_PDCCH_AGGREGATION_LEVEL
    coded = _lte_dci_encode(payload_bits, out_len=72 * aggregation_level)
    total_bits = total_regs * 8
    padded = np.full(total_bits, -1, dtype=np.int8)
    candidate_starts = _lte_pdcch_candidate_starts(total_regs, subframe_idx, aggregation_level=aggregation_level)
    start_bit = 72 * candidate_starts[0]
    stop_bit = min(start_bit + coded.size, total_bits)
    padded[start_bit:stop_bit] = coded[: stop_bit - start_bit]
    scramble = _lte_pdcch_prbs(total_bits, subframe_idx)
    scrambled = padded.copy()
    valid = scrambled >= 0
    scrambled[valid] ^= scramble[valid]
    symbols = _lte_qpsk_with_nil(scrambled)
    reg_symbols = symbols.reshape(total_regs, 4)
    return _lte_pdcch_interleave(reg_symbols).reshape(-1)


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


def _lte_direct_channel_grids(args: dict[str, Any], bits: np.ndarray) -> dict[str, np.ndarray]:
    ndlrb = int(args.get("NDLRB", 6))
    cp = str(args.get("CP", "Normal")).capitalize()
    modulation = str(args.get("modulation", "QPSK")).upper()
    tot_subframes = int(args.get("TotSubframes", 1))
    active_subcarriers = _active_subcarriers(ndlrb)
    ref_symbols = set(_reference_symbol_indices(cp))
    control_symbols = _lte_control_symbol_count(ndlrb)
    cp_lengths = _cp_lengths(LTE_PRESET_NFFT[ndlrb], cp)
    symbols_per_subframe = len(cp_lengths)
    bits_per_symbol = 2 if modulation == "QPSK" else 4
    shape = (active_subcarriers.size, tot_subframes * symbols_per_subframe)
    channel_grids: dict[str, np.ndarray] = {
        "crs": np.zeros(shape, dtype=np.complex128),
        "control": np.zeros(shape, dtype=np.complex128),
        "pss": np.zeros(shape, dtype=np.complex128),
        "sss": np.zeros(shape, dtype=np.complex128),
        "pbch": np.zeros(shape, dtype=np.complex128),
        "pdsch": np.zeros(shape, dtype=np.complex128),
    }
    carrier_to_row = {int(carrier): idx for idx, carrier in enumerate(active_subcarriers.tolist())}
    bit_cursor = 0
    rv = int(args.get("RV", 0))
    transport_schedule = _lte_transport_block_schedule(args)
    transport_total = _lte_transport_block_bits_total(args)
    payload_total = _lte_expected_payload_bits(args)
    use_transport_stream = transport_schedule is not None and transport_total is not None
    use_codeword_bits = not use_transport_stream and bits.size == payload_total

    for subframe_idx in range(tot_subframes):
        subframe_re_count = _lte_payload_re_count(ndlrb, cp, subframe_idx, args)
        subframe_bit_count = subframe_re_count * bits_per_symbol
        if use_transport_stream:
            tb_len = int(transport_schedule[subframe_idx % len(transport_schedule)])
            transport_bits, bit_cursor = _lte_transport_stream_window(bits, bit_cursor, tb_len)
            subframe_bits = _lte_dlsch_encode_transport_block(transport_bits, subframe_bit_count, rv=rv, modulation=modulation)
        elif use_codeword_bits:
            subframe_bits = bits[bit_cursor : bit_cursor + subframe_bit_count]
            bit_cursor += min(subframe_bit_count, max(0, bits.size - bit_cursor))
            if subframe_bits.size < subframe_bit_count:
                subframe_bits = np.concatenate([subframe_bits, np.zeros(subframe_bit_count - subframe_bits.size, dtype=np.int8)])
        else:
            subframe_bits = bits[bit_cursor : bit_cursor + subframe_bit_count]
            bit_cursor += min(subframe_bit_count, max(0, bits.size - bit_cursor))
            if subframe_bits.size < subframe_bit_count:
                subframe_bits = np.concatenate([subframe_bits, np.zeros(subframe_bit_count - subframe_bits.size, dtype=np.int8)])
        subframe_bits = _lte_pdsch_scramble(subframe_bits, subframe_idx)
        subframe_payload_symbols = _modulation_symbols(subframe_bits, modulation)
        payload_cursor = 0
        pcfich_rows = _lte_pcfich_rows(ndlrb)
        pcfich_symbols = _lte_pcfich_symbols(subframe_idx)
        phich_rows = _lte_phich_rows(ndlrb)
        phich_symbols = _lte_phich_symbols(subframe_idx, len(phich_rows) // 3, cp)
        pdcch_regs = _lte_pdcch_available_regs(ndlrb, cp, subframe_idx)
        pdcch_symbols = _lte_pdcch_symbols(args, subframe_idx, len(pdcch_regs))

        for sym_local_idx in range(symbols_per_subframe):
            symbol_idx = subframe_idx * symbols_per_subframe + sym_local_idx
            control_symbol = sym_local_idx < control_symbols
            ref_carriers = set()
            ref_values = np.empty(0, dtype=np.complex128)
            if sym_local_idx in ref_symbols:
                ref_carriers = set(_reference_subcarriers(active_subcarriers, sym_local_idx, cp))
                ref_values = _reference_values(ndlrb, cp, subframe_idx, sym_local_idx)
            ref_index_map = {carrier: idx for idx, carrier in enumerate(sorted(ref_carriers))}
            reserved_values = _lte_reserved_values(sym_local_idx, subframe_idx, active_subcarriers, ref_carriers, args)

            if control_symbol:
                if sym_local_idx == 0:
                    cursor = 0
                    for rows in pcfich_rows:
                        for row_idx in rows:
                            channel_grids["control"][row_idx, symbol_idx] = pcfich_symbols[cursor]
                            cursor += 1
                    cursor = 0
                    for rows in phich_rows:
                        for row_idx in rows:
                            channel_grids["control"][row_idx, symbol_idx] = phich_symbols[cursor]
                            cursor += 1
                cursor = 0
                for reg_sym_local_idx, rows in pdcch_regs:
                    if reg_sym_local_idx != sym_local_idx:
                        cursor += 4
                        continue
                    for row_idx in rows:
                        channel_grids["control"][row_idx, symbol_idx] = pdcch_symbols[cursor]
                        cursor += 1
            else:
                for carrier in active_subcarriers.tolist():
                    carrier_i = int(carrier)
                    row_idx = carrier_to_row[carrier_i]
                    if carrier_i in ref_carriers or carrier_i in reserved_values:
                        continue
                    allowed_rows = _lte_narrow_allowed_rows(ndlrb, cp, sym_local_idx, subframe_idx)
                    if allowed_rows is not None and row_idx not in allowed_rows:
                        continue
                    if payload_cursor < subframe_payload_symbols.size:
                        channel_grids["pdsch"][carrier_to_row[carrier_i], symbol_idx] = subframe_payload_symbols[payload_cursor]
                        payload_cursor += 1

            for carrier in sorted(ref_carriers):
                channel_grids["crs"][carrier_to_row[int(carrier)], symbol_idx] = ref_values[ref_index_map[carrier]]
            for carrier, value in reserved_values.items():
                if carrier in carrier_to_row:
                    row_idx = carrier_to_row[carrier]
                    sss_symbol_idx, pss_symbol_idx = _lte_sync_symbol_indices(cp)
                    if sym_local_idx == sss_symbol_idx:
                        channel_grids["sss"][row_idx, symbol_idx] = value
                    elif sym_local_idx == pss_symbol_idx:
                        channel_grids["pss"][row_idx, symbol_idx] = value
                    else:
                        channel_grids["pbch"][row_idx, symbol_idx] = value

    return channel_grids


def _lte_direct_active_grid(args: dict[str, Any], bits: np.ndarray) -> np.ndarray:
    channel_grids = _lte_direct_channel_grids(args, bits)
    grid_active = np.zeros_like(next(iter(channel_grids.values())))
    for channel_grid in channel_grids.values():
        grid_active += channel_grid
    return grid_active


def _lte_direct_burst(args: dict[str, Any], rng: np.random.Generator, *, apply_power: bool = True) -> GeneratedBurst:
    ndlrb = int(args.get("NDLRB", 6))
    cp = str(args.get("CP", "Normal")).capitalize()
    modulation = str(args.get("modulation", "QPSK")).upper()
    tot_subframes = int(args.get("TotSubframes", 1))
    bandwidth_hz, sample_rate_hz = LTE_PRESET_RATES[ndlrb]
    nfft = LTE_PRESET_NFFT[ndlrb]
    cp_lengths = _cp_lengths(nfft, cp)
    active_subcarriers = _active_subcarriers(ndlrb)
    control_symbols = _lte_control_symbol_count(ndlrb)
    symbols_per_subframe = len(cp_lengths)
    bits = _lte_message_bits(args, rng)
    grid_active = _lte_direct_active_grid(args, bits)
    wave_symbols: list[np.ndarray] = []
    for symbol_idx, cp_len in enumerate(cp_lengths * tot_subframes):
        freq = np.zeros(nfft, dtype=np.complex128)
        for row_idx, carrier in enumerate(active_subcarriers.tolist()):
            freq[_lte_bin(int(carrier), nfft)] = grid_active[row_idx, symbol_idx]
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
