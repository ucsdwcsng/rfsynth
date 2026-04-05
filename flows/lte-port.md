# LTE Port Flow

Use this flow to add and finish `LTE_DL_FDD` in the Python-native `rfsynth` path without confusing compare fixtures with production completion.

## Target

Reference source:
- `/Users/dineshb/repos/signal-processing/rfsynth-python/modules/SignalGenerator/lib/+atomic/LTE_DL_FDD.m`

## Definition of done

For LTE, "finished" means the production runtime synthesizes the waveform from parameters and logic.

These do not count as final completion:
- manifest-selected stored waveform samples
- production loading of exported MATLAB waveform templates
- production loading of exported MATLAB payload or grid artifacts

Those are allowed only in compare, debug, or test harnesses.

## Phase 1

Direct narrow slice only:
- `NDLRB = 6`
- `CP = Normal`
- `TotSubframes = 1`
- `modulation = QPSK`
- `nPacket = 1`
- `idleTime = 0`
- one public config at `centerFreq_Hz = 763000000`
- explicit `messagePath` only for compare or test-vector work

Acceptance:
- one direct runtime slice renders
- unsupported combinations fail clearly
- one raw compare exists
- one scene compare exists
- no production fixture dependence

## Phase 2

Direct matrix expansion:
- widen one knob at a time from the Phase 1 slice
- add matrix tooling only after the direct slice exists
- widen coverage for:
  - `NDLRB`
  - `TotSubframes`
  - `CP`
  - `modulation`
  - center-frequency presets

Acceptance:
- widened coverage remains direct-runtime, not fixture-backed
- matrix tooling and matrix tests are green
- compare coverage expands with the runtime

## Phase 3

Finish LTE:
- complete the intended LTE parameter surface
- remove any remaining shortcut or fixture-backed runtime dependency
- keep oracle vectors or templates only in compare/debug/tests

Acceptance:
- production runtime is fully parameter-driven for the declared LTE surface
- regression suite remains green
- compare coverage is sufficient for the widened surface

## Current status rule

If the repo contains an interim oracle-backed LTE runtime, treat it as incomplete and keep working toward Phase 3.

Current repo status:
- the supported LTE matrix surface is already direct in production runtime
- matrix tests enforce direct rendering across the generated LTE matrix
- stored LTE waveform/template assets remain compare/debug artifacts only

## Flow

### 1. Port

Agent:
- `agents/atomic-porter.md`

Tasks:
- create or update `rfsynth/native/atomic/lte_dl_fdd.py`
- register it in `rfsynth/native/atomic/__init__.py`
- add `configs/synthetic_atomic/lte_dl_fdd.json`
- add render coverage in `tests/test_native_pipeline.py`
- reject unsupported LTE combinations clearly
- keep compare fixtures out of the production renderer

### 2. Oracle compare

Agent:
- `agents/oracle-compare.md`

Preferred compare path:
- raw shared-vector LTE burst compare using explicit message bits
- then scene-level compare
- for wider coverage, use matrix compare tooling

### 3. Parity debug

Agent:
- `agents/parity-debug.md`

Likely mismatch classes:
- resource-grid mapping
- control/data placement
- reference signals
- cyclic prefix handling
- OFDM symbol ordering
- normalization or windowing
- message/vector mismatch
- hidden preset matching or fixture dependence

### 4. Regression

Agent:
- `agents/regression.md`

Tasks:
- run config checks
- run unit tests with the repo venv
- run the public synthetic suite
- run matrix tests when LTE matrix tooling changed

## Final milestone

Call LTE finished only when all of these are true:

- Phase 1 is complete
- Phase 2 is complete
- Phase 3 is complete
- the default runtime does not depend on stored MATLAB waveform, grid, or payload fixtures

## Suggested Controller Prompt

Use this flow with:

- `agents/atomic-porter.md`
- `agents/oracle-compare.md`
- `agents/parity-debug.md`
- `agents/regression.md`

Suggested instruction:

`Advance LTE toward Phase 3. Keep the production runtime direct and parameter-driven. Oracle vectors or templates may be used only in compare, debug, or tests. Use atomic-porter -> oracle-compare -> parity-debug -> regression, and do not mark LTE finished until all three phases are satisfied.`
