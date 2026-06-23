# paper-figure-python

科研绘图专用 Codex Skill：用轻量 `plot.py` 入口、稳定运行时和论文级布局守卫，把 AI 的灵活绘图能力约束在可复现、可检查、可迭代的工程流程里。

这个仓库不是一个固定图型库。它的核心设计是：Skill 负责创建绘图 job、提供 `FigureContext` API、统一风格/布局/颜色/裁切参数、执行保存与合规检查；具体图型、数据整理、统计层、标注和视觉表达，由 AI 只在 job 自己的 `plot.py` 的 `AI_EDIT_ZONE` 中完成。

## 适合做什么

- 论文级单图和多面板图：散点、线图、柱状、热图、森林图、雷达图、图像拼版等。
- 需要反复微调版式的科研图：字号、边距、图例、色板、裁切、共享轴。
- 需要让 AI 自主实现复杂图层，但又不能随意修改共享运行时的绘图任务。
- 需要把成功经验沉淀下来，在后续绘图中自动召回和复用的长期工作流。

## 当前架构

### Thin Runtime

`create_figure.py` 生成一个轻量 job：

- `plot.py`：唯一允许 AI 为单张图编辑的文件。
- `AI_EDIT_ZONE:imports`：补充 import。
- `AI_EDIT_ZONE:pre_draw`：读取、清洗、转换数据。
- `AI_EDIT_ZONE:post_draw`：完成实际绘图、统计层、标注和轴设置。

共享底座只提供稳定能力：

- `FigureContext`：统一访问 `fig`、`axes_grid`、`style`、`layout`、`color`、`palette()` 和数据挂载点。
- runtime engine：运行 `pre_draw/post_draw`、保存图片、写 run report。
- layout guard：在保存前处理溢出、裁切、面板间距和主图区域保护。
- helpers：提供非侵入式坐标轴工具。

### 编辑边界

单个绘图 job 只能修改自己的 `plot.py` 的三个 `AI_EDIT_ZONE`。

以下文件是所有 job 共享的稳定底座，不应为了单张图修改：

- `scripts/runtime/engine.py`
- `scripts/runtime/context.py`
- `scripts/runtime/helpers.py`
- `scripts/runtime/integrity.py`
- `scripts/orchestrator/core.py`

当前版本新增 runtime integrity guard：每次出图后会比对共享底座与 `.runtime_baseline.json` 的指纹。如果底座漂移，会在 stderr 和 run report 中给出警告，但不阻断出图。故意升级底座后，使用：

```bash
python3 scripts/memory.py baseline --refresh
```

### 经验成长系统

`memory/` 是轻量经验模块，用于把反复有效的绘图策略沉淀成可召回规则。

典型能力：

- 开图前 `recall`：根据任务摘要召回相关经验 hook。
- 迭代后 `suggest`：从 run/patch report 中挖掘可复用候选经验。
- `reinforce`：对真正采纳或被推翻的经验做权重反馈。
- `audit`：整理经验索引和冲突项。

memory 是旁路系统：任何失败都不影响正常出图。

#### 经验收集触发条件

经验模块不会在每次出图后自动把当前状态写成长期规则。绘图任务只有在用户明确认可最终结果后，AI 才应判断是否进入经验收集流程。

推荐的用户确认语包括：

```text
可以了，这个版本通过；如果有可复用经验就记录一下。
```

```text
就这样，后面类似图按这个风格来。
```

```text
以后都这样处理。
```

原因是中间迭代版本通常只是临时状态：如果用户还在要求继续调整，AI 不应该把未确认的字号、布局、配色或图层策略沉淀成长期偏好。明确认可后，AI 再依据 `references/memory-protocol.md` 的 `write_score` 闸门判断：

- 用户明确认可、否决或表达“以后都这样”会显著提高写入分数。
- 终版相对首版有实质差异，尤其是 `CONFIG` 或 `AI_EDIT_ZONE` 代码演变，才更值得沉淀。
- 纯数据路径、列名、单位、语法错误修正通常不写入经验。
- 已有经验覆盖的情况，优先 `reinforce`，不重复写一条新经验。
- 涉及项目隐私的规律只应进入项目层 `.paper-figure-memory/`，不应进入全局层。

因此，一个完整的推荐交互是：

1. 用户提出绘图需求。
2. AI 召回经验、创建 job、绘图、检查、调整。
3. 用户看图后说“可以了”或“以后按这个来”。
4. AI 再运行 `suggest`，必要时 `remember`，并对本次实际采纳的经验做 `reinforce`。

## 快速使用

创建新图：

```bash
python3 scripts/create_figure.py \
  --task "绘制一张论文风格雷达图" \
  --job-name radar_demo \
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

编辑生成的 job：

```text
output/radar_demo/plot.py
```

只改其中三个区域：

```python
# --- AI_EDIT_ZONE:imports START ---
# --- AI_EDIT_ZONE:imports END ---

# --- AI_EDIT_ZONE:pre_draw START ---
# --- AI_EDIT_ZONE:pre_draw END ---

# --- AI_EDIT_ZONE:post_draw START ---
# --- AI_EDIT_ZONE:post_draw END ---
```

运行出图：

```bash
python3 output/radar_demo/plot.py
```

合规检查：

```bash
python3 scripts/check_workflow_compliance.py \
  --job-dir ./output/radar_demo \
  --output-mode text
```

后调整：

```bash
python3 scripts/patch_figure.py \
  --plot ./output/radar_demo/plot.py \
  --patch '{"layout_guard_spec":{"intent":"roomy"}}' \
  --run \
  --output-mode json
```

## 目录说明

| 路径 | 作用 |
|---|---|
| `SKILL.md` | Skill 主说明，AI 使用本仓库时优先读取 |
| `scripts/create_figure.py` | 新建绘图 job |
| `scripts/patch_figure.py` | 后调整与快速重编译 |
| `scripts/check_workflow_compliance.py` | job 合规检查 |
| `scripts/run_smoke_tests.py` | smoke test |
| `scripts/runtime/` | thin runtime、`FigureContext`、layout guard、完整性自检 |
| `scripts/orchestrator/` | create/patch 编排服务 |
| `scripts/params/` | 参数默认值、编译、布局先验应用 |
| `scripts/palette_registry.py` | 色板和领域配色预设 |
| `references/chart-atlas/` | 图型速查 |
| `references/params/` | 参数说明与后调整映射 |
| `references/layout_priors/` | 布局先验 JSON |
| `memory/` | 可召回、可强化的绘图经验库 |
| `examples/` | 可运行示例 |

## 设计原则

- 图型开放：`chart_type=custom` 是常态，AI 在 `AI_EDIT_ZONE` 中实现具体图。
- 底座稳定：共享 runtime 不为单图让步，单图逻辑落在 job `plot.py`。
- 版式受控：用 layout guard 和参数表达风格意图，而不是临时关闭保护。
- 可复现：job 自包含绘图逻辑，run report 留下配置、布局守卫和 integrity 记录。
- 可成长：成功经验进入 `memory/`，下次开图前召回，避免重复踩坑。

## 当前公开仓库状态

默认分支：`master`

仓库地址：

```text
https://github.com/kdkdkgood/paper-figure-python
```
