<!-- 条件读取：仅在需要绘图表达、布局或参数推荐时读取此文件。这里是 priors，不是硬约束。 -->

# Drawing Priors：科研绘图表达与参数推荐

本文只提供推荐参数，不定义硬性图型边界。AI 可以根据数据语义自由选择图型、图层和统计表达。

> 配套参考（按需读取）：
> - 多面板叙事布局：`references/figure-archetypes.md`
> - 图型速查地图：`references/chart-atlas/`（按图型分片）
> - 2026 视觉趋势：`references/nature-2026-observations.md`
> - 领域配色预设：`references/params/palette-presets.md`
> - 可选工具函数：`scripts/runtime/helpers.py`（`from runtime.helpers import ...`）

## 1. 使用原则

- `chart_type=custom` 是默认推荐：runtime 创建画布和 axes，AI 在 hook 中完成绘图。
- runtime 不提供强制图类型绘制器；图型、图层、统计表达由 AI 按数据语义实现。
- `layout_spec`、`style_spec`、`color_spec`、`layout_guard_spec` 是视觉 priors，用于统一论文风格。
- 复杂科研表达优先写 hook 代码，不把图型逻辑沉积到全局配置。

## 2. 信息架构：先想"讲什么故事"，再选图型

动笔前先确定这张图回答的科学问题属于哪一层，避免多面板信息冗余：

| 层级 | 回答的问题 | 典型表达 |
|---|---|---|
| **Overview（概览）** | "整体长什么样 / 有几类" | 分布图、热图、时间总览、示意图 |
| **Deviation（差异）** | "谁比谁高 / 处理有没有效果" | 分组柱 + 原始点、point-range、森林图、配对图 |
| **Relationship（关系）** | "变量之间怎么联动 / 能否预测" | 散点 + 回归、相关矩阵、二维密度 |

多面板组图建议沿 **Overview → Deviation → Relationship** 递进，每个面板只承担一层职责；
若两个面板讲同一件事，合并或删除其一。布局如何映射这条叙事线，见 `figure-archetypes.md`。

## 3. 反冗余策略（默认偏好）

科研图的清晰度来自"删"，不是"加"。除非有明确理由，默认遵循：

- **能直接标注就不用图例**：曲线少时把名称标在线尾 / 末点旁，优于角落图例。
- **去顶 / 右脊柱**：通过 `axis_spec.show_top_spine=False`、`show_right_spine=False` 只留左 / 下脊柱。
- **默认不画网格线**：`style_spec.axes_grid` 默认 False；确需参考线时用低 alpha 的少量主刻度线。
- **不靠颜色单独区分系列**：叠加线型 / 点型 / 纹理（见 `helpers.apply_print_safe_hatching`），保证灰度与色盲可读。
- **收紧坐标轴留白**：数据集中时用 `helpers.tighten_y_axis` 提升信息密度，避免大片空白。
- **删装饰**：阴影、3D、渐变填充、重边框一律默认不用。

## 4. 布局推荐

| 表达场景 | 推荐 layout | 推荐 axis_mode | 说明 |
|---|---|---|---|
| 单一核心关系 | `single` | `independent` | 适合一张主图，如剂量-响应、相关关系、时间曲线 |
| 单图但内容较宽 | `double` | `independent` | 适合长标签、宽时间轴、复杂图例 |
| 两组并列比较 | `pair-1x2` | `independent` | 适合 A/B 条件、原始值/归一化值 |
| 上下两个阶段 | `pair-2x1` | `shared_axis` 或 `independent` | 适合同一 x 轴下的主结果 + 残差/附加指标 |
| 三条件横向比较 | `triple-1x3` | `independent` | 适合三种处理、三种模型、三类组织 |
| 三段纵向流程 | `triple-3x1` | `shared_axis` | 适合同一变量的三层分解 |
| 四面板综合图 | `quad-2x2` | `independent` | 适合论文主图常见 A-D 面板 |
| 横向多条件概览 | `quad-1x4` | `independent` | 适合小 multiples，但注意标签密度 |
| 纵向多指标堆叠 | `quad-4x1` | `shared_axis` | 适合同一 x 轴多个指标 |
| 六面板矩阵 | `hex-2x3` | `independent` | 适合多条件筛选、方法补充图 |
| 六面板纵向矩阵 | `hex-3x2` | `independent` | 适合较多面板但需要保持单面板可读 |

> 需要"示意图主导 + 量化面板"或"主图 + 小辅助面板"这类非对称叙事时，runtime 的均匀网格不够用，
> 在单一大轴上用 `inset_axes` 自行切分，详见 `figure-archetypes.md`。

> **`shared_axis` 是原生共享**：选用 `shared_axis` 时 runtime 走 matplotlib 原生 `sharex`/`sharey`——
> 多行布局列内共享 X、多列布局行内共享 Y，内侧面板 tick label 自动隐藏，**不要**手动
> `tick_params(labelbottom=False)`。轴标签务必用 `ctx.sharex`/`ctx.sharey` 自适应铺设（共享方向只铺边缘、独立方向逐面板铺），
> 这样用户 patch 切换 `axis_mode` 时标签自动联动，代码范式见 `SKILL.md`「轴标签自适应范式」。注意 `set_xlim`/`set_ylim`
> 会沿共享方向联动所有面板。混合面板（multi 且类型不一致）会自动降级为 `independent`。

## 5. 表达场景推荐

| 数据/问题 | 推荐表达 | 推荐补充层 | 参数提示 |
|---|---|---|---|
| 连续 x-y 关系 | scatter / line / smooth curve | 回归线、置信带、相关系数 | marker 适度透明，避免遮挡 |
| 时间序列 | line / ribbon / event markers | CI 阴影、关键事件竖线 | 共享 x 轴时减少重复 x label |
| 组间均值比较 | bar + raw points / point-range | CI/SEM、显著性标注 | 不建议只有 bar，优先展示原始点 |
| 分布比较 | violin / box / beeswarm / raincloud | 中位数、分位数、样本量 | 分布图优先展示数据形状 |
| 配对样本 | paired line / slopegraph | 每个个体连线、均值差 | 保留个体轨迹 |
| 相关矩阵 | heatmap | 分组边界、数值标注 | 色图选择要与数据正负性匹配 |
| 空间/二维密度 | hexbin / contour / KDE | colorbar、等值线 | 高密度数据减少单点遮挡 |
| 模型性能比较 | point-range / grouped bar / heatmap | 排名、误差线 | 排序比原始类别顺序更可读 |
| 消融 / 层级递进 | 单色变 alpha 的 bar / line | 层级标注 | 用 `helpers.make_ablation_colors` |
| 组成比例 | stacked bar / mosaic / alluvial | 百分比标签 | 类别过多时合并低频项 |
| 机制示意 + 数据 | custom multi-panel | 箭头、inset、标注 | 尽量避免装饰性元素过多 |

## 6. Style Priors

从 `ctx.style` 读取：

| 用途 | 推荐键 |
|---|---|
| 坐标轴标签 | `axis_label_size` |
| 刻度标签 | `tick_label_size` |
| 图例 | `legend_size`, `legend_title_size` |
| 线条 | `line_width` |
| 点大小 | `marker_size` |
| 轴线 | `axes_linewidth` |
| 标注 | `annotation_size` |

示例：

```python
style = ctx.style
ax.set_xlabel("Dose (mg/L)", fontsize=style["axis_label_size"])
ax.tick_params(labelsize=style["tick_label_size"])
```

## 7. Color Priors

从 `ctx.colors` 或 `ctx.palette()` 读取分类颜色；`ctx.color` 读取色图与预设。

推荐：

- 分类变量：优先 `okabe_ito` 或 `tableau10`
- 连续正值：顺序色图，如 `viridis`（从 `ctx.color["sequential_cmap"]` 取）
- 有正负方向：发散色图，如 `coolwarm` / `RdBu_r`（从 `ctx.color["diverging_cmap"]` 取）
- 不要用过多相近颜色表达多类别

**领域配色预设**：换配色的唯一入口是 `color_spec.palette_preset`，可选 `default` / `ml_pastel` / `imaging_dark` / `clinical_temporal` / `genomics_wave`，选定后 `ctx.color` 与 `ctx.palette()` 自动同步该领域配色（分类色板 + 顺序/发散色图 + 背景倾向）；用户显式设置的子键仍优先。各预设的领域适配、色板细节和自定义逃生口见 `references/params/palette-presets.md`。

## 8. Layout Guard Priors

布局守卫是硬安全层，但参数是可调 priors：

| 情况 | 可调参数 |
|---|---|
| 标签溢出 | `layout_guard_spec.max_side_adjust_frac` |
| 图例/colorbar 溢出 | `layout_guard_spec.max_total_scale` |
| 子图间距过窄 | `layout_guard_spec.min_subplot_gap_px`, `min_subplot_vgap_px` |
| 画布太紧 | `layout_spec.width_mm`, `layout_spec.aspect_ratio` |

AI 不应手动调用 `tight_layout/subplots_adjust/set_size_inches`，应通过参数和 layout guard 解决。

## 9. 推荐 hook 写法

```python
from runtime.helpers import add_significance_bracket, tighten_y_axis


def post_draw(ctx):
    ax = ctx.ax(0)
    ax.cla()

    style = ctx.style
    colors = ctx.colors
    df = ctx.df_override

    ax.scatter(df["x"], df["y"], s=18, color=colors[0], alpha=0.75)
    ax.set_xlabel("X label (unit)", fontsize=style["axis_label_size"])
    ax.set_ylabel("Y label (unit)", fontsize=style["axis_label_size"])

    # 反冗余：去顶/右脊柱可通过 axis_spec 配置；此处按需收紧坐标轴
    tighten_y_axis(ax, float(df["y"].min()), float(df["y"].max()), padding_pct=0.08)
```
