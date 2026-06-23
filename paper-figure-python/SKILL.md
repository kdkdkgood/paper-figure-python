---
name: paper-figure-python
description: 科研绘图专用技能。create 只生成轻量 plot.py、运行时 API、风格/布局参数和布局守卫；具体图型与图层由 AI 在 AI_EDIT_ZONE 中自主实现。
---

# Paper Figure Python

## 核心定位

这个 skill 不再提供强制图类型绘制器。它只负责：

- 创建轻量 `plot.py` 入口。
- 提供统一的 `FigureContext` API。
- 提供论文风格、布局、颜色、坐标轴、裁切和布局守卫参数。
- 运行保存、裁切、布局守卫和合规检查。

具体画什么图、如何 reshape 数据、如何叠加统计层、如何标注，全部交给 AI 在 `AI_EDIT_ZONE` 中完成。

## ⛔ 编辑边界铁律（不可逾越）

**唯一允许编辑的文件是每个 job 自己的 `plot.py`，且仅限其中三个 `AI_EDIT_ZONE` 区段。**

`scripts/runtime/`（`engine.py` / `context.py` / `helpers.py` / `integrity.py`）与 `scripts/orchestrator/core.py` 是**所有 job 共享的稳定底座**。为单张图改动它们，会静默破坏过去、现在、未来的每一个 job——这是绝对禁止的。

- **报错指向 `engine.py` 等底座 ≠ 该改底座。** 底座按设计是稳定的、`plot.py` 是灵活的。把解决方案落在 `plot.py` 的 `AI_EDIT_ZONE`，而非迁就性地改引擎。
- 出图时若检测到底座偏离基线，stderr 会打印醒目警告并写入 run report 的 `runtime_integrity`。看到该警告先自查是否误改了底座。
- 确需升级底座（极少数、面向所有 job 的能力增强）：改完用 `python3 $SKILL_ROOT/scripts/memory.py baseline --refresh` 刷新基线。

### 典型陷阱：极坐标/自定义 projection 不要 `remove()` 轴

`ctx.ax(0).remove()` 会让轴脱离 figure（`.figure` 变 None），引擎出图前遍历原始 `axes_grid` 调 `tick_params()` 时即崩溃（`'NoneType' object has no attribute 'dpi_scale_trans'`）——**正确做法是隐藏旧轴、叠加新轴**：

```python
# AI_EDIT_ZONE:post_draw —— 切换到 polar 等自定义 projection
old_ax = ctx.ax(0)
old_pos = old_ax.get_position()
old_ax.set_visible(False)                      # 关键：隐藏而非 remove()，旧轴仍挂在 figure 上
ax = ctx.fig.add_subplot(1, 1, 1, projection="polar")
ax.set_position(old_pos)
ctx.axes_grid = np.array([[ax]])               # 供你后续代码引用；在此 ax 上完成全部绘图
```

引擎遍历的是它自己构建的**原始** `axes_grid`（那个隐藏的 Cartesian 轴，对它做轴细节处理安全无害），不会碰你新加的 polar 轴——所以不必、也不应为此改引擎。

## 路径约定

- **SKILL_ROOT** = 本 skill 实际安装目录。**不要写死**——它随机器与操作系统变化（macOS/Linux/Windows，可能是 `~/.claude/skills/paper-figure-python`、`~/.kiro/skills/paper-figure-python` 或任意自定义位置）。
- 下文示例统一用占位符 `$SKILL_ROOT` 与通用 `python3`。**用前先自举一次**，把占位符换成真实路径（见下）。
- 输出位置由用户指定；未指定时用当前 workspace 的 `output`。禁止把任务输出写回 `SKILL_ROOT`。
- **迁移**：脚本运行时自动探测自身位置（`__file__` 反推 + 环境变量 `PAPER_FIGURE_SKILL_ROOT` 覆盖 + `~/.claude/skills`、`~/.kiro/skills` 常见安装位 + job 父目录），跨机器/跨工具（Codex 等）零配置。仅当全部探测失败时，设 `PAPER_FIGURE_SKILL_ROOT` 指向 skill 根目录即可。

### 自举 SKILL_ROOT（跨平台，零配置）

本文件即位于 `<SKILL_ROOT>/SKILL.md`，AI 读到它时已知道 skill 根目录，可直接把示例里的 `$SKILL_ROOT` 替换为该真实路径。需要程序化确认时，让 `memory.py` 自报位置（它用 `__file__` 自定位，在任何 OS、任何安装位都成立）：

```bash
# macOS / Linux
python3 "<本文件所在目录>/scripts/memory.py" root   # 输出 skill_root / memory_root
# Windows PowerShell 同理：python <...>\scripts\memory.py root
```

`python3` 仅为占位；用调用方环境内可用的 Python 即可（你的专有解释器路径由你的系统提示词注入，不写进本 skill）。

## 工作流

### 新图

1. 快速判断任务、数据路径、推荐 layout 和 style。
2. 调用 create 生成 job。
3. 直接编辑 job 内 `plot.py` 的 `AI_EDIT_ZONE`。
4. 运行 `python <PLOT_PATH>` 出图。
5. 运行合规检查。

### 迭代修改

同一张图的后续反馈直接改现有 `plot.py`，不要重新 create。只有更换数据文件、全新图、用户明确要求新建时才开新 job。

### 看图后调整

生成 `figure.png` 后的风格和布局微调优先走 `patch_figure.py` / `fast_patch`，它会保留原有 `AI_EDIT_ZONE` 绘图代码，只重编译 CONFIG 并可直接重新运行。适合：

- 放大/缩小字号、线宽、marker、图例。
- 调整画布比例、面板间距、边距和裁切策略。
- 设置 `layout_guard_spec.intent="roomy"` 或 `"preserve_data"` 来表达用户风格意图。

只有新增图层、改数据处理、改统计逻辑时，才直接编辑 `plot.py` 的 `AI_EDIT_ZONE`。

## 经验成长系统

本 Skill 带轻量经验模块（`memory/`），在多轮调整中沉淀可复用经验、并用"经验是否真被采纳"反向校准自己。**旁路设计**：memory 故障绝不影响出图，任何 `memory.py` 命令失败都静默降级、退出码 0。细则见 `references/memory-protocol.md`（不进默认读取链）。

下文命令用 `python3` 与 `$SKILL_ROOT` 占位符（见「路径约定」自举一次即得真实值）；`memory.py` 自身会探测记忆根，跨平台零配置。

### 开新图（积累兑现处）

读 SKILL.md 后、分析任务前，先召回一次（一条命令拿 BOOT 锚点 + 命中 hook，正文 0 展开）：

```bash
python3 "$SKILL_ROOT/scripts/memory.py" recall \
  --workspace <WORKSPACE_ROOT> --context "<任务摘要>"
```

- 默认**只用返回的 hook 决策**；仅 `heavy_read=true`（`eff_weight≥0.8`）、高风险（多面板/colorbar/shared_axis/复杂图例）或 hook 与当前情况冲突时，才读对应 `entry` 正文。
- 看顶层 `quality`：`low` 表示与已有经验关联弱，直接走下文默认规则出图，别被 `relevance=low` 的条目带偏；`high/medium` 再优先采纳对应 hook。
- 把召回经验折进 create 参数、`layout/style/color/layout_guard` spec 与 `AI_EDIT_ZONE` 策略。`anti://` 命中表示"别这么做"。

### 迭代中

不写正式经验，专心改图。`orchestrator_reports/` 已自动留 patch 历史作为后续证据。

### 图稳定 / 被用户认可后

1. 若 job 有多轮 patch，跑 `suggest` 从 report 历史挖候选（对比首版↔终版 config）：
   ```bash
   python3 "$SKILL_ROOT/scripts/memory.py" suggest \
     --job-dir <JOB_DIR> --workspace <WORKSPACE_ROOT>
   ```
2. 算 `write_score`（见 protocol §3）：`≥3` 才一句话提示后 `remember`（项目专属归项目层、通用归全局层）。
3. **回报强化**——把本次召回里真正落地的经验记一票，被推翻的减一票：
   ```bash
   # 多个 path 用空格分隔跟在同一个 flag 后，不要重复 --adopted / --rejected
   python3 "$SKILL_ROOT/scripts/memory.py" reinforce \
     --workspace <WORKSPACE_ROOT> --adopted "<path>" "<path2>" --rejected "<path>"
   ```

### 明确不写

纯数据/列名/路径/单位修正、语法/依赖错误、一次性 reshape、临时口味、已有经验已覆盖、用户明说别记。

### 审计

净增经验多、出现冲突或衰减待办累积时，或用户要求"整理经验库"时跑 `audit`；破坏性合并/废弃**先报告原因、老板确认后**再执行（protocol §8）。

## CLI

create：

```bash
python3 "$SKILL_ROOT/scripts/create_figure.py" \
  --task <TASK> \
  --job-name <JOB_NAME> \
  --chart-type custom \
  --layout <LAYOUT> \
  --style-profile elsevier \
  --axis-mode independent \
  --out-root <WORKSPACE_ROOT>/output \
  --output-mode json \
  --template-mode thin \
  --no-run \
  --no-validate
```

run：

```bash
python <PLOT_PATH>
```

check：

```bash
python3 "$SKILL_ROOT/scripts/check_workflow_compliance.py" \
  --job-dir <JOB_DIR> \
  --output-mode text
```

smoke test：

```bash
python3 "$SKILL_ROOT/scripts/run_smoke_tests.py" \
  --out-root <WORKSPACE_ROOT>/output/smoke_tests
```

patch：

```bash
python3 "$SKILL_ROOT/scripts/patch_figure.py" \
  --plot <JOB_DIR>/plot.py \
  --patch <PATCH_JSON_OR_FILE> \
  --run \
  --output-mode json
```

**后调整是增量 patch**：新 patch 基于当前 `plot.py` 的 CONFIG 深合并，不必重复上次已调过的参数；默认备份旧 `plot.py`（`--no-backup` 关闭）。

**「用户意图 → patch 参数」完整速查表**见 `references/params/post-adjust-map.md`，看图后调整时按需读取。

## AI_EDIT_ZONE 协议

生成的 `plot.py` 只有三类 AI 可编辑区域：

- `AI_EDIT_ZONE:imports`：添加 pandas、scipy、seaborn 等 import。
- `AI_EDIT_ZONE:pre_draw`：读取、清洗、转换数据；把结果挂到 `ctx`。
- `AI_EDIT_ZONE:post_draw`：完成所有实际绘图、统计层、标注和轴设置。

推荐模式：

```python
def pre_draw(ctx):
    import pandas as pd

    df = pd.read_csv("data.csv")
    ctx.df_override = df


def post_draw(ctx):
    ax = ctx.ax(0)
    style = ctx.style
    colors = ctx.palette(3)
    df = ctx.df_override

    ax.scatter(df["x"], df["y"], s=style["marker_size"], color=colors[0])
    ax.set_xlabel("X (unit)", fontsize=style["axis_label_size"])
    ax.set_ylabel("Y (unit)", fontsize=style["axis_label_size"])
```

## FigureContext API

AI 绘图时优先使用 `ctx`，不要反复扫描 runtime 源码。

| API | 用途 |
|---|---|
| `ctx.fig` | 当前 matplotlib Figure |
| `ctx.axes_grid` | axes 网格 |
| `ctx.ax(index)` | 按展平序号取轴 |
| `ctx.axis(row, col)` | 按行列取轴 |
| `ctx.cfg` | 完整运行配置 |
| `ctx.style` | `style_spec` 推荐参数 |
| `ctx.layout` | `layout_spec` 推荐参数 |
| `ctx.color` | `color_spec` |
| `ctx.colors` | 当前分类色板列表 |
| `ctx.palette(n=None)` | 取前 n 个分类色 |
| `ctx.df_override` | 单图或全局数据对象 |
| `ctx.panel_dfs[index]` | 多面板按面板挂载数据 |
| `ctx.share_axes` / `ctx.sharex` / `ctx.sharey` | 当前是否启用原生共享轴（见“共享轴模式”） |

## 可选工具函数（helpers）

非侵入的纯 ax 工具，按需取用，也可自己实现。`from runtime.helpers import ...`：

| 函数 | 用途 |
|---|---|
| `add_panel_label(ax, "a")` | 手动面板编号逃生口（默认引擎托管，见「字图编号」；手动调用后引擎跳过该图自动摆放） |
| `add_significance_bracket(ax, x1, x2, y, p=...)` | 显著性括号 + 星标 |
| `make_ablation_colors(base_hex, n)` | 单色变 alpha 的消融/层级配色 |
| `apply_print_safe_hatching(container, "//")` | 叠加纹理，灰度/色盲安全 |
| `tighten_y_axis(ax, lo, hi)` | 按数据范围收紧坐标轴留白 |
| `is_dark(hex)` / `luminance_aware_text_color(bg)` | 亮度感知文字配色 |
| `style_dark_image_ax(ax)` | 暗背景成像面板（黑底、去脊柱/刻度） |

## 参数语义

- `chart_type` 是绘图意图标签，默认 `custom`，允许任意非空字符串。
- `layout_spec` 是推荐画布结构和尺寸。
- `style_spec` 是推荐视觉参数。
- `color_spec` 是推荐色板和色图参数。**换配色只有单一入口 `color_spec.palette_preset`**，选定后 `ctx.color` 与 `ctx.palette()` 自动同步；需要固定自定义色时用 `color_spec.categorical_palette` 传 hex 列表（唯一逃生口）。可选预设、领域适配和逃生口规则详见 `references/params/palette-presets.md`。
- `layout_guard_spec` 是布局安全层参数。
- 这些参数不限制 AI 选择图型、统计方法、列映射或图层组合。
- 用户明确要求“更大、更松、更有个人风格”时，优先通过 `layout_spec.width_mm/aspect_ratio`、`style_spec` 字号/线宽/marker，或 `layout_guard_spec.intent` 表达意图；不要直接关闭守卫。
- `layout_guard_spec.intent` 可用：`balanced` 默认论文平衡、`compact` 紧凑、`roomy` 更愿意扩画布、`preserve_data` 更保护主图区。必要时叠加 `preferred_canvas_scale`，例如 `1.15`。

## 共享轴模式（shared_axis）

`--axis-mode shared_axis`（或 patch 的 `route.axis_mode=shared_axis`）在面板数 > 1 时让 runtime 走 matplotlib **原生** `sharex`/`sharey`（多行列内共享 X、多列行内共享 Y、混合面板自动降级 `independent`）。完整的间距/标号/标签规则见 `references/params/panel-axis-rules.md`。

对 AI 绘图代码的两个关键语义（避免踩坑）：

- 内侧面板 tick label 由 matplotlib 自动隐藏，**无需手动** `tick_params(labelbottom=False)`。
- ⚠️ `set_xlim()` 在 sharex 下联动列内所有面板，`set_ylim()` 在 sharey 下联动行内所有面板——这是预期行为。

### 轴标签自适应范式（务必采用）

**不要写死轴标签铺设位置**，否则用户 patch 切换 `axis_mode` 后标签会缺失或冗余。用 `ctx.sharex`/`ctx.sharey` 让标签随共享方向自动联动——同一份代码在两种模式下都正确：共享 X 时仅最底行铺 `xlabel`、共享 Y 时仅最左列铺 `ylabel`，独立时每个面板都铺。

```python
if (not ctx.sharex) or r == ctx.nrows - 1:  # 共享 X 仅最底行；独立每个都铺
    ax.set_xlabel("物理量 (单位)")
if (not ctx.sharey) or c == 0:              # 共享 Y 仅最左列；独立每个都铺
    ax.set_ylabel("物理量 (单位)")
```

## 字图编号（panel_label_spec）

字图编号由 **runtime 引擎托管**：AI 不必在 `post_draw` 手摆，引擎在布局守卫前按 `panel_label_spec` 统一摆放。`mode="auto"`（默认）即按轴模式自动选 inside/outside 并自动预留空间、绝不裁切；`inside`/`outside`/`off` 可强制。

**完整参数**（`corner`、`label_style`、自定义文本 `ctx.panel_labels`、手动逃生口 `add_panel_label`）详见 `references/params/panel-axis-rules.md` §4，仅在需要调整编号位置/样式时读取。

## Layout 推荐

布局选型表（场景 → layout → axis_mode）见 `references/drawing-priors.md` §4「布局推荐」。常用速记：单图 `single`、宽标签 `double`、横向比较 `pair-1x2` / `triple-1x3`、主图+残差 `pair-2x1`、论文主图 `quad-2x2`、纵向多指标堆叠 `quad-4x1`、六面板 `hex-2x3` / `hex-3x2`。

## 绘图规范

- AI 必须在 `plot.py` 中绘图，不要绕过 job 直接用临时脚本出图。
- 不要用 `np.random` 伪造真实任务数据。
- 优先从 `ctx.style`、`ctx.layout`、`ctx.colors` 读取视觉参数。
- 不要无理由手动调用 `fig.subplots_adjust()`、`plt.tight_layout()`、`fig.set_size_inches()`；布局由守卫统一处理。
- 图型、数据 reshape、统计检验、显著性标注、inset、colorbar、双轴、极坐标等均由 AI 自主实现。

## 最小读取

默认只读：

- 本文件。
- `memory.py recall` 的输出（一次调用拿 BOOT 锚点 + 命中 hook，正文 0 展开；命中且 `eff_weight≥0.8`/高风险/冲突时才读对应 entry 正文）。
- 用户提供的数据文件或现有 `plot.py`。

仅在需要布局/表达推荐时读取（**先读 `drawing-priors.md`，它是绘图表达中枢，其余按需展开**）：

- `references/drawing-priors.md`（中枢：绘图表达、信息架构、反冗余、配色预设入口）
- `references/figure-archetypes.md`（多面板叙事布局）
- `references/chart-atlas/`（图型速查，按图型分片读取）
- `references/nature-2026-observations.md`（当代视觉趋势）
- `references/params/palette-presets.md`（领域配色预设）
- `references/layout_priors_index.json` 及对应分片
- `references/params/global-core.md`
- `references/params/panel-axis-rules.md`（多子图轴/标签规则 + §4 字图编号完整参数）
- `references/params/post-adjust-map.md`（看图后「用户意图 → patch 参数」速查表）

创建新图前可参考可运行范例（覆盖柱/趋势/散点/热图/森林）：

- `examples/`（`python examples/<name>.py` 直接出图，含 helpers 与预设用法）

## 常见问题

- `UnboundLocalError: np`：不要在函数内部重复 `import numpy as np`，模板已提供全局 `np`。
- 图为空：确认 `post_draw(ctx)` 中实际调用了绘图 API。
- 标签/图例溢出：优先调整 `layout_guard_spec` 或 layout，不要直接绕开守卫。
- 多面板取错轴：用 `ctx.ax(index)` 或 `ctx.axis(row, col)`。
