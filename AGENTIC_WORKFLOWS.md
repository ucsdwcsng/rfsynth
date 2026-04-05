# Agentic Workflows

This repo uses three layers for reusable agentic work:

- `skills/`: reusable operating procedures
- `agents/`: worker prompts with acceptance metrics
- `flows/`: controller sequences for one larger goal

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

Typical edits:
- `Acceptance metrics`
- `Working rules`
- `Stop conditions`
- `Handoff format`

### Modify a flow when:

- the milestone order changes
- a protocol needs a different first narrow target
- a new intermediate checkpoint is required
- one agent should now hand off to a different next agent

Typical edits:
- `Recommended first supported subset`
- `Flow`
- `Acceptance`
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

If you want a worker to continue until a metric is met, put that in:
- `Acceptance metrics`
- and repeat it in `Stop conditions`

Do not rely on soft language like "improve" or "get closer". Use a threshold.

## Good Examples In This Repo

- `agents/oracle-compare.md`
  - choose `scene-behavioral`, `atomic-exact`, or `near-exact`
- `agents/parity-debug.md`
  - continue until the selected metric is actually green
- `flows/nr5g-port.md`
  - start with one narrow preset, then widen only after parity closes

## How To Add A New Protocol Flow

1. Copy the closest existing flow from `flows/`.
2. Pick one narrow preset only.
3. Define the first compare mode:
   - usually `scene-behavioral` first
   - `atomic-exact` only after explicit vectors or templates exist
4. Add one public config and one test before widening support.
5. Add exact or near-exact thresholds only when the waveform generation path really allows them.

## Current NR Pattern

The `nr5g` path now uses a mixed strategy:

- direct Python logic for narrow control-style presets
- oracle-backed grid templates for exact narrow presets such as FR1 and PDSCH 16QAM

If you want to extend NR next, prefer:

1. export one new narrow template
2. add one new public config
3. add one test
4. validate raw compare
5. validate scene compare
6. rerun the public suite
