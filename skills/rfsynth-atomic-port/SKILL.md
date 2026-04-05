---
name: rfsynth-atomic-port
description: Port one MATLAB atomic generator into the Python-native rfsynth runtime, keep it aligned with the MATLAB object model, and preserve the rule that production waveforms must be generated directly rather than loaded from MATLAB fixtures.
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

## Phase model

- `Phase 1`: one direct narrow slice
- `Phase 2`: direct matrix expansion
- `Phase 3`: finish the intended runtime surface and remove remaining shortcuts

At every phase:
- compare fixtures are allowed
- production waveform fixtures are not

## Default workflow

1. Identify the MATLAB source of truth.
2. Keep the MATLAB object-model split.
3. Create or update one Python atomic under `rfsynth/native/atomic/`.
4. Define the current phase and supported slice up front.
5. Preserve parameter semantics inside that slice.
6. Make unsupported combinations fail clearly.
7. Wire the atomic into `rfsynth/native/atomic/__init__.py`.
8. Add at least one public config if the atomic is meant to be user-visible.
9. Add or extend tests in `tests/test_native_pipeline.py`.
10. If exact parity is realistic, add shared-vector support in compare or test-vector paths only.
11. Run minimum validation:
   - render the new config through the Python-native path
   - run visual verification
   - run oracle compare if MATLAB parity is expected

## Guardrails

- One atomic or one protocol knob expansion per task.
- Prefer direct ports of the MATLAB logic over “similar-looking” approximations.
- Keep short JSON config support stable.
- Do not make the production runtime depend on checked-in oracle waveform, grid, or payload fixtures.
- Do not satisfy a milestone by adding a preset matcher that ignores supported parameters.
- If compare fixtures are needed, keep them isolated to compare, debug, or test-vector helpers.

## Expected outputs

- one new or updated Python atomic file
- registry update
- config coverage
- test coverage
- optional exact-compare vector support
- one clearly documented supported slice
- no default runtime dependency on oracle fixtures

## Answer format

Keep the report concrete:
- what atomic was ported
- what source files were used as the reference
- what config/test files were added or changed
- what phase target was worked
- what supported slice was implemented
- whether it renders
- whether the default runtime depends on fixtures
- whether parity is exact, behavioral, or still open
