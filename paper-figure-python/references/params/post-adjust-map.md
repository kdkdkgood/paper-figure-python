<!-- 条件读取：仅在「看图后按用户意图选 patch 参数」时读取此速查表 -->

# 后调整映射速查（用户意图 → patch 参数）

`fast_patch` 默认增量深合并：新 patch 基于当前 `plot.py` 的 CONFIG 合并，不必重复上次已调过的参数。

| 用户意图 | 优先 patch |
|---|---|
| 字太小/线太细/点太小 | `style_spec.axis_label_size/tick_label_size/line_width/marker_size` |
| 整体图框比例要改变 | `layout_spec.aspect_ratio` |
| 图框要 1:1 | `layout_spec.aspect_ratio=1.0` |
| 整体更宽松 | `layout_guard_spec.intent="roomy"` 和 `preferred_canvas_scale` |
| 主图区域不要被边距挤小 | `layout_guard_spec.intent="preserve_data"` |
| 标签或色条被裁 | `layout_guard_spec.max_total_scale`、`crop_spec.padding_px`、必要时 `layout_spec.width_mm` |
| 字图编号放到 X 轴标题下方 | `panel_label_spec.mode="outside"` |
| 字图编号放回子图内部 | `panel_label_spec.mode="inside"` |
| 字图编号挪到其他角 | `panel_label_spec.corner="top_right"`（top_left/top_right/bottom_left/bottom_right）|
| 字图编号离 X 轴标题太近/太远 | `panel_label_spec.xlabel_gap_pt`（pt，仅 outside）|
| 不要字图编号 | `panel_label_spec.mode="off"` |
| 编号改小写 a/b/c 或去括号 | `panel_label_spec.label_style="lower"`（upper_paren/lower_paren/upper/lower）|

备份：默认备份旧 `plot.py`；测试可用 `--backup-dir .patch_backups`，不想备份用 `--no-backup`。
