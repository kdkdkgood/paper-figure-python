#!/usr/bin/env python3
"""范例：散点 + 回归 + 边际分布（DEMO 合成数据）。

场景：两连续变量的相关关系。主轴画散点 + 线性拟合 + 相关系数；
用 inset_axes 在顶部/右侧挂边际直方图（非对称版面，thin runtime 单大轴 + inset）。
"""

from __future__ import annotations

import numpy as np

from _example_base import demo_config, example_job_dir  # noqa: F401
from runtime import run_figure

CONFIG = demo_config(
    layout="double",
    overrides={"axis_spec": {"show_top_spine": False, "show_right_spine": False}},
)


def pre_draw(ctx):
    rng = np.random.default_rng(3)
    x = rng.normal(50, 12, 220)
    y = 0.8 * x + rng.normal(0, 8, x.size) + 5
    ctx.df_override = {"x": x, "y": y}


def post_draw(ctx):
    ax = ctx.ax(0)
    ax.cla()
    style, colors = ctx.style, ctx.palette(1)
    d = ctx.df_override
    x, y = np.asarray(d["x"], float), np.asarray(d["y"], float)

    ax.scatter(x, y, s=16, alpha=0.6, color=colors[0], edgecolor="none")
    k, b = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 60)
    ax.plot(xs, k * xs + b, color="#C44E52", lw=style["line_width"])
    r = float(np.corrcoef(x, y)[0, 1])
    ax.text(0.04, 0.95, f"r = {r:.2f}", transform=ax.transAxes, va="top",
            fontsize=style["annotation_size"])
    ax.set_xlabel("Predictor (unit)", fontsize=style["axis_label_size"])
    ax.set_ylabel("Outcome (unit)", fontsize=style["axis_label_size"])

    # 边际分布（inset，极简刻度）
    ax_top = ax.inset_axes([0.0, 1.02, 1.0, 0.16])
    ax_top.hist(x, bins=26, color=colors[0], alpha=0.7)
    ax_top.axis("off")
    ax_right = ax.inset_axes([1.02, 0.0, 0.16, 1.0])
    ax_right.hist(y, bins=26, orientation="horizontal", color=colors[0], alpha=0.7)
    ax_right.axis("off")


if __name__ == "__main__":
    out = run_figure(CONFIG, pre_draw=pre_draw, post_draw=post_draw, job_dir=example_job_dir(__file__))
    print(f"[OK] {out}")
