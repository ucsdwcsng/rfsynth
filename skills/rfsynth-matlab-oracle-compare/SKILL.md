---
name: rfsynth-matlab-oracle-compare
description: Compare Python-native rfsynth outputs against the MATLAB oracle, either as full-scene behavioral comparisons or shared-vector exact atomic comparisons, and save metrics plus residual plots.
---

# rfsynth MATLAB Oracle Compare

Use this skill when the task is to compare the Python-native path in `/Users/dineshb/repos/signal-processing/rfsynth` against the MATLAB reference implementation.

## Compare modes

Use the right compare mode first.

- Scene behavioral compare:
  - compare metadata, verification verdicts, aligned IQ summary metrics, and residual plots
  - best for public scene configs and protocol-heavy waveforms
- Atomic exact compare:
  - compare raw bursts driven by explicit shared vectors
  - best for atomics where exact IQ parity is realistic

## Main entrypoints

- One scene:
  - `scripts/compare_python_to_matlab.py`
- Whole atomic folder:
  - `scripts/compare_atomic_folder.py`
- One exact atomic with shared vectors:
  - `scripts/compare_atomic_iq.py`

## Default workflow

1. Choose the compare mode.
2. Use a fixed seed, but do not rely on seed alone for exact parity.
3. For exact parity, generate and use explicit shared vectors.
4. Run MATLAB through the repo helpers, not ad hoc shell snippets.
5. Save outputs to `/tmp` and inspect:
   - `compare.json`
   - `*_compare_time.png`
   - `*_compare_psd.png`
   - `*_compare_spectrogram.png`
6. Read both the IQ metrics and the verification results before concluding anything.

## Current compare behavior

The compare helpers already do this by default:

- drop the first `100` samples
- estimate lag by cross-correlation
- align before computing residual metrics
- plot Python, MATLAB, and residual views

The time compare plots show:
- Python real vs MATLAB real
- Python imag vs MATLAB imag
- real residual
- imag residual

The spectrogram compare plots show:
- Python
- MATLAB
- residual

## Guardrails

- Do not call a full-scene match “exact parity” unless the compare path is shared-vector driven and the metrics justify it.
- Wideband noise and intentionally silent signals are special cases.
- For Bluetooth, WLAN, LTE, or 5G, exact parity usually requires explicit payload/control vectors and protocol-specific framing logic.

## Useful commands

Single scene behavioral compare:

```bash
python3 scripts/compare_python_to_matlab.py \
  configs/synthetic_atomic/am.json \
  --python-out /tmp/rfsynth_python_oracle \
  --matlab-out /tmp/rfsynth_matlab_oracle
```

Whole-folder behavioral compare:

```bash
python3 scripts/compare_atomic_folder.py \
  configs/synthetic_atomic \
  --python-out /tmp/rfsynth_python_atomic_folder \
  --matlab-out /tmp/rfsynth_matlab_atomic_folder \
  --report-out /tmp/rfsynth_atomic_folder_compare
```

Single-atomic exact compare:

```bash
python3 scripts/compare_atomic_iq.py \
  configs/synthetic_atomic/qam.json \
  --out /tmp/rfsynth_atomic_compare
```

## Expected outputs

- saved Python artifacts
- saved MATLAB artifacts
- compare metrics
- residual plots
- one verdict: exact, allclose, behavioral-only, or still divergent

## Answer format

Return:
- compare mode used
- config or folder compared
- key metrics
- where the plots and `compare.json` were written
- whether the result is exact parity, near-exact, behavioral parity, or unresolved
