#!/usr/bin/env python3
"""范例：多面板趋势 + 置信带（DEMO 合成数据）。

场景：同一训练过程下三个指标随 epoch 的走势，纵向堆叠 + shared_axis 对齐 x 轴。
每个面板画均值线 + CI 带，仅底部面板保留 x 轴标签；字图编号交给引擎托管
（panel_label_spec.mode="auto"：>=2 图自动标号，shared_axis 走内部角标）。
"""

from __future__ import annotations

import numpy as np

from _example_base import demo_config, example_job_dir  # noqa: F401
from runtime import run_figure

CONFIG = demo_config(
    layout="triple-3x1",
    axis_mode="shared_axis",
    overrides={"axis_spec": {"show_top_spine": False, "show_right_spine": False}},
)

METRICS = [("Accuracy", 0.55, 0.92), ("F1 score", 0.50, 0.88), ("AUROC", 0.60, 0.95)]


def pre_draw(ctx):
    rng = np.random.default_rng(11)
    epochs = np.arange(1, 41)
    panels = []
    for name, lo, hi in METRICS:
        curve = lo + (hi - lo) * (1 - np.exp(-epochs / 9.0))
        noise = rng.normal(0, 0.012, size=(8, epochs.size))
        runs = curve[None, :] + noise
        panels.append({
            "name": name,
            "x": epochs,
            "mean": runs.mean(0),
            "ci": 1.96 * runs.std(0) / np.sqrt(runs.shape[0]),
        })
    ctx.df_override = panels


def post_draw(ctx):
    style = ctx.style
    color = ctx.palette(3)
    panels = ctx.df_override
    axes = ctx.axes_grid.ravel()
    for i, (ax, p) in enumerate(zip(axes, panels)):
        ax.cla()
        x, m, ci = p["x"], p["mean"], p["ci"]
        ax.plot(x, m, color=color[i], lw=style["line_width"])
        ax.fill_between(x, m - ci, m + ci, color=color[i], alpha=0.18, linewidth=0)
        ax.set_ylabel(p["name"], fontsize=style["axis_label_size"])
        if i < len(axes) - 1:
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel("Epoch", fontsize=style["axis_label_size"])


if __name__ == "__main__":
    out = run_figure(CONFIG, pre_draw=pre_draw, post_draw=post_draw, job_dir=example_job_dir(__file__))
    print(f"[OK] {out}")
