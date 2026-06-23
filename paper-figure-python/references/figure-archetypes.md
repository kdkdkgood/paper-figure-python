<!-- 条件读取：需要把"科学叙事"映射到"多面板布局"时读取此文件。 -->

# Figure Archetypes：多面板叙事布局

把信息架构（`drawing-priors.md` 第 2 节）落到具体版面。每个 archetype 给出：**叙事意图 →
推荐 layout / 实现方式 → 关键 API → guard / style 提示 → 常见陷阱**。

> 关键约束：thin runtime 由 `layout_spec.nrows/ncols` 创建**均匀网格**。需要"不等大面板 /
> 合并单元格"时，不要去拼网格——取一个大轴（`single` / `double`），用
> `ax.inset_axes([x, y, w, h])`（坐标为 0-1 轴比例）自行切分子区域。

---

## A. Schematic-led Composite（示意图主导 + 量化面板）

- **叙事意图**：用大型机制 / 流程示意图引入，下方或右侧挂 1-3 个量化结果面板。常见于方法学主图。
- **推荐实现**：`single` 或 `double` 单大轴。主轴画示意图（`ax.annotate` 箭头、`patches`
  画框/流程、文本标注），再用 `ax.inset_axes` 在角落放定量 inset。
- **关键 API**：`ax.annotate(..., arrowprops=...)`、`matplotlib.patches.FancyBboxPatch/FancyArrowPatch`、
  `ax.inset_axes([0.62, 0.08, 0.34, 0.34])`、`ax.set_axis_off()`（示意区关坐标轴）。
- **提示**：示意主轴 `ax.set_axis_off()`；inset 用 `ctx.style` 字号；箭头/框线粗细对齐 `axes_linewidth`。
- **陷阱**：示意图元素过多显得花哨；inset 与示意元素重叠。先布局留白再放 inset。

## B. Dark Image Plate（暗背景成像拼贴）

- **叙事意图**：荧光 / 显微 / 注意力热力等图像的重复网格拼贴，黑底突出信号。
- **推荐实现**：`quad-2x2` / `quad-1x4` / `hex-2x3` 均匀网格；配 `color_spec.palette_preset="imaging_dark"`。
- **关键 API**：`ax.imshow(img, cmap=ctx.color["sequential_cmap"])`、
  `helpers.style_dark_image_ax(ax)`、scalebar 用 `ax.plot` + `ax.text`。
- **提示**：CONFIG 传 `axis_spec={"show_top_spine": False, "show_right_spine": False}` 配合
  `style_dark_image_ax` 彻底去脊柱；暗底文字用 `helpers.luminance_aware_text_color(bg)`。
- **陷阱**：runtime 默认白底；务必逐面板 `set_facecolor` 或用 helper，否则黑图周围露白。

## C. Clinical Triptych（临床三联：纵向→森林→汇总）

- **叙事意图**：临床 / 生存研究三步走——纵向随访曲线 → 效应量森林图 → 汇总（KM 或风险表）。
- **推荐实现**：`triple-3x1`（纵向堆叠）或 `triple-1x3`（横向）；配 `palette_preset="clinical_temporal"`。
- **关键 API**：纵向用 `ax.plot` + `ax.fill_between`（CI 带）；森林用 `ax.errorbar(x, y, xerr=...)`
  + `ax.axvline(1.0 或 0.0)` 参考线；汇总用阶梯 `ax.step` 或风险表 `ax.table`。
- **提示**：三面板共享同一组别配色；森林图 y 轴类别从上到下按效应量排序更可读。
- **陷阱**：HR/OR 森林图横轴常用对数刻度（`ax.set_xscale("log")`），别用线性误导。

## D. Asymmetric Hero Layout（非对称主图 + 小辅助面板）

- **叙事意图**：一个主导的复杂面板（大圆形 / 极坐标 / 网络 / 大热图）+ 几个小辅助面板。
- **推荐实现**：`double` 单大轴 + `inset_axes` 放小辅助面板；或 `pair-1x2` 让左大右小（用
  `layout_spec.aspect_ratio` 调整整体，再在右面板内 inset 叠放）。
- **关键 API**：极坐标 inset 用 `ax.inset_axes([...], projection="polar")`；
  `ax.inset_axes` 可多次调用堆叠多个小面板。
- **提示**：主面板承担 Overview，辅助面板承担 Deviation/Relationship，避免重复同一信息。
- **陷阱**：非对称容易失衡；让主面板占视觉面积 ≥ 60%，辅助面板字号不小于主面板的 0.85×。

## E. Small-Multiples Grid（小倍数网格）

- **叙事意图**：同一图型在多个条件 / 时间点 / 个体上重复，靠"重复中找差异"。
- **推荐实现**：`quad-1x4` / `quad-2x2` / `hex-2x3`，优先 `shared_axis` 统一量纲便于横向比较。
- **关键 API**：循环 `for i, ax in enumerate(ctx.axes_grid.ravel()): ...`；统一 `ax.set_ylim`。
- **提示**：所有面板共用一套坐标范围与配色；只在底行标 x 轴、左列标 y 轴（runtime 在
  `shared_axis` 下自动精简间距）；面板编号用 `helpers.add_panel_label` 逐面板添加（thin 模式不自动编号）。
- **陷阱**：面板过多导致单格过小；超过 6-8 格考虑聚合或换热图。

---

## 选型速查

| 你的叙事 | archetype | layout 起点 |
|---|---|---|
| 先讲机制再给数据 | A 示意主导 | `single` + inset |
| 一堆成像图要拼 | B 暗背景拼贴 | `quad-2x2` + imaging_dark |
| 临床随访 + 效应量 | C 临床三联 | `triple-3x1` + clinical_temporal |
| 一个主面板撑全场 | D 非对称主图 | `double` + inset |
| 同图型多条件重复 | E 小倍数 | `quad-1x4` shared_axis |
