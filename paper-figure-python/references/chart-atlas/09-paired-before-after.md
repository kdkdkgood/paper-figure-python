# 09 — 配对前后 / slopegraph

**意图判据**：配对样本（同一受试者治疗前后、配对方法 A vs B）的**个体变化**，强调每条轨迹方向。

**推荐 layout**：`single`（两时点）/ `triple-1x3`（多时点分面）。

**关键 API**：

- 个体连线：对每个体 `ax.plot([0, 1], [before_i, after_i], color="#bbb", lw=0.8, alpha=0.6, zorder=1)`。
- 端点：`ax.scatter([0]*n, before, ...)` 与 `ax.scatter([1]*n, after, ...)`。
- 上升/下降着色：按 `after_i - before_i` 正负给连线不同色（如升红降蓝）。
- 均值差：叠加两端均值的粗线 + 显著性 `from runtime.helpers import add_significance_bracket`。

**常见陷阱**：

- 只画两个箱子丢了配对关系——配对的核心是连线。
- x 轴用连续刻度——两时点用类别刻度 `set_xticks([0,1])`。
- 线太多糊住——降 alpha 或按方向着色突出趋势。

**post_draw 骨架**：

```python
def post_draw(ctx):
    import numpy as np
    ax = ctx.ax(0); ax.cla()
    style = ctx.style
    d = ctx.df_override                          # {"before":[...], "after":[...]}
    before, after = np.asarray(d["before"], float), np.asarray(d["after"], float)
    up, dn = ctx.palette(2)
    for b, a in zip(before, after):
        ax.plot([0, 1], [b, a], color=(up if a >= b else dn), lw=0.9, alpha=0.55, zorder=1)
    ax.scatter([0] * before.size, before, s=20, color="#444", zorder=3)
    ax.scatter([1] * after.size, after, s=20, color="#444", zorder=3)
    ax.plot([0, 1], [before.mean(), after.mean()], color="#111", lw=2.2, zorder=4)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Before", "After"], fontsize=style["tick_label_size"])
    ax.set_ylabel("Measure (unit)", fontsize=style["axis_label_size"])
```
