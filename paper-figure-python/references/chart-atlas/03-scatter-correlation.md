# 03 — 散点 + 回归 + 边际分布

**意图判据**：两连续变量的关系，需拟合趋势、相关系数；点多时关注密度/重叠。

**推荐 layout**：`single`；要边际分布走非对称版面：`double` 大轴 + `ax.inset_axes` 顶/右挂边际直方图。

**关键 API**：

- 散点：`ax.scatter(x, y, s=18, alpha=0.7, color=colors[0], edgecolor="none")`。
- 回归：`np.polyfit` + `ax.plot`；置信带可用 bootstrap 或 `±se`。
- 相关：`scipy.stats.pearsonr` / `spearmanr`，结果写进 `ax.text`。
- 边际：`axx = ax.inset_axes([0,1.02,1,0.18]); axx.hist(x, bins=24)`；右侧同理 `orientation="horizontal"`。
- 密度大时：`ax.hexbin(x, y, gridsize=30, cmap=ctx.color["sequential_cmap"], mincnt=1)`。

**常见陷阱**：

- 点重叠成墨团——上 alpha、改 hexbin 或 KDE。
- 外推回归线超出数据范围——只在数据区间画拟合线。
- 边际轴刻度喧宾夺主——`axx.axis("off")` 或极简刻度。

**post_draw 骨架**：

```python
def post_draw(ctx):
    import numpy as np
    from scipy import stats
    ax = ctx.ax(0); ax.cla()
    style, colors = ctx.style, ctx.palette(1)
    d = ctx.df_override                        # {"x":..., "y":...}
    x, y = np.asarray(d["x"], float), np.asarray(d["y"], float)
    ax.scatter(x, y, s=18, alpha=0.7, color=colors[0], edgecolor="none")
    k, b = np.polyfit(x, y, 1); xs = np.linspace(x.min(), x.max(), 50)
    ax.plot(xs, k * xs + b, color="#C44E52", lw=style["line_width"])
    r, p = stats.pearsonr(x, y)
    ax.text(0.04, 0.95, f"r = {r:.2f}", transform=ax.transAxes, va="top",
            fontsize=style["annotation_size"])
    ax.set_xlabel("X (unit)", fontsize=style["axis_label_size"])
    ax.set_ylabel("Y (unit)", fontsize=style["axis_label_size"])
```
