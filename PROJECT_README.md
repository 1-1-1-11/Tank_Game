# Y. L. Tank Game Bot

This project is a rule-based Python bot for the Y. L. Tank Game competition. It is not a machine-learning system or a full game engine. The core work is real-time decision making under a fixed judge protocol: each turn receives the current map, tanks, walls, and bullets, then returns one move direction.

The repository is organized for portfolio review while still keeping local historical material. Source code and curated runtime files are tracked by Git. Old build outputs and historical opponent executables are kept locally under `archive/old_build_outputs/`, but they are intentionally ignored and are not part of the public repository.

## Project Positioning

- Type: rule-based tank battle bot
- Language: Python
- Focus: state evaluation, bullet avoidance, trap detection, fire-line checks, Pro rule handling
- Good for showing: algorithmic modeling, heuristic search, competition strategy iteration, project cleanup

## Repository Structure

```text
.
|-- README.md
|-- PROJECT_README.md
|-- config.json
|-- config_1v1.json
|-- src/
|   |-- bots/
|   |   |-- xjy.py
|   |   |-- xjy1v1.py
|   |   `-- demo/
|   `-- archive_versions/
|-- bin/
|   |-- judges/
|   `-- final_bots/
|-- docs/
|   |-- images/
|   `-- XJY.pptx
`-- archive/
```

## Main Files

- `src/bots/xjy.py`: main bot source.
- `src/bots/xjy1v1.py`: 1v1 strategy version.
- `src/tank_ai/`: extracted rule, danger, mobility, trap, and scoring helpers used by the main bot.
- `src/bots/demo/`: small demo bots used by the public sample configs.
- `bin/final_bots/xjy.exe`: packaged main bot.
- `bin/judges/judge.exe`: standard judge.
- `bin/judges/judge_pro.exe`: Pro-rule judge.
- `bin/judges/judge_1v1_final_10.exe`: retained final 1v1 judge.
- `src/archive_versions/`: historical Python strategy versions.
- `archive/old_build_outputs/`: local-only old PyInstaller outputs and opponent executables. This folder is ignored by Git.

## Specs

The MVP refactor is documented under `docs/specs/`:

- `PRD.md`: product goals, audience, MVP boundaries, and non-goals.
- `TECH_SPEC.md`: current protocol, decision pipeline, and module responsibilities.
- `MVP_PLAN.md`: implementation steps and acceptance criteria.
- `AI_CODING_GUIDE.md`: rules for future AI-assisted development.

## Configs

- `config.json`: public, GitHub-friendly sample config. It only points to tracked files.
- `config_1v1.json`: public, GitHub-friendly 1v1 sample config.
- `config.local.json`: local full-match config for archived opponent executables. Ignored by Git.
- `config_1v1.local.json`: local 1v1 config for archived opponent executables. Ignored by Git.

Use the public configs when cloning or reviewing the repository. Use the local configs only on this machine, where the archived opponent executables still exist.

## Strategy Overview

The main entry point is `TankAI.get_action(state)`. The judge sends a JSON state through standard input, and the bot returns one of `UP`, `DOWN`, `LEFT`, or `RIGHT`.

The main strategy includes:

- Legal move checks: avoid walls, boundaries, and immediate reverse moves under Pro rules.
- Bullet risk checks: simulate bullets moving two cells per frame and account for wall blocking.
- Mobility scoring: use BFS to estimate available space around candidate positions.
- Trap prediction: use DFS/static map analysis to avoid entering dead ends.
- Attack scoring: check whether the bot can aim at an enemy after moving.
- Stability scoring: reduce unnecessary direction jitter.

## Run

Check Python:

```powershell
py --version
```

Compile-check the main source:

```powershell
py -m py_compile .\src\bots\xjy.py
```

Run the standard judge:

```powershell
.\bin\judges\judge.exe
```

Run the Pro judge:

```powershell
.\bin\judges\judge_pro.exe
```

Run the 1v1 judge:

```powershell
.\bin\judges\judge_1v1_final_10.exe
```

## Packaging

To rebuild the main bot:

```powershell
pyinstaller --onefile --clean --paths .\src .\src\bots\xjy.py
```

PyInstaller will create new `build/` and `dist/` folders. Those folders are ignored by Git. After verifying a new executable, manually replace `bin/final_bots/xjy.exe` if needed.

## History

The project keeps historical strategy files such as `xjy921.py`, `xjy1018.py`, `xjy1108.py`, `Gemini3.py`, and `improved*.py` under `src/archive_versions/`. They are not the current entry point, but they document the strategy evolution from threat maps and path search toward trap handling and 1v1-specific behavior.

`archive/experiments/GPT.py` is retained as a duplicate-name history artifact. Its content matches the main `xjy.py` version.
