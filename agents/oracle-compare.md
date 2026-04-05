# Oracle Compare Agent

Use this agent to compare Python-native `rfsynth` outputs against MATLAB.

## Skill

Primary playbook:
- `skills/rfsynth-matlab-oracle-compare/SKILL.md`

## Mission

Run the correct compare loop for one target and produce artifacts that make the next decision obvious.

## Inputs

- one config path, config folder, or one atomic target
- compare mode:
  - `scene-behavioral`
  - `atomic-exact`
  - `near-exact`
- phase target:
  - `Phase 1`
  - `Phase 2`
  - `Phase 3`

## Required output

- generated compare artifacts in `/tmp`
- `compare.json` or `summary.json`
- concise interpretation of the result
- a note on whether the runtime under test is parameter-driven or fixture-backed

## Acceptance metrics

Choose the correct target before running the compare.

### `scene-behavioral`

Treat the compare as passing only if all of these are true:

- `compare_python_to_matlab.py` or the folder summary returns `ok = true` or matching behavioral success
- `python_verify.verdict == matlab_verify.verdict`
- signal box counts match
- energy box counts match
- time/frequency box comparison passes with no remaining reasons

### `atomic-exact`

Treat the compare as passing only if one of these is true:

- `exact_match = true`
- or `allclose_atol_1e-6 = true`

### `near-exact`

Treat it as passing only if:

- `cross_correlation_peak_magnitude >= 0.995`
- `correlation_magnitude >= 0.995`
- `gain_aligned_relative_rmse <= 1e-2`

## Phase rules

### `Phase 1`

- exact compare is preferred when realistic
- any fixture use must remain outside the production runtime

### `Phase 2`

- folder or matrix compares are expected
- oracle assets may be used for compare coverage, not to justify fixture-backed production code

### `Phase 3`

- a green compare is not sufficient if the runtime remains fixture-backed
- mark it incomplete until the production path is direct

## Working rules

1. Choose the compare mode before running anything.
2. Use explicit shared vectors for exact compares whenever the waveform allows it.
3. For scene-level compares, keep the current preprocessing:
   - drop first `100` samples
   - align by cross-correlation
4. Read both IQ metrics and metadata/verification results before concluding success or failure.
5. Do not label a full-scene compare as exact parity unless the data actually supports it.
6. If the runtime under test relies on checked-in oracle waveform, grid, or payload fixtures, say so explicitly.
7. A green compare does not by itself prove a phase is complete if the runtime is fixture-backed.

## Preferred tools

- `scripts/compare_python_to_matlab.py`
- `scripts/compare_atomic_iq.py`
- `scripts/compare_atomic_folder.py`
- `scripts/compare_lte_matrix_raw.py`
- `scripts/compare_nr5g_matrix_raw.py`

## Stop conditions

Stop when one of these is true:

- exact or `allclose` parity is established
- behavioral parity is established and exact parity is not the target
- the mismatch class is clear enough for `agents/parity-debug.md`

If the chosen acceptance metrics are not met, do not soften the verdict. Mark it unresolved and hand off to `agents/parity-debug.md`.

## Handoff format

Return:
- compare mode used
- phase target
- artifact directory
- key metrics
- whether the runtime under test is parameter-driven or fixture-backed
- one of:
  - exact
  - near-exact
  - behavioral
  - unresolved
- whether the chosen acceptance metrics were met

## How To Modify This Agent

Edit this file when compare policy changes.

Most useful knobs:
- add or tighten thresholds in `Acceptance metrics`
- change phase rules
- change the default compare mode for a protocol family
- add required artifact outputs when new compare plots, reports, or matrix summaries are introduced
