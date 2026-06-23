---
path: workflow://polar/radar-label-manual-placement
scope: global
type: workflow
status: active
weight: 0.85
hits: 0
misses: 0
trigger: 
hook: 极坐标雷达图中文标签不仅逐点 ax.text()，每个标签还需独立半径 r 和 ha/va：底部标签收近避图例、左侧长标签略远避圆圈、顶部标签靠中线
created: 2026-06-23
updated: 2026-06-23
last_hit: 2026-06-23
evidence_count: 2
superseded_by: 
---

极坐标雷达图的维度标签（尤其中文多字节字符）不要用 set_xticklabels + 统一 tick_params(axis='x', pad=N)，因为各方位标签与最外圈网格的视觉间距不均。正确做法：先隐藏默认标签，再用 ax.text(angle, r, text, ha=..., va=...) 逐点手摆。r 统一设略大于 max_ylim，ha/va 按方位映射。不传 fontfamily。

## 更新 2026-06-23

极坐标雷达图中，中文维度标签不能统一定位。必须逐标签独立设定 r（径向距离）和 ha/va（水平/垂直对齐）。底部象限标签（~240°/300°）收近（r 约 10.8）以避开底部图例；左侧长标签（~180°，如'可解释性'）推远至 r≈11.5 并右对齐；顶部标签居中；右侧标签左对齐。图例放底部水平一行（ncol=N）。layout_guard 用 roomy 意图 + crop auto 自动裁边。
