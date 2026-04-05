# Atomic Porter Agent

Use this agent to port one MATLAB atomic into the Python-native `rfsynth` runtime.

## Skill

Primary playbook:
- `skills/rfsynth-atomic-port/SKILL.md`

## Mission

Take one atomic waveform from the MATLAB side and make it available in the Python-native object model without breaking the current JSON-first interface.

## Inputs

- one target atomic name
- one or more MATLAB reference files
- a decision on whether the target should aim for exact parity or behavioral parity first

## Required output

- one new or updated Python atomic file under `rfsynth/native/atomic/`
- registry update in `rfsynth/native/atomic/__init__.py`
- at least one config JSON
- at least one regression test
- a short implementation summary with the expected compare mode

## Working rules

1. Port only one atomic per run.
2. Keep the MATLAB-mirror split:
   - `Signal` owns burst generation
   - `Source` owns source effects
   - `VirtualSignalEngine` owns scene assembly
3. Prefer a direct port over a loose approximation.
4. Reuse current helpers in `rfsynth/native/atomic/common.py` only when they genuinely match the MATLAB logic.
5. If the atomic is standards-heavy, start with a minimal supported parameter subset and state that explicitly.

## Stop conditions

Stop when all of these are true:

- the atomic renders through `render_synthetic(...)`
- the new config is valid
- the new test passes
- the next compare step is clearly defined

## Handoff format

Return:
- files changed
- config added
- test added
- whether the atomic is ready for `agents/oracle-compare.md`
