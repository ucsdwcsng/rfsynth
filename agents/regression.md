# Regression Agent

Use this agent to guard the public Python-native synthetic path after a port or parity fix.

## Skill

Primary playbook:
- `skills/rfsynth-scene-regression/SKILL.md`

## Mission

Run the repo’s public synthetic checks and report whether the branch is still healthy.

## Inputs

- current branch state
- optional narrowed config set if the controller wants a smaller sweep

## Required output

- config validation result
- unit test result
- suite result
- list of regressions, if any

## Working rules

1. Run config validation first.
2. Run the Python-native unit tests second.
3. Run the public suite third.
4. If a config regresses, inspect its artifact bundle before summarizing.
5. If the change was parity-driven and the suite is green, hand off cleanly; do not start parity debugging on your own unless explicitly asked.

## Preferred tools

- `scripts/check_configs.py`
- `python3 -m unittest tests.test_native_pipeline`
- `scripts/run_python_native_suite.py`

## Stop conditions

Stop when:

- the branch is green
- or a clear regression list is produced

## Handoff format

Return:
- pass/fail for config check
- pass/fail for unit tests
- config count swept
- failing or inconclusive configs
- summary artifact path
