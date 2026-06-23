# 04 — 热图 / 相关矩阵 / 聚类

**意图判据**：矩阵型数据（基因×样本、相关系数、混淆矩阵）。有正负方向用发散色图，纯正值用顺序色图。

**推荐 layout**：`single` / `double`（标签长时）。需要聚类树时在 `inset_axes` 加树状图。

**关键 API**：

- 主体：`im = ax.imshow(M, aspect="auto", cmap=cmap, vmin=..., vmax=...)`。
- 发散对齐 0：`vmax = np.nanmax(np.abs(M)); vmin=-vmax`，`cmap=ctx.color["diverging_cmap"]`。
- 色条：`ctx.fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)`。
- 刻度：`ax.set_xticks(range(n)); ax.set_xticklabels(cols, rotation=45, ha="right")`。
- 数值标注（小矩阵）：`ax.text(j, i, f"{v:.2f}", ha="center", va="center", color=helpers.luminance_aware_text_color(rgba))`。
- 聚类：`scipy.cluster.hierarchy.linkage/leaves_list` 重排行列顺序。

**常见陷阱**：

- 正负数据用顺序色图——必须发散且 0 对中性。
- 大矩阵硬标数字——只在 ≤12×12 时标注。
- 行列未排序——聚类或按均值排序后可读性大增。

**post_draw 骨架**：

```python
def post_draw(ctx):
    import numpy as np
    ax = ctx.ax(0); ax.cla()
    style = ctx.style
    d = ctx.df_override                        # {"matrix":2D, "rows":[...], "cols":[...]}
    M = np.asarray(d["matrix"], float)
    vmax = float(np.nanmax(np.abs(M)))
    im = ax.imshow(M, aspect="auto", cmap=ctx.color["diverging_cmap"], vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(d["cols"]))); ax.set_xticklabels(d["cols"], rotation=45, ha="right",
                                                             fontsize=style["tick_label_size"])
    ax.set_yticks(range(len(d["rows"]))); ax.set_yticklabels(d["rows"], fontsize=style["tick_label_size"])
    ctx.fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
```
