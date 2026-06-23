#!/usr/bin/env python3
"""可选的纯 ax 工具函数层（thin runtime 的非侵入扩展）。

设计约束：
- 全部基于传入的 ``ax`` / 容器对象工作，不接管控制流、不创建 Figure、不调用
  ``tight_layout`` / ``subplots_adjust`` / ``set_size_inches``，因此与布局守卫不冲突。
- AI 在 ``AI_EDIT_ZONE:post_draw`` 中按需取用，也可以完全自己实现，不强制依赖。

用法::

    from runtime.helpers import add_panel_label, add_significance_bracket

    def post_draw(ctx):
        ax = ctx.ax(0)
        ...
        add_significance_bracket(ax, 0, 1, y=top + 0.5, p=0.003)
        add_panel_label(ax, "a")
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

import numpy as np
from matplotlib.colors import to_rgb

# thin 模式下面板编号由 AI 负责；用独立 gid 标记，避免与 legacy 编号块（若被启用）冲突。
_USER_PANEL_LABEL_GID = "pf_user_panel_label"

_PANEL_LABEL_POSITIONS = {
    "top_left": (0.02, 0.97, "left", "top"),
    "top_right": (0.98, 0.97, "right", "top"),
    "bottom_left": (0.02, 0.03, "left", "bottom"),
    "bottom_right": (0.98, 0.03, "right", "bottom"),
}


# --- 颜色 / 视觉 -------------------------------------------------------------

def _relative_luminance(hex_color: str) -> float:
    """sRGB 相对亮度（WCAG 定义），范围 [0, 1]。"""

    r, g, b = to_rgb(hex_color)

    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def is_dark(hex_color: str, threshold: float = 0.35) -> bool:
    """判断颜色是否偏暗（用于决定其上文字取浅色还是深色）。"""

    return _relative_luminance(hex_color) < float(threshold)


def luminance_aware_text_color(bg_hex: str, *, light: str = "#FFFFFF", dark: str = "#111111") -> str:
    """根据背景亮度返回可读的文字颜色。"""

    return light if is_dark(bg_hex) else dark


def make_ablation_colors(
    base_hex: str,
    n: int,
    *,
    alpha_range: tuple[float, float] = (0.30, 1.0),
) -> list[tuple[float, float, float, float]]:
    """单色 + 线性变 alpha 的消融配色（层级递进，最后一档最实）。

    返回 RGBA 元组列表，可直接传给 ``color=`` / ``facecolor=``。
    """

    count = max(1, int(n))
    r, g, b = to_rgb(base_hex)
    lo, hi = float(alpha_range[0]), float(alpha_range[1])
    if count == 1:
        return [(r, g, b, hi)]
    alphas = np.linspace(lo, hi, count)
    return [(r, g, b, float(a)) for a in alphas]


def apply_print_safe_hatching(
    container: Any,
    pattern: str | Sequence[str] = "//",
    *,
    edgecolor: str | None = "#222222",
) -> None:
    """为柱/区域填充叠加纹理，确保灰度打印或色盲下仍可区分。

    ``container`` 可为 ``BarContainer``、patch 列表或单个 patch；``pattern`` 支持
    单个或多个（按容器顺序循环）。
    """

    if hasattr(container, "patches"):
        patches = list(container.patches)
    elif isinstance(container, (list, tuple)):
        patches = list(container)
    else:
        patches = [container]

    patterns = [pattern] if isinstance(pattern, str) else list(pattern)
    if not patterns:
        return
    for idx, patch in enumerate(patches):
        try:
            patch.set_hatch(patterns[idx % len(patterns)])
            if edgecolor is not None:
                patch.set_edgecolor(edgecolor)
        except Exception:
            continue


# --- 轴控制 -----------------------------------------------------------------

def tighten_y_axis(
    ax: Any,
    data_min: float | None = None,
    data_max: float | None = None,
    *,
    padding_pct: float = 0.10,
) -> None:
    """按数据范围 + 留白比例收紧 y 轴，避免大片空白稀释信息密度。

    未显式给定 ``data_min/data_max`` 时，从已绘制数据范围推导。
    """

    if data_min is None or data_max is None:
        lo, hi = ax.dataLim.intervaly
        if data_min is None:
            data_min = lo
        if data_max is None:
            data_max = hi

    values = np.asarray([data_min, data_max], dtype=float)
    if not np.isfinite(values).all() or float(data_max) <= float(data_min):
        return
    pad = (float(data_max) - float(data_min)) * float(padding_pct)
    ax.set_ylim(float(data_min) - pad, float(data_max) + pad)


def style_dark_image_ax(
    ax: Any,
    bg: str = "#000000",
    *,
    hide_spines: bool = True,
    hide_ticks: bool = True,
) -> Any:
    """把轴置为暗背景成像面板（黑底、去脊柱、去刻度）。

    注意：runtime 在 ``post_draw`` 之后会按 ``axis_spec`` 重置 top/right 脊柱可见性，
    暗背景面板建议同时在 CONFIG 传入 ``axis_spec={"show_top_spine": False,
    "show_right_spine": False}``，以保证四周脊柱都隐藏。
    """

    ax.set_facecolor(bg)
    if hide_spines:
        for spine in ax.spines.values():
            spine.set_visible(False)
    if hide_ticks:
        ax.set_xticks([])
        ax.set_yticks([])
    return ax


# --- 标注 -------------------------------------------------------------------

def add_panel_label(
    ax: Any,
    label: str,
    position: str = "top_left",
    *,
    fontsize: float | None = None,
    fontweight: str = "bold",
    color: str = "#111111",
    offset: tuple[float, float] = (0.0, 0.0),
) -> Any:
    """在子图内角落添加面板编号（如 ``a`` / ``A``）。

    thin 模式下 runtime **不会**自动编号，面板编号由 AI 负责，本函数即标准做法：
    多面板时对每个 ``ctx.ax(i)`` 调用一次。使用独立 gid，不与 legacy 编号块冲突。
    """

    pos = _PANEL_LABEL_POSITIONS.get(str(position), _PANEL_LABEL_POSITIONS["top_left"])
    x, y, ha, va = pos
    text = ax.text(
        x + float(offset[0]),
        y + float(offset[1]),
        str(label),
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=fontsize,
        fontweight=fontweight,
        color=color,
    )
    try:
        text.set_gid(_USER_PANEL_LABEL_GID)
    except Exception:
        pass
    return text


def p_to_stars(p_value: float, *, ns: str = "n.s.") -> str:
    """p 值 -> 星标（``***/**/*``），不显著返回 ``ns``。"""

    p = float(p_value)
    if p <= 0.001:
        return "***"
    if p <= 0.01:
        return "**"
    if p <= 0.05:
        return "*"
    return ns


def add_significance_bracket(
    ax: Any,
    x1: float,
    x2: float,
    y: float,
    *,
    p: float | None = None,
    text: str | None = None,
    tick_height: float | None = None,
    color: str = "#222222",
    linewidth: float = 1.0,
    fontsize: float | None = None,
    text_pad: float | None = None,
) -> None:
    """在 ``x1``-``x2`` 之间、高度 ``y`` 处绘制显著性括号并标注星标 / 文本。

    ``text`` 优先；否则由 ``p`` 经 :func:`p_to_stars` 推导。``tick_height`` / ``text_pad``
    未给定时按当前 y 轴跨度自适应。
    """

    label = text if text is not None else (p_to_stars(p) if p is not None else "")
    y0, y1 = ax.get_ylim()
    span = abs(float(y1) - float(y0)) or 1.0
    th = float(tick_height) if tick_height is not None else 0.02 * span
    pad = float(text_pad) if text_pad is not None else 0.01 * span

    ax.plot(
        [x1, x1, x2, x2],
        [y - th, y, y, y - th],
        lw=float(linewidth),
        color=color,
        clip_on=False,
        solid_capstyle="butt",
    )
    if label:
        ax.text(
            (float(x1) + float(x2)) / 2.0,
            y + pad,
            label,
            ha="center",
            va="bottom",
            color=color,
            fontsize=fontsize,
        )


__all__ = [
    "is_dark",
    "luminance_aware_text_color",
    "make_ablation_colors",
    "apply_print_safe_hatching",
    "tighten_y_axis",
    "style_dark_image_ax",
    "add_panel_label",
    "p_to_stars",
    "add_significance_bracket",
]
