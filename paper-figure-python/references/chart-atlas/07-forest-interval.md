# 07 — 森林图 / 效应量区间

**意图判据**：多个模型/亚组/研究的**点估计 + 置信区间**对比（HR、OR、系数、效应量）。

**推荐 layout**：`single` / `double`（标签长）。临床三联的中段，见 `figure-archetypes.md` C。

**关键 API**：

- 区间：`ax.errorbar(estimate, y, xerr=[[est-lo],[hi-est]], fmt="o", capsize=3)`，y 为类别序号。
- 无效线：`ax.axvline(1.0)`（比值类）或 `ax.axvline(0.0)`（差值类），`ls="--", color="#888"`。
- 对数轴（比值）：`ax.set_xscale("log")`。
- 排序：按点估计排序，最强效应在顶部。
- 右侧数值列：`ax.text(x_right, y, f"{est:.2f} ({lo:.2f}–{hi:.2f})")`（可用第二 inset 轴）。

**常见陷阱**：

- HR/OR 用线性轴——必须对数轴，否则区间视觉失真。
- 漏画无效参考线——读者无法判断是否跨过 1/0。
- 类别未排序——乱序削弱可读性。

**post_draw 骨架**：

```python
def post_draw(ctx):
    import numpy as np
    ax = ctx.ax(0); ax.cla()
    style = ctx.style
    rows = ctx.df_override                       # [{"name","est","lo","hi"}...] 已按 est 排序
    y = np.arange(len(rows))
    est = np.array([r["est"] for r in rows]); lo = np.array([r["lo"] for r in rows]); hi = np.array([r["hi"] for r in rows])
    ax.errorbar(est, y, xerr=[est - lo, hi - est], fmt="o", color=ctx.palette(1)[0],
                capsize=3, lw=style["line_width"], markersize=style["marker_size"])
    ax.axvline(1.0, ls="--", lw=0.8, color="#888")
    ax.set_xscale("log")
    ax.set_yticks(y); ax.set_yticklabels([r["name"] for r in rows], fontsize=style["tick_label_size"])
    ax.set_xlabel("Hazard ratio (95% CI)", fontsize=style["axis_label_size"])
```
