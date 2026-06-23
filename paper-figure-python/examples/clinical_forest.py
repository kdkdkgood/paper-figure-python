#!/usr/bin/env python3
"""范例：森林图 / 效应量区间（DEMO 合成数据）。

场景：多个亚组的风险比（HR）及 95% CI。对数横轴、HR=1 无效参考线、按点估计排序、
右侧数值列。配色用 clinical_temporal 预设。
"""

from __future__ import annotations

import numpy as np
from matplotlib.ticker import FixedLocator, NullLocator, ScalarFormatter

from _example_base import demo_config, example_job_dir  # noqa: F401
from runtime import run_figure

CONFIG = demo_config(
    layout="double",
    overrides={
        "color_spec": {"palette_preset": "clinical_temporal"},
        "axis_spec": {"show_top_spine": False, "show_right_spine": False},
    },
)

SUBGROUPS = ["Overall", "Age < 60", "Age ≥ 60", "Male", "Female", "Stage I–II", "Stage III–IV"]


def pre_draw(ctx):
    rng = np.random.default_rng(5)
    est = np.exp(rng.normal(-0.25, 0.3, len(SUBGROUPS)))
    half = np.abs(rng.normal(0.35, 0.08, len(SUBGROUPS)))
    rows = [
        {"name": n, "est": float(e), "lo": float(e * np.exp(-h)), "hi": float(e * np.exp(h))}
        for n, e, h in zip(SUBGROUPS, est, half)
    ]
    rows.sort(key=lambda r: r["est"])
    ctx.df_override = rows


def post_draw(ctx):
    ax = ctx.ax(0)
    ax.cla()
    style = ctx.style
    color = ctx.palette(1)[0]
    rows = ctx.df_override
    y = np.arange(len(rows))
    est = np.array([r["est"] for r in rows])
    lo = np.array([r["lo"] for r in rows])
    hi = np.array([r["hi"] for r in rows])

    ax.errorbar(
        est, y, xerr=[est - lo, hi - est], fmt="o", color=color,
        capsize=3, lw=style["line_width"], markersize=style["marker_size"],
    )
    ax.axvline(1.0, ls="--", lw=0.8, color="#888888")
    ax.set_xscale("log")
    # 对数轴上给出可读的 HR 刻度（0.4 / 0.7 / 1 / 1.5），而非默认仅 10^0
    ticks = [0.4, 0.7, 1.0, 1.5]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.set_xlim(min(lo.min(), 0.4) * 0.9, hi.max() * 1.1)
    ax.set_yticks(y)
    ax.set_yticklabels([r["name"] for r in rows], fontsize=style["tick_label_size"])
    ax.set_xlabel("Hazard ratio (95% CI)", fontsize=style["axis_label_size"])
    ax.set_ylim(-0.6, len(rows) - 0.4)

    x_text = hi.max() * 1.35
    for yi, r in zip(y, rows):
        ax.text(x_text, yi, f"{r['est']:.2f} ({r['lo']:.2f}–{r['hi']:.2f})",
                va="center", ha="left", fontsize=style["annotation_size"])


if __name__ == "__main__":
    out = run_figure(CONFIG, pre_draw=pre_draw, post_draw=post_draw, job_dir=example_job_dir(__file__))
    print(f"[OK] {out}")
