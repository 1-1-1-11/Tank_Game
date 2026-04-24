# Y. L. Tank Game Bot

这是一个面向 Y. L. Tank Game 比赛规则开发的 Python 坦克对战 Bot。项目重点不是训练模型，而是在裁判每一帧给出的地图、坦克、墙体和子弹状态下，快速返回一个合法且尽量安全的移动方向。

当前目录已按作品集展示整理：主版本源码、最终可执行文件、裁判程序、历史实验版本和展示材料分开放置。旧版本没有删除，只是归档到 `archive/` 或 `src/archive_versions/`，方便之后回看迭代过程。

## Project Positioning

- 类型：规则驱动的坦克对战 AI Bot
- 语言：Python
- 主要能力：局面评分、子弹规避、死胡同预判、火力线判断、Pro 规则适配
- 适合展示：算法建模、启发式搜索、竞赛策略迭代、工程归档能力

这个项目不应夸大成完整游戏引擎或深度学习系统。它更准确的定位是一个围绕比赛规则优化的实时决策程序。

## Directory Structure

```text
.
├─ config.json
├─ config_1v1.json
├─ src/
│  ├─ bots/
│  │  ├─ xjy.py
│  │  ├─ xjy1v1.py
│  │  └─ demo/
│  └─ archive_versions/
├─ bin/
│  ├─ judges/
│  └─ final_bots/
├─ docs/
│  ├─ images/
│  └─ XJY.pptx
├─ archive/
│  ├─ old_judges/
│  ├─ old_build_outputs/
│  ├─ old_specs/
│  └─ experiments/
└─ .spec-workflow/
```

## Main Files

- `src/bots/xjy.py`：当前主版本 Bot 源码。
- `src/bots/xjy1v1.py`：1v1 规则下的策略版本。
- `bin/final_bots/xjy.exe`：主版本 Bot 的最终打包文件。
- `bin/judges/judge.exe`：常规裁判程序。
- `bin/judges/judge_pro.exe`：Pro 规则裁判程序。
- `bin/judges/judge_1v1_final_10.exe`：保留的 1v1 最终裁判版本。
- `src/archive_versions/`：历史 Python 策略版本。
- `archive/old_build_outputs/`：旧的 PyInstaller 构建产物和历史对手 exe。

## Strategy Overview

主版本 Bot 的决策入口是 `TankAI.get_action(state)`。裁判通过标准输入传入 JSON 状态，Bot 输出 `UP`、`DOWN`、`LEFT` 或 `RIGHT`。

核心策略包括：

- 移动合法性检查：避免越界、撞墙和 Pro 规则下的立即反向。
- 子弹危险判断：按子弹每帧移动两格的规则模拟下一步风险，并考虑墙体阻挡。
- 机动性评分：用 BFS 估计目标位置附近的可活动空间。
- 陷阱预判：用 DFS 或静态地图分析判断进入某个方向后是否会被困在死胡同。
- 进攻评分：检查移动后是否能沿当前方向瞄准敌人。
- 稳定性处理：在多个候选方向接近时，减少无意义抖动。

## Run

先确认 Python 环境：

```powershell
python --version
```

如果要直接检查源码语法：

```powershell
python -m py_compile .\src\bots\xjy.py
```

运行常规裁判：

```powershell
.\bin\judges\judge.exe
```

运行 Pro 裁判：

```powershell
.\bin\judges\judge_pro.exe
```

运行 1v1 裁判：

```powershell
.\bin\judges\judge_1v1_final_10.exe
```

`config.json` 和 `config_1v1.json` 已更新为整理后的相对路径。历史对手 exe 保留在 `archive/old_build_outputs/dist/`，主 Bot 使用 `bin/final_bots/xjy.exe`。

## Packaging

如需重新打包主 Bot：

```powershell
pyinstaller --onefile --clean .\src\bots\xjy.py
```

新的打包产物默认会进入 `dist/`。为了保持项目整洁，确认可用后再手动替换 `bin/final_bots/xjy.exe`。

## History

开发过程中保留了多个实验版本，例如 `xjy921.py`、`xjy1018.py`、`xjy1108.py`、`Gemini3.py` 和 `improved*.py`。这些文件不是当前主入口，但能反映策略从威胁图、A*、走廊风险、1v1 策略到陷阱处理的迭代过程。

`GPT.py` 与主版本 `xjy.py` 内容一致，已作为重复留痕文件放入 `archive/experiments/`。
