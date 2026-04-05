# Agentic Workflows

This repo uses three layers for reusable agentic work:

- `skills/`: reusable operating procedures
- `agents/`: worker prompts with acceptance metrics
- `flows/`: controller sequences for one larger goal

## Phase Model

For LTE and NR, "finished" means the production runtime synthesizes the waveform from parameters and logic, not from stored MATLAB waveform or grid artifacts.

- `Phase 1`: Direct narrow slice
  - one narrow supported parameter slice
  - runtime is parameter-driven inside that slice
  - oracle fixtures may be used only in compare, debug, or tests
  - no production dependency on stored MATLAB samples, exported grids, or manifest-selected waveform templates
- `Phase 2`: Direct matrix expansion
  - widen one knob at a time from the Phase 1 slice
  - add matrix tooling, matrix tests, and broader compare coverage
  - still no production dependency on stored MATLAB waveform assets
  - oracle fixtures remain compare/debug assets only
- `Phase 3`: Finish and retire shortcuts
  - complete the intended LTE or NR parameter surface
  - close the remaining parity gaps
  - remove any remaining fixture-backed production paths
  - only this phase counts as "finished everything"

## Current Architectural Rule

If the runtime under test loads stored waveform samples, exported MATLAB grids, or template-selected production assets, it is not Phase 3 complete.

It may still be useful as:
- an oracle-backed prototype
- a debug scaffold
- a compare fixture path

But agents must label it explicitly as incomplete.

## What To Modify

### Modify a skill when:

- the commands or file paths have changed
- the workflow is still the same, but the mechanics changed
- a repeated failure mode should become a standard step

Typical edits:
- preferred scripts
- required artifacts
- command order
- troubleshooting notes

### Modify an agent when:

- the worker should stop earlier or later
- the handoff contract is unclear
- the acceptance metrics are too weak or too strict
- the repo now supports a new compare mode or artifact type
- the phase definition changed

Typical edits:
- `Acceptance metrics`
- `Working rules`
- `Stop conditions`
- `Handoff format`

### Modify a flow when:

- the milestone order changes
- a protocol needs a different first narrow target
- a new intermediate checkpoint is required
- the completion definition changes
- one agent should now hand off to a different next agent

Typical edits:
- `Phase 1`
- `Phase 2`
- `Phase 3`
- `Flow`
- `Final milestone`

## Recommended Edit Pattern

1. Tighten the agent first.
2. Then update the flow to use the tightened agent.
3. Update the skill last if the commands or artifact paths changed.

That order keeps controller logic aligned with worker expectations.

## Controller Knobs

When you want agents to "keep going", the main knobs are:

- acceptance thresholds
- explicit retry expectations
- stop conditions
- required artifact list
- phase target

If you want a worker to continue until a metric is met, put that in:
- `Acceptance metrics`
- and repeat it in `Stop conditions`

Do not rely on soft language like "improve" or "get closer". Use a threshold.

## Good Examples In This Repo

- `agents/oracle-compare.md`
  - choose `scene-behavioral`, `atomic-exact`, or `near-exact`
- `agents/parity-debug.md`
  - continue until the selected metric is actually green
- `flows/lte-port.md`
  - phase the work from one direct slice to wider parameter coverage
- `flows/nr5g-port.md`
  - separate oracle-backed compare fixtures from production runtime completion

## How To Add A New Protocol Flow

1. Define the direct-runtime Phase 1 slice.
2. Pick one narrow supported slice only.
3. Preserve runtime parameter semantics inside that slice.
   - unsupported combinations must fail clearly
   - do not silently preset-match in the production path
4. Define the first compare mode:
   - usually `scene-behavioral` first
   - `atomic-exact` only after explicit vectors or templates exist
5. If compare needs explicit vectors or templates, keep them in compare fixtures or tests, not the default runtime path.
6. Add one public config and one test before widening support.
7. Add matrix tooling only after the direct Phase 1 slice exists.
8. Do not call the protocol "finished" until Phase 3 is complete.

## Preferred LTE and NR Pattern

For LTE and NR:

- direct Python logic belongs in the production renderer
- MATLAB-exported samples, grids, templates, and vectors belong only in compare, debug, or tests

Current repo status:
- LTE production runtime is direct for the supported matrix surface: `NDLRB` in `{6,15,25,50,75,100}`, `CP` in `{Normal,Extended}`, `TotSubframes >= 1`, `modulation` in `{QPSK,16QAM}`, with `nPacket=1` and `idleTime=0`
- NR production runtime is direct for the currently supported matrix surface: `control` at `gridSize=50`, `control` FR1 at `gridSize=15`, and the narrow `pdsch 16QAM` profile
- stored LTE/NR waveform templates remain compare/debug artifacts, not production runtime inputs

If the repo temporarily contains an oracle-backed runtime for LTE or NR, agents should treat it as an interim state to remove, not as the completion target.
