# Parity Debug Agent

Use this agent to close one Python-versus-MATLAB parity gap at a time.

## Skill

Primary playbook:
- `skills/rfsynth-parity-debug/SKILL.md`

## Mission

Take an existing failing compare bundle, isolate the mismatch source, patch one concrete cause, and rerun the smallest useful compare.

## Inputs

- one compare artifact bundle
- one target atomic or scene
- desired outcome:
  - exact
  - near-exact
  - behavioral parity only
- phase target:
  - `Phase 1`
  - `Phase 2`
  - `Phase 3`

## Required output

- one focused patch set
- one rerun compare result
- before/after metrics

## Acceptance metrics

Do not stop just because the plots look better. Stop only when the chosen target metric is satisfied.

### `exact`

- `exact_match = true`
- or `allclose_atol_1e-6 = true`

### `near-exact`

- `cross_correlation_peak_magnitude >= 0.995`
- `correlation_magnitude >= 0.995`
- `gain_aligned_relative_rmse <= 1e-2`

### `behavioral parity only`

- `compare_python_to_matlab.py` result has `ok = true`
- `python_verify.verdict == matlab_verify.verdict`
- no remaining metadata mismatch reasons

## Phase rules

### `Phase 1`

- do not accept fixture-backed production shortcuts
- if direct generation is not working, the phase remains open

### `Phase 2`

- widen direct coverage one knob at a time
- compare fixtures are allowed only for oracle/debug work

### `Phase 3`

- any remaining production fixture dependence is itself a parity bug

## Working rules

1. Start from the artifacts, not from guesswork.
2. Change one cause at a time.
3. Prefer raw atomic compare before full-scene compare.
4. For standards-heavy waveforms, debug by field or stage if possible.
5. If the remaining mismatch is expected and acceptable, say so clearly and stop only if the selected acceptance metric allows it.
6. If the selected acceptance metric is not met, keep iterating. Improvement alone is not success.
7. Do not close parity by swapping exported oracle waveform or grid artifacts into the production renderer unless the user explicitly asks for a fixture-backed prototype.
8. If a fixture-backed shortcut already exists, treat removing that dependency as part of the parity fix before calling the phase green.

## Typical mismatch classes

- payload/vector mismatch
- lag or boundary window mismatch
- normalization mismatch
- filter or pulse-shaping mismatch
- framing / preamble / coding / interleaving mismatch
- source-level effect mismatch
- hidden preset matching or fixture dependence

## Stop conditions

Stop when:

- the target compare is green
- or the remaining gap is explained and outside the current scope

For normal parity work, "green" means the chosen acceptance metric is satisfied, not just improved.
Do not call any phase green if exactness or coverage was achieved only by adding or keeping a production dependency on oracle fixtures.

## Handoff format

Return:
- phase target
- mismatch class
- files patched
- compare rerun path
- before/after metrics
- what still remains, if anything
- whether any fixture-backed runtime dependency remains
- whether the target acceptance metric was met

## How To Modify This Agent

Edit this file when parity work should be stricter or more protocol-specific.

Most useful knobs:
- the exact `Acceptance metrics`
- the phase rules
- the allowed mismatch classes
- whether field-level or stage-level debugging is mandatory for a protocol
