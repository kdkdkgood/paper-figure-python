<!-- 条件读取：仅在多子图 + shared_axis 模式需要轴/标签/面板编号规则时读取此文件 -->

# Panel & Axis Rules（多子图核心规则）

## 1) 标号触发规则

- 当同一图中 `x` 轴标题数量 `>=2` 时，启用 `(A)(B)(C)...`。
- 单图默认不标号。
- 标号由 **runtime 引擎托管**（按 `panel_label_spec` 摆放），不必在 `post_draw` 手摆；完整用法见 `SKILL.md`「字图编号」。`panel_label_spec.mode="auto"` 即按下列轴模式规则自动选 inside/outside。

## 2) 轴模式规则

### `shared_axis`

- 子图间距：`wspace/hspace = 0.0`（共轴贴合）
- 标签显示：仅保留必要轴标签（底行 `x`、左列 `y`）
- 子图标号位置：子图内左上角（in-panel）

### `independent`

- 标签显示：`y` 轴标签保留；`x` 轴刻度与 `x` 轴标题在所有子图保留
- 子图间距比 `shared_axis` 更大
- 子图标号位置：子图外部（`outside`，X 轴标题下方居中，引擎按 tightbbox 自动预留底部空间）；当为单列且行数 `>=3` 的紧凑纵排时，回退 in-panel 以避免与 `xlabel` 干涉
- 该规则为固定联动策略；如需强制改摆放，用 `panel_label_spec.mode=inside/outside`
- 布局微调：`pair-2x1 + independent` 会自动压缩 `hspace` 并上移 `(A)(B)`，减少中间留白

## 3) 反干涉约束

- 子图标号不得与 `xlabel/ylabel/tick` 重叠
- 子图标号不得越出 figure 边界
- 优先使用相对坐标：`transform=ax.transAxes`

## 4) 字图编号完整参数（panel_label_spec）

字图编号由 **runtime 引擎托管**：AI 不必在 `post_draw` 里逐个手摆，引擎在布局守卫前按 `panel_label_spec` 统一摆放，inside↔outside 切换只改一行、绘图代码一字不动。

### 两种摆放模式

- **inside**：编号在子图**内部角落**，角由 `corner` 指定（`top_left` 默认 / `top_right` / `bottom_left` / `bottom_right`）；需要精确位置时用 `inside_x`/`inside_y`（transAxes 逃生口）。
- **outside**：编号摆在**每个子图 X 轴标题（xlabel）下方**、水平居中；引擎自动测量 xlabel + 刻度高度并下沉 `xlabel_gap_pt`，被 `ax.get_tightbbox` 计入 → 守卫自动预留底部空间、**绝不裁切**。

### `mode` 取值

- `auto`（默认）：单图不标号；≥2 图自动标号；`shared_axis` ⇒ inside 左上角，`independent` ⇒ outside，单列且 `nrows>=3` 的紧凑纵排回退 inside（避免撞 xlabel）。
- `inside` / `outside`：强制指定。
- `off`：不标号。

### `label_style`

`lower_paren`（默认 `(a)(b)`）/ `upper_paren`（`(A)(B)`）/ `lower`（`a b`）/ `upper`（`A B`）。

### 自定义编号文本（覆盖自动 a/b/c）

在 `post_draw` 设 `ctx.panel_labels = ["a", "b", None, "d"]`（`None` 表示该面板跳过），或用 `panel_label_spec.labels` 传同样的列表。其余摆放/间距仍由引擎按 spec 处理。

### 逃生口

若要完全手动控制单个编号，`from runtime.helpers import add_panel_label` 后在 `post_draw` 调用；一旦检测到手动编号，引擎自动跳过该图的托管摆放，不会重复。

绘图前指定（create 的 `--overrides` 或 patch 的 `panel_label_spec`）和事后交互修改（`fast_patch` 一行，归 L1、保留绘图代码、直接重出图）走的是**同一个入口**。
