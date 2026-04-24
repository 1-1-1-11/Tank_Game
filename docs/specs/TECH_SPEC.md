# Tank-Game MVP Technical Spec

## Current Protocol

The judge starts a bot process and sends one JSON state per line through standard input. The bot prints one action and flushes standard output.

Allowed actions:

- `UP`
- `DOWN`
- `LEFT`
- `RIGHT`

The public interface remains:

```python
class TankAI:
    def get_action(self, state):
        ...
```

## Current Decision Pipeline

The current `xjy.py` behavior can be described as:

```text
state
-> revive/death state handling
-> static map cache update
-> enumerate four directions
-> reject invalid moves
-> score bullet danger
-> score trap survival depth
-> score normal tactics
-> choose highest score
-> fallback if every move is invalid
-> return action
```

Normal tactical scoring includes mobility, center distance, aim bonus, enemy collision penalty, and direction continuity.

## Target Module Structure

```text
src/
|-- bots/
|   `-- xjy.py
`-- tank_ai/
    |-- __init__.py
    |-- constants.py
    |-- state.py
    |-- rules.py
    |-- danger.py
    |-- mobility.py
    |-- traps.py
    `-- scoring.py
```

Responsibilities:

- `constants.py`: directions, opposite directions, score constants, scoring weights.
- `state.py`: state normalization helpers such as wall sets and enemy positions.
- `rules.py`: movement validity, boundary checks, wall checks, reverse-move checks.
- `danger.py`: bullet-hit prediction.
- `mobility.py`: BFS mobility scoring.
- `traps.py`: DFS survival-depth search.
- `scoring.py`: candidate action scoring and best-action selection support.
- `bots/xjy.py`: judge I/O, `TankAI` state, module orchestration.

## Data Flow

```text
state
-> state helpers
-> rules/danger/mobility/traps
-> scoring
-> action
```

The MVP does not introduce a new wire schema. The judge-facing JSON state remains unchanged.

## Compatibility Rules

- `TankAI.get_action(state)` must remain callable without additional arguments.
- Script execution must still work when running `src/bots/xjy.py` directly.
- Any extracted helper must preserve the original direction order: `UP`, `DOWN`, `LEFT`, `RIGHT`.
- Candidate sorting must remain score-descending and stable for equal scores.
- Exceptions in `get_action` still fall back to `UP`.

## Regression Strategy

The first refactor should preserve behavior on fixed mock states. If behavior changes, the change must be documented as intentional and moved out of MVP scope unless it is required to fix a clear bug.

