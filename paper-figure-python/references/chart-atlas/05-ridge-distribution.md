# 05 — 山脊图 / 分布比较

**意图判据**：多组（5-20）连续分布的形状比较，关注偏度、峰数、整体位移。组少（≤4）时用 violin/box 即可。

**推荐 layout**：`single`（纵向堆叠的 ridgeline）/ `double`（组多需要更高画布）。

**关键 API**：

- KDE：`scipy.stats.gaussian_kde(values)` 在网格上求密度。
- 山脊：每组一条基线 `y_offset`，`ax.fill_between(grid, off, off + density*scale, alpha=0.8)` 自上而下错位。
- 单色层级：`from runtime.helpers import make_ablation_colors` 表示有序组（如剂量）。
- 替代：`ax.violinplot(data, showmedians=True)` / `ax.boxplot(data, showfliers=False)`。

**常见陷阱**：

- 山脊重叠过多糊成一片——增大行距 `y_offset` 或降低 `scale`。
- 无序类别用渐变色——渐变只对有序变量有意义，名义类别用分类色。
- 丢了样本量——在每行右侧标 `n=`。

**post_draw 骨架**：

```python
def post_draw(ctx):
    import numpy as np
    from scipy import stats
    from runtime.helpers import make_ablation_colors
    ax = ctx.ax(0); ax.cla()
    style = ctx.style
    groups = ctx.df_override                    # [{"name","values"}...] 有序
    cols = make_ablation_colors(ctx.palette(1)[0], len(groups))
    grid = np.linspace(min(min(g["values"]) for g in groups),
                       max(max(g["values"]) for g in groups), 200)
    for i, g in enumerate(groups):
        dens = stats.gaussian_kde(g["values"])(grid)
        off = i * 0.6
        ax.fill_between(grid, off, off + dens / dens.max() * 0.9, color=cols[i], alpha=0.85, lw=0.6)
    ax.set_yticks([i * 0.6 for i in range(len(groups))])
    ax.set_yticklabels([g["name"] for g in groups], fontsize=style["tick_label_size"])
    ax.set_xlabel("Value (unit)", fontsize=style["axis_label_size"])
```
