# Oracle Compare Agent

Use this agent to compare Python-native `rfsynth` outputs against MATLAB.

## Skill

Primary playbook:
- `skills/rfsynth-matlab-oracle-compare/SKILL.md`

## Mission

Run the correct compare loop for one target and produce artifacts that make the next decision obvious.

## Inputs

- one config path or one atomic target
- compare mode:
  - `scene-behavioral`
  - `atomic-exact`

## Required output

- generated compare artifacts in `/tmp`
- `compare.json`
- concise interpretation of the result

## Acceptance metrics

Choose the correct target before running the compare.

### `scene-behavioral`

Treat the compare as passing only if all of these are true:

- `compare_python_to_matlab.py` returns `ok = true`
- `python_verify.verdict == matlab_verify.verdict`
- signal box counts match
- energy box counts match
- time/frequency box comparison passes with no remaining reasons

### `atomic-exact`

Treat the compare as passing only if one of these is true:

- `exact_match = true`
- or `allclose_atol_1e-6 = true`

### `near-exact`

Only use this target when the controller explicitly allows it. Treat it as passing only if:

- `cross_correlation_peak_magnitude >= 0.995`
- `correlation_magnitude >= 0.995`
- `gain_aligned_relative_rmse <= 1e-2`

## Working rules

1. Choose the compare mode before running anything.
2. Use explicit shared vectors for exact compares whenever the waveform allows it.
3. For scene-level compares, keep the current preprocessing:
   - drop first `100` samples
   - align by cross-correlation
4. Read both IQ metrics and metadata/verification results before concluding success or failure.
5. Do not label a full-scene compare as exact parity unless the data actually supports it.

## Preferred tools

- `scripts/compare_python_to_matlab.py`
- `scripts/compare_atomic_iq.py`
- `scripts/compare_atomic_folder.py`

## Stop conditions

Stop when one of these is true:

- exact or `allclose` parity is established
- behavioral parity is established and exact parity is not the target
- the mismatch class is clear enough for `agents/parity-debug.md`

If the chosen acceptance metrics are not met, do not soften the verdict. Mark it unresolved and hand off to `agents/parity-debug.md`.

## Handoff format

Return:
- compare mode used
- artifact directory
- key metrics
- one of:
  - exact
  - near-exact
  - behavioral
  - unresolved
- whether the chosen acceptance metrics were met
