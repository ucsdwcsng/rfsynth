---
name: rfsynth-atomic-port
description: Port one MATLAB atomic generator into the Python-native rfsynth runtime, wire it into the MATLAB-mirror object model, add config coverage, and leave it ready for oracle comparison and regression.
---

# rfsynth Atomic Port

Use this skill when the task is to add one new Python-native atomic signal to `/Users/dineshb/repos/signal-processing/rfsynth` and keep the implementation aligned with the MATLAB design.

## Scope

- Runtime model:
  - `rfsynth/native/core.py`
  - `rfsynth/native/scene.py`
  - `rfsynth/native/atomic/__init__.py`
- Python atomics:
  - `rfsynth/native/atomic/*.py`
- MATLAB references:
  - `matlab/lib/+atomic/*.m`
- Richer upstream references when needed:
  - `/Users/dineshb/repos/signal-processing/rfsynth-python/modules/SignalGenerator/lib/+atomic/*.m`
- Configs:
  - `configs/synthetic_atomic/*.json`
- Tests:
  - `tests/test_native_pipeline.py`

## Default workflow

1. Identify the MATLAB source of truth.
   - Start with `matlab/lib/+atomic/<Name>.m`.
   - If the current repo has a narrowed or older version, check the richer upstream source in `rfsynth-python/modules/SignalGenerator/lib/+atomic/`.
2. Keep the MATLAB object-model split.
   - `Signal` owns burst generation and metadata.
   - `Source` owns source-level effects.
   - `VirtualSignalEngine` owns scene assembly and artifact writing.
   - Do not reintroduce a flat waveform-dispatch design.
3. Create one Python file per atomic under `rfsynth/native/atomic/`.
   - Subclass the Python `Signal` base.
   - Implement `generate_transmission(self, scene, rng)`.
   - Return a `GeneratedBurst` with `samples`, `sample_rate_hz`, `bandwidth_hz`, `protocol`, `modality`, `modulation`, and any useful `extras`.
4. Wire the atomic into `rfsynth/native/atomic/__init__.py`.
5. Add at least one public config in `configs/synthetic_atomic/` if the atomic is meant to be user-visible.
6. Add or extend tests in `tests/test_native_pipeline.py`.
7. If exact parity is realistic, add shared-vector support in:
   - `rfsynth/native/atomic_compare.py`
   - `matlab/examples/run_atomic_test_vector.m`
   - any MATLAB helper needed to accept explicit vectors
8. Run the minimum validation:
   - render the new config through the Python-native path
   - run visual verification
   - run oracle compare if MATLAB parity is expected

## Guardrails

- One atomic per task. Do not mix multiple new protocols in the same port unless the user explicitly asks for it.
- Prefer direct ports of the MATLAB logic over “similar-looking” approximations.
- For standards-heavy protocols, do not assume behavioral parity is enough if the current work is parity-focused.
- Keep short JSON config support stable. The user-facing interface remains JSON-first even though the internals mirror MATLAB.

## Good targets for this skill

- Adding `LTE_DL_FDD` from `/Users/dineshb/repos/signal-processing/rfsynth-python/modules/SignalGenerator/lib/+atomic/LTE_DL_FDD.m`
- Adding `nr5g` from `/Users/dineshb/repos/signal-processing/rfsynth-python/modules/SignalGenerator/lib/+atomic/nr5g.m`
- Porting a generic modulation family from `matlab/lib/+atomic/`

## Expected outputs

- one new Python atomic file
- registry update
- config coverage
- test coverage
- optional exact-compare vector support

## Answer format

Keep the report concrete:
- what atomic was ported
- what source files were used as the reference
- what config/test files were added or changed
- whether it renders
- whether parity is exact, behavioral, or still open
