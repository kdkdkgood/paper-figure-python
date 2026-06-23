# 01 — 分组柱状图 + 显著性

**意图判据**：少数离散类别（≤6）的均值/计数比较，需要标注组间显著性。类别很多时改用横向
dot plot 或热图。

**推荐 layout**：`single`（一组对比）/ `pair-1x2`（两套指标）。`axis_mode=independent`。

**关键 API**：

- `ax.bar(x + offset, mean, width, yerr=sem, capsize=3, color=colors[i])` 分组用 x 偏移。
- 原始点叠加：`ax.scatter(jittered_x, raw, s=10, color=..., alpha=0.6, zorder=3)`。
- 显著性：`from runtime.helpers import add_significance_bracket`。
- 灰度安全：`from runtime.helpers import apply_print_safe_hatching`。

**常见陷阱**：

- 只画柱不画原始点——优先叠加点或误差线。
- 柱子从非 0 起——均值柱基线必须为 0，否则误导。
- 显著性括号高度撞数据——用 `helpers.tighten_y_axis` 后在最高点之上留 5-8% 放括号。

**post_draw 骨架**：

```python
def post_draw(ctx):
    import numpy as np
    ax = ctx.ax(0); ax.cla()
    style, colors = ctx.style, ctx.palette(2)
    g = ctx.df_override                      # {"labels":[...], "A":[...], "B":[...]}
    x = np.arange(len(g["labels"])); w = 0.36
    for i, key in enumerate(("A", "B")):
        vals = np.asarray(g[key], float)
        ax.bar(x + (i - 0.5) * w, vals.mean(0), w, yerr=vals.std(0),
               capsize=3, color=colors[i], label=key, edgecolor="#222", linewidth=0.6)
    ax.set_xticks(x); ax.set_xticklabels(g["labels"], fontsize=style["tick_label_size"])
    ax.set_ylabel("Response (a.u.)", fontsize=style["axis_label_size"])
    from runtime.helpers import add_significance_bracket, tighten_y_axis
    tighten_y_axis(ax, 0, float(np.max([np.asarray(g[k]).mean(0).max() for k in ("A","B")])) * 1.25)
    add_significance_bracket(ax, x[0], x[1], y=ax.get_ylim()[1] * 0.88, p=0.004)
    ax.legend(fontsize=style["legend_size"], frameon=False)
```
