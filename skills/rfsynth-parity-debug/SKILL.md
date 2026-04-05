---
name: rfsynth-parity-debug
description: Debug Python-versus-MATLAB parity failures in rfsynth by reading residual plots and metrics, isolating the mismatch source, patching one cause at a time, and rerunning the right compare loop.
---

# rfsynth Parity Debug

Use this skill when the Python-native implementation exists but still diverges from MATLAB and the task is to close the gap methodically.

## Inputs

Typical starting points:

- `compare.json`
- `*_compare_time.png`
- `*_compare_psd.png`
- `*_compare_spectrogram.png`

These usually come from:
- `scripts/compare_atomic_iq.py`
- `scripts/compare_atomic_folder.py`
- `scripts/compare_python_to_matlab.py`

## Debug workflow

1. Start from the strongest failing compare artifact, not from the code alone.
2. Classify the mismatch:
   - payload randomness mismatch
   - lag or burst-boundary mismatch
   - amplitude or normalization mismatch
   - pulse-shaping / filtering mismatch
   - framing / preamble / interleaver / coding mismatch
   - source-level effect mismatch
3. Prefer raw atomic compare before full-scene compare.
4. If the signal is standards-heavy, debug by field or stage.
   - WLAN: use `scripts/compare_wlan_fields.py` and `matlab/examples/export_wlan_field_artifacts.m`
   - BLE: use explicit packet/control vectors and parameter sweeps
5. Patch one cause at a time.
6. Rerun the smallest useful compare first.
7. Only after the raw compare improves, rerun the full-scene compare.

## Reading the plots

- Real/imag overlays:
  - good for lag, sign, scaling, and burst-boundary issues
- Residual real/imag:
  - good for spotting short boundary windows, CP mismatches, and symbol slips
- PSD residual:
  - good for occupied-band mismatch, pilot layout mismatch, or filter mismatch
- Spectrogram residual:
  - good for timing drift, packet framing mismatch, or frequency placement mistakes

## Good stopping rules

Stop when one of these is true:

- `exact_match = true`
- `allclose_atol_1e-6 = true`
- or the user has explicitly accepted behavioral parity and the remaining residual is explained

## Guardrails

- Do not chase full-scene exact parity first when a raw shared-vector compare is available.
- Do not change the compare preprocessing casually. The default drop-100 and cross-correlation alignment are part of the current workflow.
- Do not treat seed matching as proof of payload matching.

## Common examples

- WLAN:
  - interleaver direction
  - pilot polarity offset
  - scrambler taps
  - preamble sign pattern
  - default packet windowing
- BLE:
  - access address bit order
  - whitening
  - modulation index
  - pulse length
  - coded-phy or CTE framing details

## Answer format

Keep the report focused:
- mismatch class
- files patched
- compare rerun used
- before/after metrics
- what still remains, if anything
