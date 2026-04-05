---
name: rfsynth-matlab-oracle-compare
description: Compare Python-native rfsynth outputs against the MATLAB oracle as either full-scene behavioral checks or exact raw-burst checks, while keeping oracle fixtures out of the production runtime.
---

# rfsynth MATLAB Oracle Compare

Use this skill when the task is to compare the Python-native path in `/Users/dineshb/repos/signal-processing/rfsynth` against the MATLAB reference implementation.

## Compare modes

- Scene behavioral compare
- Atomic exact compare
- Near-exact compare when explicitly allowed

## Main entrypoints

- One scene:
  - `scripts/compare_python_to_matlab.py`
- Whole atomic folder:
  - `scripts/compare_atomic_folder.py`
- One exact atomic with shared vectors:
  - `scripts/compare_atomic_iq.py`
- LTE raw matrix compare:
  - `scripts/compare_lte_matrix_raw.py`
- NR raw matrix compare:
  - `scripts/compare_nr5g_matrix_raw.py`

## Default workflow

1. Choose the compare mode.
2. Use a fixed seed, but do not rely on seed alone for exact parity.
3. For exact parity, generate and use explicit shared vectors.
4. Run MATLAB through the repo helpers, not ad hoc shell snippets.
5. Save outputs to `/tmp`.
6. Read both IQ metrics and verification results before concluding anything.
7. State whether the runtime under test is parameter-driven or fixture-backed.

## Guardrails

- Do not call a full-scene match “exact parity” unless the compare path is shared-vector driven and the metrics justify it.
- Wideband noise and intentionally silent signals are special cases.
- For Bluetooth, WLAN, LTE, or 5G, exact parity usually requires explicit payload/control vectors and protocol-specific framing logic.
- Exported templates or vectors are valid compare fixtures, not proof that a fixture-backed production renderer is acceptable.
- If the runtime under test is fixture-backed, say so explicitly even when the compare metrics are green.

## Useful commands

Use the project venv when Python dependencies matter:

```bash
/Users/dineshb/repos/signal-processing/rfsynth-python/.venv/bin/python \
  scripts/compare_python_to_matlab.py configs/synthetic_atomic/am.json
```

```bash
/Users/dineshb/repos/signal-processing/rfsynth-python/.venv/bin/python \
  scripts/compare_atomic_iq.py configs/synthetic_atomic/qam.json
```

```bash
/Users/dineshb/repos/signal-processing/rfsynth-python/.venv/bin/python \
  scripts/compare_lte_matrix_raw.py /tmp/rfsynth_lte_dl_fdd_matrix/configs
```

```bash
/Users/dineshb/repos/signal-processing/rfsynth-python/.venv/bin/python \
  scripts/compare_nr5g_matrix_raw.py /tmp/rfsynth_nr5g_matrix/configs
```

## Expected outputs

- saved Python artifacts
- saved MATLAB artifacts
- compare metrics
- residual plots
- whether the runtime under test is parameter-driven or fixture-backed
- one verdict: exact, allclose, behavioral-only, or still divergent

## Answer format

Return:
- compare mode used
- config, folder, or matrix compared
- key metrics
- where the plots and summary files were written
- whether the runtime under test is parameter-driven or fixture-backed
- whether the result is exact parity, near-exact, behavioral parity, or unresolved
