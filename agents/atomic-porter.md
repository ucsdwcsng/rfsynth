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
- one declared phase target:
  - `Phase 1`: direct narrow slice
  - `Phase 2`: direct matrix expansion
  - `Phase 3`: finish and remove remaining shortcuts
- one explicitly declared supported parameter slice for the current phase

## Required output

- one new or updated Python atomic file under `rfsynth/native/atomic/`
- registry update in `rfsynth/native/atomic/__init__.py`
- at least one config JSON
- at least one regression test
- a short implementation summary with the expected compare mode
- a short statement of the supported slice and the runtime-versus-fixture boundary

## Acceptance metrics

Do not hand off the atomic as "ported" unless all applicable metrics below are met.

- Config validation:
  - the new config passes `scripts/check_configs.py`
- Renderability:
  - `render_synthetic(...)` completes without error
  - IQ output is non-empty
  - metadata and scoring files are written
- Runtime semantics:
  - supported signal arguments affect runtime behavior inside the declared slice
  - unsupported combinations fail clearly
- Architecture:
  - production rendering must not load stored MATLAB waveform samples
  - production rendering must not load exported MATLAB grids or templates as waveform sources
  - compare fixtures may exist only in compare, test-vector, or debug helpers
- Local signal sanity:
  - signal count is at least `1`
  - the new atomic does not produce `Visual fail` in the normal synthetic path unless it is intentionally silent
- Test coverage:
  - at least one targeted unit test for the atomic passes
- Handoff readiness:
  - the next compare mode is explicitly chosen:
    - `scene-behavioral`
    - `atomic-exact`
    - or `near-exact`

## Phase expectations

### `Phase 1`

- one direct narrow slice only
- no production fixture dependence

### `Phase 2`

- widen one knob at a time from the direct slice
- add matrix tooling and matrix tests when useful
- still no production fixture dependence

### `Phase 3`

- complete the intended production parameter surface
- remove any remaining temporary shortcut paths

## Working rules

1. Port only one atomic or one protocol knob expansion per run.
2. Keep the MATLAB-mirror split:
   - `Signal` owns burst generation
   - `Source` owns source effects
   - `VirtualSignalEngine` owns scene assembly
3. Prefer a direct port over a loose approximation.
4. Reuse current helpers in `rfsynth/native/atomic/common.py` only when they genuinely match the MATLAB logic.
5. If the atomic is standards-heavy, start with a minimal supported parameter subset and state that explicitly.
6. Do not satisfy any phase by adding a preset matcher or checked-in waveform-template loader to the production renderer.
7. Shared vectors, exported templates, and oracle payloads belong in compare or test harnesses unless the user explicitly asks for a fixture-backed prototype.

## Stop conditions

Stop when all of these are true:

- the atomic renders through `render_synthetic(...)`
- the new config is valid
- the new test passes
- the next compare step is clearly defined
- the supported slice is explicitly documented
- the default runtime path is parameter-driven inside that slice
- the acceptance metrics above are met

If the acceptance metrics are not met, keep iterating locally. Do not hand off a half-ported or fixture-backed atomic as "done".

## Handoff format

Return:
- files changed
- config added
- test added
- phase target
- supported slice
- whether the runtime path is parameter-driven or fixture-backed
- whether the atomic is ready for `agents/oracle-compare.md`
- which acceptance metrics were met

## How To Modify This Agent

Edit this file when the definition of "ported" changes.

Most useful knobs:
- add or tighten `Acceptance metrics`
- change phase expectations
- require a different compare mode in `Handoff readiness`
- add protocol-specific constraints to `Working rules`
