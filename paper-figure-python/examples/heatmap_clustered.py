#!/usr/bin/env python3
"""范例：聚类热图（DEMO 合成数据）。

场景：feature × sample 矩阵，含模块化结构。用谱排序（leading eigenvector，纯 numpy）对行列
重排出现块状聚类，发散色图对齐 0。配色用 genomics_wave 预设（发散 PuOr）。
"""

from __future__ import annotations

import numpy as np

from _example_base import demo_config, example_job_dir  # noqa: F401
from runtime import run_figure

CONFIG = demo_config(
    layout="double",
    overrides={"color_spec": {"palette_preset": "genomics_wave"}},
)


def _spectral_order(matrix: np.ndarray) -> np.ndarray:
    """按相关矩阵 leading eigenvector 排序（谱 seriation），纯 numpy。"""

    corr = np.corrcoef(matrix)
    corr = np.nan_to_num(corr)
    _, vecs = np.linalg.eigh(corr)
    return np.argsort(vecs[:, -1])


def pre_draw(ctx):
    rng = np.random.default_rng(20260620)
    n_feat, n_samp = 24, 16
    M = rng.normal(0, 0.4, size=(n_feat, n_samp))
    # 注入 3 个模块块状信号
    M[:8, :6] += 1.1
    M[8:16, 6:11] -= 1.0
    M[16:, 11:] += 0.9
    # 打乱后再靠谱排序还原聚类结构
    M = M[rng.permutation(n_feat)][:, rng.permutation(n_samp)]
    ctx.df_override = {
        "matrix": M,
        "rows": [f"G{idx:02d}" for idx in range(n_feat)],
        "cols": [f"S{idx:02d}" for idx in range(n_samp)],
    }


def post_draw(ctx):
    ax = ctx.ax(0)
    ax.cla()
    style = ctx.style
    d = ctx.df_override
    M = np.asarray(d["matrix"], float)

    row_order = _spectral_order(M)
    col_order = _spectral_order(M.T)
    M = M[row_order][:, col_order]
    rows = [d["rows"][i] for i in row_order]
    cols = [d["cols"][i] for i in col_order]

    vmax = float(np.nanmax(np.abs(M)))
    im = ax.imshow(M, aspect="auto", cmap=ctx.color["diverging_cmap"], vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right", fontsize=style["tick_label_size"])
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows, fontsize=style["tick_label_size"])
    ax.set_xlabel("Samples", fontsize=style["axis_label_size"])
    ax.set_ylabel("Features", fontsize=style["axis_label_size"])
    ctx.fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)


if __name__ == "__main__":
    out = run_figure(CONFIG, pre_draw=pre_draw, post_draw=post_draw, job_dir=example_job_dir(__file__))
    print(f"[OK] {out}")
