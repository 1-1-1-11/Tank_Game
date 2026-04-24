# Tank-Game AI Coding Guide

## Default Workflow

1. Read `docs/specs/PRD.md` and `docs/specs/TECH_SPEC.md`.
2. Check `git status --short`.
3. Inspect the target module before editing.
4. Make one bounded change.
5. Run syntax checks and relevant tests.
6. Summarize behavior impact.

## Required Checks

Before code changes:

```powershell
git status --short
```

After Python changes:

```powershell
py -m py_compile .\src\bots\xjy.py .\src\bots\xjy1v1.py
Get-ChildItem .\src\tank_ai\*.py | ForEach-Object { py -m py_compile $_.FullName }
pytest
```

After config changes:

```powershell
Get-Content -Raw .\config.json | ConvertFrom-Json | Out-Null
Get-Content -Raw .\config_1v1.json | ConvertFrom-Json | Out-Null
```

## Rules for AI Coding

- Do not rewrite the whole bot in one pass.
- Do not change score constants unless the task explicitly asks for tuning.
- Do not replace rule-based logic with machine learning in this MVP.
- Do not change judge-facing input/output.
- Do not depend on ignored archive files in public configs.
- Do not edit root `README.md` unless explicitly requested.
- When rebuilding the executable, use `pyinstaller --onefile --clean --paths .\src .\src\bots\xjy.py` so `tank_ai` modules are discoverable.

## Behavior Preservation

When refactoring, preserve:

- Direction order: `UP`, `DOWN`, `LEFT`, `RIGHT`.
- Reverse-move rule.
- Bullet two-step hit prediction.
- Wall blocking in bullet prediction.
- DFS survival-depth scoring.
- BFS mobility scoring.
- Aim bonus and continuity bonus.
- Exception fallback to `UP`.

## Good Future Prompts

- "Extract only the mobility logic into `tank_ai/mobility.py` and add tests. Preserve behavior."
- "Add batch match evaluation as a new script. Do not change bot strategy."
- "Add replay logging behind an optional flag. Do not change judge protocol."

## Bad Future Prompts

- "Make the bot smarter."
- "Refactor everything."
- "Use AI to improve it."
- "Clean the code and optimize it."

These are too broad and likely to cause behavior drift.
