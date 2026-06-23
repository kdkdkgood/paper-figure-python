#!/usr/bin/env python3
"""范例：分组柱状图 + 显著性标注（DEMO 合成数据）。

场景：少数类别下两种方法的均值比较，叠加原始点、误差线、显著性括号与打印安全纹理。
配色用 ml_pastel 预设；去顶/右脊柱体现反冗余。
"""

from __future__ import annotations

import numpy as np

from _example_base import demo_config, example_job_dir  # noqa: F401  (先导入以配置 sys.path)
from runtime import run_figure
from runtime.helpers import add_significance_bracket, apply_print_safe_hatching, tighten_y_axis

CONFIG = demo_config(
    layout="single",
    overrides={
        "color_spec": {"palette_preset": "ml_pastel"},
        "axis_spec": {"show_top_spine": False, "show_right_spine": False},
    },
)

CATEGORIES = ["Cond. I", "Cond. II", "Cond. III", "Cond. IV"]


def pre_draw(ctx):
    rng = np.random.default_rng(7)
    n = 12
    base = np.array([4.0, 5.2, 6.1, 5.6])
    ctx.df_override = {
        "labels": CATEGORIES,
        "A": rng.normal(base, 0.6, size=(n, 4)),
        "B": rng.normal(base + 1.1, 0.6, size=(n, 4)),
    }


def post_draw(ctx):
    ax = ctx.ax(0)
    ax.cla()
    style, colors = ctx.style, ctx.palette(2)
    g = ctx.df_override
    x = np.arange(len(g["labels"]))
    w = 0.36

    bar_tops = []
    for i, key in enumerate(("A", "B")):
        vals = g[key]
        mean, sem = vals.mean(0), vals.std(0) / np.sqrt(vals.shape[0])
        bars = ax.bar(
            x + (i - 0.5) * w, mean, w, yerr=sem, capsize=3,
            color=colors[i], edgecolor="#333333", linewidth=0.6, label=f"Method {key}",
        )
        apply_print_safe_hatching(bars, "" if i == 0 else "//")
        # 原始点抖动叠加
        jitter = np.random.default_rng(i).normal(0, 0.04, vals.shape)
        ax.scatter(
            (x + (i - 0.5) * w)[None, :] + jitter, vals,
            s=8, color="#33333355", edgecolor="none", zorder=3,
        )
        bar_tops.append(mean + sem)

    ax.set_xticks(x)
    ax.set_xticklabels(g["labels"], fontsize=style["tick_label_size"])
    ax.set_ylabel("Response (a.u.)", fontsize=style["axis_label_size"])
    tighten_y_axis(ax, 0.0, float(np.max(bar_tops)) * 1.28)

    y_top = ax.get_ylim()[1]
    add_significance_bracket(ax, x[0] - 0.5 * w, x[0] + 0.5 * w, y=y_top * 0.80, p=0.004)
    add_significance_bracket(ax, x[2] - 0.5 * w, x[2] + 0.5 * w, y=y_top * 0.82, p=0.03)
    ax.legend(fontsize=style["legend_size"], frameon=False, loc="upper right")


if __name__ == "__main__":
    out = run_figure(CONFIG, pre_draw=pre_draw, post_draw=post_draw, job_dir=example_job_dir(__file__))
    print(f"[OK] {out}")
