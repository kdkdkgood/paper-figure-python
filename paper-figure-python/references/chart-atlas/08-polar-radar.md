# 08 — 极坐标 / 雷达图

**意图判据**：多指标（4-10 维）的综合轮廓对比（模型多维评分、能力画像）；或周期性数据（方向、时刻）。

**推荐 layout**：`single`，在大轴上挂极坐标 inset：`ax.inset_axes([...], projection="polar")`；
或用 `figure-archetypes.md` D 非对称主图。

**关键 API**：

- 雷达：角度 `theta = np.linspace(0, 2π, n, endpoint=False)`，闭合需首尾相接。
- `pax.plot(theta_closed, vals_closed)` + `pax.fill(theta_closed, vals_closed, alpha=0.15)`。
- 轴标签：`pax.set_xticks(theta); pax.set_xticklabels(metric_names)`。
- 周期性：`projection="polar"` 直接画 `pax.bar(theta, r)` 或 `pax.plot`。

**常见陷阱**：

- 维度 >10 雷达变蛛网糊——改平行坐标或热图。
- 各指标量纲不同未归一——先 min-max / z-score 到可比范围。
- 雷达面积被误读为"总分"——必要时旁注说明。

**post_draw 骨架**：

```python
def post_draw(ctx):
    import numpy as np
    ax = ctx.ax(0); ax.set_axis_off()
    style, colors = ctx.style, ctx.palette(3)
    d = ctx.df_override                          # {"metrics":[...], "series":[{"name","values(0-1)"}...]}
    n = len(d["metrics"]); theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    theta_c = np.concatenate([theta, theta[:1]])
    pax = ax.inset_axes([0.1, 0.1, 0.8, 0.8], projection="polar")
    for i, s in enumerate(d["series"]):
        v = np.asarray(s["values"], float); v_c = np.concatenate([v, v[:1]])
        pax.plot(theta_c, v_c, color=colors[i], lw=style["line_width"], label=s["name"])
        pax.fill(theta_c, v_c, color=colors[i], alpha=0.15)
    pax.set_xticks(theta); pax.set_xticklabels(d["metrics"], fontsize=style["tick_label_size"])
    pax.set_yticklabels([])
    pax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=style["legend_size"], frameon=False)
```
