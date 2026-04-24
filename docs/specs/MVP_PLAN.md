# Tank-Game MVP Plan

## Principle

The MVP is a structure-first refactor. It should make future work easier without trying to make the bot smarter in the same step.

## Step 1: Document Current Behavior

Allowed:

- Add PRD, technical spec, MVP plan, and AI Coding guide.
- Describe current behavior and module boundaries.

Not allowed:

- Change strategy behavior.
- Change judge protocol.

Acceptance:

- `docs/specs/` contains the four MVP documents.

## Step 2: Extract Constants and Rules

Allowed:

- Move direction constants and scoring constants to `tank_ai/constants.py`.
- Move boundary, wall, and reverse checks to `tank_ai/rules.py`.

Not allowed:

- Change direction order.
- Change score values.

Acceptance:

- `xjy.py` imports constants/rules from `tank_ai`.
- Rule tests cover valid move, wall collision, boundary collision, and reverse move.

## Step 3: Extract Danger and Movement Analysis

Allowed:

- Move bullet-hit prediction to `danger.py`.
- Move BFS mobility scoring to `mobility.py`.
- Move DFS survival-depth search to `traps.py`.

Not allowed:

- Change bullet movement semantics.
- Change DFS depth thresholds from the caller.

Acceptance:

- Tests cover bullet two-step hit, wall-blocked bullet, mobility, and trap depth.

## Step 4: Extract Scoring

Allowed:

- Move candidate scoring into `scoring.py`.
- Keep `TankAI` responsible for state cache and final action assignment.

Not allowed:

- Tune scoring weights.
- Add new strategy modes.

Acceptance:

- Fixed mock-state behavior remains stable.
- `xjy.py` becomes orchestration code rather than a large strategy implementation.

## Step 5: Verify and Commit

Run:

```powershell
py -m py_compile .\src\bots\xjy.py .\src\bots\xjy1v1.py
Get-ChildItem .\src\tank_ai\*.py | ForEach-Object { py -m py_compile $_.FullName }
pytest
```

If `pytest` is missing, install it or record the blocker before continuing.

## AI Coding Handoff

Future prompts should ask for one small step at a time. Example:

> Extract danger-map logic only. Do not change score constants or final action selection. Add tests for bullet speed and wall blocking.
