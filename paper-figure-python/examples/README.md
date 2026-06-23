# Example Gallery

可直接运行的 thin `plot.py` 范例，覆盖常见科研图型，供 Agent 创建新图时快速参考。

| 文件 | 图型 | 适用场景 | 演示要点 |
|---|---|---|---|
| [grouped_bar_significance.py](grouped_bar_significance.py) | 分组柱 + 显著性 | 组间均值比较 | `ml_pastel` 预设、误差线、原始点、显著性括号、打印安全纹理 |
| [multi_panel_trend.py](multi_panel_trend.py) | 多面板趋势 + 置信带 | 训练/时间多指标 | `triple-3x1` + `shared_axis`、CI 带、`add_panel_label` 编号 |
| [scatter_regression_marginal.py](scatter_regression_marginal.py) | 散点 + 回归 + 边际 | 两连续变量关系 | `inset_axes` 边际分布、线性拟合、相关系数 |
| [heatmap_clustered.py](heatmap_clustered.py) | 聚类热图 | 矩阵/组学数据 | `genomics_wave` 预设、谱排序聚类、发散色图对齐 0 |
| [clinical_forest.py](clinical_forest.py) | 森林图 | 效应量/亚组 | `clinical_temporal` 预设、对数轴、无效参考线、数值列 |

## 运行

```bash
/Users/pytorch/.pytorch1/bin/python examples/grouped_bar_significance.py
```

输出写到 `examples/_output/<范例名>/figure.png`（已被 .gitignore 忽略）。

## 说明

- 范例数据均为**合成 DEMO 数据**（固定随机种子），仅演示绘图模式，非真实任务数据。
- 公共构建器 `_example_base.py` 用真实参数编译链生成完整 CONFIG，并相对定位 `scripts/`，
  可移植运行。
- 真实任务请按 `SKILL.md` 工作流：`create_figure.py` 生成 job → 在 `AI_EDIT_ZONE` 绘图。
