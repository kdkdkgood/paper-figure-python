# 02 — 趋势线 + 置信带

**意图判据**：连续自变量（时间/剂量/epoch）下的走势，需表达不确定性（CI/SEM）。多条曲线对比走势。

**推荐 layout**：`single`；多指标同 x 轴用 `quad-4x1` + `shared_axis`；主结果 + 残差用 `pair-2x1`。

**关键 API**：

- 主线：`ax.plot(x, mean, color=colors[i], lw=style["line_width"], label=...)`。
- 置信带：`ax.fill_between(x, mean - ci, mean + ci, color=colors[i], alpha=0.18, linewidth=0)`。
- 事件竖线：`ax.axvline(t_event, ls="--", lw=0.8, color="#888")`。
- 直接标注（反冗余）：`ax.annotate(name, xy=(x[-1], mean[-1]), xytext=(4,0), textcoords="offset points")`。

**常见陷阱**：

- 曲线 >4 条还堆一个面板——拆小倍数或直接标注末端。
- 置信带 alpha 过高盖住线——保持 0.15-0.20。
- 时间轴重复 x 刻度——`shared_axis` 下只底行保留。

**post_draw 骨架**：

```python
def post_draw(ctx):
    import numpy as np
    ax = ctx.ax(0); ax.cla()
    style, colors = ctx.style, ctx.palette(3)
    d = ctx.df_override                       # {"x":..., "series":[{"name","mean","ci"}...]}
    for i, s in enumerate(d["series"]):
        x, m, ci = np.asarray(d["x"]), np.asarray(s["mean"]), np.asarray(s["ci"])
        ax.plot(x, m, color=colors[i], lw=style["line_width"], label=s["name"])
        ax.fill_between(x, m - ci, m + ci, color=colors[i], alpha=0.18, linewidth=0)
        ax.annotate(s["name"], xy=(x[-1], m[-1]), xytext=(4, 0),
                    textcoords="offset points", va="center",
                    fontsize=style["annotation_size"], color=colors[i])
    ax.set_xlabel("Epoch", fontsize=style["axis_label_size"])
    ax.set_ylabel("Accuracy", fontsize=style["axis_label_size"])
```
