#!/usr/bin/env python3
"""配色单一真值源：命名分类色板 + 领域预设。

这是 runtime（context/engine）与参数编译层（stage_b/jobgen_config）共享的纯数据模块，
不依赖 matplotlib，导入零副作用，避免在 thin runtime 与 create 流程间产生重复或耦合。

- ``NAMED_PALETTES``：分类色板名 -> hex 列表。
- ``PALETTE_PRESETS``：领域预设名 -> 配色 bundle（分类色板 + 顺序/发散色图 + 背景提示）。
- ``resolve_palette``：把一个 ``color_spec`` 解析成最终分类色列表（唯一解析逻辑）。
"""

from __future__ import annotations

from typing import Any


# --- 命名分类色板（hex 列表）-------------------------------------------------

NAMED_PALETTES: dict[str, list[str]] = {
    # 通用 / 色盲友好
    "okabe_ito": ["#E69F00", "#56B4E9", "#009E73", "#0072B2", "#D55E00", "#CC79A7", "#F0E442", "#000000"],
    "tableau10": ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"],
    "grayscale": ["#111111", "#333333", "#555555", "#777777", "#999999", "#BBBBBB"],
    # 机器学习 / 多方法对比：低饱和、统一色系，适合大量曲线/分组不刺眼
    "ml_pastel": ["#A1C9F4", "#FFB482", "#8DE5A1", "#FF9F9B", "#D0BBFF", "#DEBB9B", "#FAB0E4", "#CFCFCF"],
    # 显微 / 暗背景成像：高亮度荧光色，黑底上对比强
    "imaging_dark": ["#00E5FF", "#FF4FD8", "#FFE54F", "#7CFC00", "#FF8A3D", "#FFFFFF"],
    # 临床 / 时间序列：冷->暖的时间编码顺序色
    "clinical_temporal": ["#08519C", "#3182BD", "#6BAED6", "#FDAE6B", "#E6550D", "#A63603"],
    # 生物信息 / 基因组 track：高区分度 + 中性轮廓
    "genomics_wave": ["#1B9E77", "#D95F02", "#7570B3", "#E7298A", "#66A61E", "#E6AB02", "#A6761D", "#666666"],
}


# --- 领域预设 bundle ---------------------------------------------------------
#
# 每个预设把"分类色板 + 顺序色图 + 发散色图 + 热图默认取色 + 背景倾向"打包，
# 选定预设即可一次性切换到该领域的论文观感；用户显式设置的 color_spec 子键仍优先。

PALETTE_PRESETS: dict[str, dict[str, Any]] = {
    "default": {
        "categorical_palette": "tableau10",
        "sequential_cmap": "viridis",
        "diverging_cmap": "RdBu_r",
        "heatmap_cmap_mode": "sequential",
        "background": "#ffffff",
        "on_dark": False,
        "notes": "通用 / 工程：高对比，沿用现有基线行为。",
    },
    "ml_pastel": {
        "categorical_palette": "ml_pastel",
        "sequential_cmap": "cividis",
        "diverging_cmap": "RdBu_r",
        "heatmap_cmap_mode": "sequential",
        "background": "#ffffff",
        "on_dark": False,
        "notes": "机器学习 / 多方法对比：低饱和统一色系，曲线/分组多时不刺眼。",
    },
    "imaging_dark": {
        "categorical_palette": "imaging_dark",
        "sequential_cmap": "magma",
        "diverging_cmap": "RdBu_r",
        "heatmap_cmap_mode": "sequential",
        "background": "#000000",
        "on_dark": True,
        "notes": "显微 / 荧光成像：黑底高亮度配色，配合 helpers.style_dark_image_ax。",
    },
    "clinical_temporal": {
        "categorical_palette": "clinical_temporal",
        "sequential_cmap": "cividis",
        "diverging_cmap": "RdBu_r",
        "heatmap_cmap_mode": "sequential",
        "background": "#ffffff",
        "on_dark": False,
        "notes": "临床 / 时间序列：冷->暖时间编码，适合纵向随访与生存分析。",
    },
    "genomics_wave": {
        "categorical_palette": "genomics_wave",
        "sequential_cmap": "viridis",
        "diverging_cmap": "PuOr",
        "heatmap_cmap_mode": "sequential",
        "background": "#ffffff",
        "on_dark": False,
        "notes": "生物信息 / 基因组：高区分度 track 色 + 中性轮廓，发散用 PuOr。",
    },
}

DEFAULT_PRESET = "default"

PALETTE_NAMES: frozenset[str] = frozenset(NAMED_PALETTES)
PRESET_NAMES: frozenset[str] = frozenset(PALETTE_PRESETS)
# color_spec.categorical_palette 字符串仅允许 "auto"（=交给 palette_preset）；
# 具体配色一律通过 palette_preset 选择，或传自定义 hex 列表逃生口。
VALID_PALETTE_STRINGS: frozenset[str] = frozenset({"auto"})


def resolve_preset(name: Any) -> dict[str, Any]:
    """返回预设 bundle 的拷贝；未知预设回退到 default。"""

    key = str(name).strip().lower() if name is not None else DEFAULT_PRESET
    return dict(PALETTE_PRESETS.get(key, PALETTE_PRESETS[DEFAULT_PRESET]))


def resolve_palette(color_spec: Any, n: int | None = None) -> list[str]:
    """把 ``color_spec`` 解析为最终分类色列表（context/engine 共用的唯一实现）。

    单一管线，仅两种来源、零歧义：
    1. ``categorical_palette`` 传**自定义 hex 列表** → 直接采用（高级逃生口）。
    2. 其余一切情况 → 由唯一换色入口 ``palette_preset`` 决定分类色板。
    """

    if not isinstance(color_spec, dict):
        color_spec = {}

    # 逃生口：仅当显式给出非空 hex 列表时生效。
    palette_cfg = color_spec.get("categorical_palette")
    if isinstance(palette_cfg, list) and palette_cfg:
        colors = [str(item) for item in palette_cfg]
        return colors[: int(n)] if n is not None else colors

    # 主管线：palette_preset 是唯一的"换配色"语义键。
    preset = str(color_spec.get("palette_preset", DEFAULT_PRESET)).strip().lower()
    bundle = PALETTE_PRESETS.get(preset, PALETTE_PRESETS[DEFAULT_PRESET])
    name = str(bundle["categorical_palette"]).lower()
    colors = list(NAMED_PALETTES.get(name, NAMED_PALETTES["tableau10"]))
    return colors[: int(n)] if n is not None else colors


__all__ = [
    "NAMED_PALETTES",
    "PALETTE_PRESETS",
    "DEFAULT_PRESET",
    "PALETTE_NAMES",
    "PRESET_NAMES",
    "VALID_PALETTE_STRINGS",
    "resolve_preset",
    "resolve_palette",
]
