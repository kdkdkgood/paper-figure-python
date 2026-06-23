# paper-figure-python

AI 科研绘图工作流底座：让 Codex 在受控边界内用 Python/Matplotlib 持续产出论文级图表，并把被验证过的绘图经验沉淀为下次可召回的规则。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Overview

`paper-figure-python` 不是普通绘图库，也不是固定图型模板集合。它是一套面向 AI Agent 的科研绘图 Skill：AI 可以自由理解数据、选择图型、编写绘图代码，但所有自由都被放进明确的工程边界里。

这套边界解决的是 AI 绘图中最常见的实际问题：

- 图能画出来，但越改越乱。
- 为了修一张图，AI 误改共享 runtime。
- 标签、图例、colorbar、裁切和多面板间距没有统一策略。
- 用户反复调整出的好经验，下次任务又从零开始。
- 中间版本还没被认可，却被错误沉淀成长期偏好。

这个仓库的目标是：**自由实现图层，稳定保护底座，自动守住版式，任务结束后沉淀经验。**

## Repository Layout

可安装的 Codex Skill 位于独立目录：

```text
paper-figure-python/
```

仓库结构：

```text
.
├── README.md
├── LICENSE
└── paper-figure-python/
    ├── SKILL.md
    ├── README.md
    ├── scripts/
    ├── memory/
    ├── references/
    ├── examples/
    └── agents/
```

下载、复制或安装时，请保留完整的 `paper-figure-python/` 目录。`SKILL.md` 是 AI 使用本 Skill 时的主入口；根目录 `README.md` 用于说明公开仓库的定位、边界和授权。

## Key Features

### Thin Runtime

Skill 创建轻量 `plot.py` job。AI 只允许编辑三个区域：

```python
# --- AI_EDIT_ZONE:imports START ---
# --- AI_EDIT_ZONE:imports END ---

# --- AI_EDIT_ZONE:pre_draw START ---
# --- AI_EDIT_ZONE:pre_draw END ---

# --- AI_EDIT_ZONE:post_draw START ---
# --- AI_EDIT_ZONE:post_draw END ---
```

这让 AI 可以自由实现数据清洗、reshape、统计层、标注和复杂图型组合，同时避免污染共享 runtime。

### FigureContext API

AI 绘图时通过稳定 API 工作，而不是依赖 runtime 内部细节：

- `ctx.fig`
- `ctx.ax(index)`
- `ctx.axes_grid`
- `ctx.style`
- `ctx.layout`
- `ctx.color`
- `ctx.palette()`
- `ctx.df_override`
- `ctx.panel_dfs`

这样保留 Matplotlib 的灵活性，同时统一风格、布局、颜色和数据挂载方式。

### Layout Guard

科研图表常见的问题不是“画不出来”，而是版式失控。Layout guard 用于处理：

- 标签和标题溢出。
- 图例或 colorbar 挤压主图。
- 多面板间距不足。
- 裁切不稳定。
- 用户要求“更松、更大气”时，AI 只会手动 `tight_layout()`。

推荐通过参数表达版式意图：

- `layout_spec.width_mm`
- `layout_spec.aspect_ratio`
- `style_spec`
- `layout_guard_spec.intent`
- `layout_guard_spec.preferred_canvas_scale`

默认原则：优先保护主图数据区，不为了标签、图例或 colorbar 随意压缩主图。

### Runtime Integrity Guard

`scripts/runtime/` 和 `scripts/orchestrator/` 是所有 job 共享的稳定底座。当前版本会在出图后检查共享底座是否偏离 `.runtime_baseline.json`。

如果检测到漂移，系统会在 stderr 和 run report 中提示，但不会阻断出图。故意升级底座后，可以刷新基线：

```bash
python3 paper-figure-python/scripts/memory.py baseline --refresh
```

### Memory System

`memory/` 是这个 Skill 的核心能力之一。它不是聊天记录，也不是自动日志，而是用于沉淀可复用绘图经验的轻量系统。

它适合记录：

- 某类图的标签摆放策略。
- 中文字体缺字时的稳定修法。
- colorbar 溢出时扩画布而不是压缩主图。
- 用户偏好的“论文感”“宽松感”“高级感”如何落到参数。
- 多面板图如何组织科学叙事。

开图前，AI 可以用 `memory.py recall` 召回相关经验。任务结束后，只有在用户明确认可最终图时，AI 才应判断是否收集新经验。

## Memory Collection Boundary

经验收集不是自动发生的。

当图还在调整中，AI 不应把中间版本写成长期经验。请在满意后明确告诉 AI，例如：

```text
可以了，这个版本通过；如果有可复用经验就记录一下。
```

或：

```text
以后类似图都按这个风格来。
```

这类确认会让 AI 判断是否运行：

- `memory.py suggest`
- `memory.py remember`
- `memory.py reinforce`

是否建议、强化或写入经验由 AI 按 `memory-protocol` 自动判断。用户不需要手动区分哪些内容值得记录，也不需要管理经验条目的类型、权重或作用域。

Memory 是旁路系统：召回、建议或写入失败都不影响正常出图。

## Quick Start

Create a figure job:

```bash
python3 paper-figure-python/scripts/create_figure.py \
  --task "绘制一张论文风格图" \
  --job-name demo \
  --chart-type custom \
  --layout single \
  --style-profile elsevier \
  --axis-mode independent \
  --out-root ./output \
  --output-mode json \
  --template-mode thin \
  --no-run \
  --no-validate
```

Edit only the generated job file:

```text
output/demo/plot.py
```

Run:

```bash
python3 output/demo/plot.py
```

Check workflow compliance:

```bash
python3 paper-figure-python/scripts/check_workflow_compliance.py \
  --job-dir ./output/demo \
  --output-mode text
```

Patch layout/style after visual review:

```bash
python3 paper-figure-python/scripts/patch_figure.py \
  --plot ./output/demo/plot.py \
  --patch '{"layout_guard_spec":{"intent":"roomy"}}' \
  --run \
  --output-mode json
```

## References and Examples

The Skill includes conditional references. AI should read only what is relevant to the current task:

- `paper-figure-python/references/drawing-priors.md`：科研绘图表达原则、反冗余策略、布局和配色 priors。
- `paper-figure-python/references/figure-archetypes.md`：多面板叙事结构。
- `paper-figure-python/references/chart-atlas/`：按图型分片的速查资料。
- `paper-figure-python/references/params/`：参数语义、后调整映射、色板预设。
- `paper-figure-python/references/layout_priors/`：常见面板结构的布局先验。
- `paper-figure-python/examples/`：可运行的 thin plot 示例。

## Intended Use and Boundaries

This repository is intended for:

- AI-assisted scientific plotting.
- Paper-style figures and multi-panel layouts.
- Reproducible figure jobs with explicit editable zones.
- Iterative visual refinement with compliance checks.
- Experience reuse through the memory system.

This repository is not intended to be:

- A general-purpose plotting library with stable public Python APIs.
- A replacement for Matplotlib, pandas, seaborn, scipy, or domain plotting libraries.
- A guarantee that generated figures are scientifically valid without human review.
- A substitute for journal-specific figure validation or publication compliance checks.

Users are responsible for verifying data correctness, statistical interpretation, figure ethics, copyright of input assets, and publication requirements.

## License

This project is released under the [MIT License](LICENSE).

You may use, copy, modify, merge, publish, distribute, sublicense, and sell copies of this software, subject to the MIT License terms.

The software is provided “as is”, without warranty of any kind. See [LICENSE](LICENSE) for the full license text.
