<!-- 条件读取：需要把握当代顶刊配图视觉趋势时读取此文件。属于审美 priors，非硬约束。 -->

# Nature 2026 视觉趋势观察

从近期顶刊（Nature / NMI / Nature Medicine 等）配图中提炼的视觉倾向，作为审美 priors。
这些是"当代审美偏好"，不是硬规则；与具体期刊模板冲突时，以期刊要求为准。

## 1. 配色

- **低饱和、统一色系**成为主流，尤其机器学习 / 多方法对比图（见 `palette_preset="ml_pastel"`）。
- 暗背景成像走 **cyan / magenta** 高亮度路线，在黑底上对比强（`palette_preset="imaging_dark"`）。
- 临床图偏好**时间编码色**（冷→暖表示时间推进，`palette_preset="clinical_temporal"`）。
- 顺序色图默认 **viridis / cividis / magma** 这类感知均匀、色盲友好的色图，少见 jet / rainbow。
- 发散数据用 **RdBu_r / PuOr / coolwarm**，并让 0 对齐到中性色（`vmin=-vmax, vmax=vmax`）。

## 2. 信息密度与留白

- 单图信息密度提高：直接标注取代图例，坐标轴留白收紧（见 `helpers.tighten_y_axis`）。
- 脊柱极简：普遍只留**左 / 下脊柱**，去顶 / 右；刻度向外、长度短。
- 网格线默认消失，必要时仅极淡的主刻度参考线。

## 3. 消融与层级表达

- **单色变 alpha / 变亮度**表示消融层级或剂量梯度，比多色更克制（见 `helpers.make_ablation_colors`）。
- 层级用一致色相 + 渐变明度，读者一眼看出"同一族、强度递进"。

## 4. 对比度与可读性

- **亮度感知配色**：深色背景上的文字 / 标注自动取浅色，反之取深色
  （见 `helpers.luminance_aware_text_color` / `is_dark`）。
- 打印安全：关键分组叠加纹理 / 线型，不只靠颜色（`helpers.apply_print_safe_hatching`）。

## 5. 叙事化主图（Narrative Figure）

- 主图越来越"图文一体"：机制示意 + 量化面板 + 关键标注组合在一张图里讲完整故事
  （见 `figure-archetypes.md` 的 Schematic-led Composite / Asymmetric Hero）。
- 面板分工清晰：Overview → Deviation → Relationship 递进，避免多面板重复同一信息。

## 6. 统计标注规范

- 显著性用**括号 + 星标**（`*/**/***`）就近标注，而非堆在角落
  （见 `helpers.add_significance_bracket`）。
- 误差线、样本量、检验方法标注齐全；分布图优先展示原始点 / 数据形状。

---

> 落地方式：以上趋势大多已封装在 `color_spec.palette_preset` 与 `scripts/runtime/helpers.py`，
> 直接取用即可，无需为追随趋势而手写大量样板。
