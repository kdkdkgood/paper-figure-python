# 06 — 雨云图（raincloud）

**意图判据**：少数组（2-5）想同时展示**分布形状 + 原始点 + 摘要统计**，比单纯箱线信息更全。

**推荐 layout**：`single`（横向若干组）。

**关键 API**：

- 半个小提琴（云）：`ax.violinplot([vals], positions=[p], showextrema=False)` 后裁掉一半，或用
  `body.get_paths()` 仅保留单侧。
- 原始点（雨）：`ax.scatter(p + jitter, vals, s=8, alpha=0.5)`，jitter 用小幅正态。
- 摘要（伞）：`ax.boxplot([vals], positions=[p], widths=0.1, showfliers=False)` 或中位数 + IQR 线。
- 配色：每组一色 `ctx.palette(n)`。

**常见陷阱**：

- 云、雨、伞挤在同一 x——给三者各留偏移（云在上、雨在下、伞居中）。
- 点太多盖住云——降 alpha / 抽样展示。
- 组间 x 间距太密——增大 `positions` 间隔。

**post_draw 骨架**：

```python
def post_draw(ctx):
    import numpy as np
    ax = ctx.ax(0); ax.cla()
    style, colors = ctx.style, ctx.palette(4)
    groups = ctx.df_override                    # [{"name","values"}...]
    for i, g in enumerate(groups):
        v = np.asarray(g["values"], float); p = i
        vp = ax.violinplot([v], positions=[p + 0.12], widths=0.5, showextrema=False)
        for b in vp["bodies"]:
            b.set_facecolor(colors[i]); b.set_alpha(0.5); b.set_edgecolor("none")
        ax.scatter(p - 0.18 + np.random.normal(0, 0.03, v.size), v, s=7,
                   color=colors[i], alpha=0.5, edgecolor="none")
        ax.boxplot([v], positions=[p], widths=0.08, showfliers=False)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([g["name"] for g in groups], fontsize=style["tick_label_size"])
    ax.set_ylabel("Value (unit)", fontsize=style["axis_label_size"])
```

> 注：雨云图的抖动点用 `np.random.normal` 仅做视觉 jitter（非伪造数据），可接受。
