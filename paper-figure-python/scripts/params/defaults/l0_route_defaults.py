#!/usr/bin/env python3
"""L0 路由层默认值与路由枚举。"""

from __future__ import annotations

LAYOUT_GRID = {
    "single": {"nrows": 1, "ncols": 1},
    "double": {"nrows": 1, "ncols": 1},
    "pair-1x2": {"nrows": 1, "ncols": 2},
    "pair-2x1": {"nrows": 2, "ncols": 1},
    "triple-1x3": {"nrows": 1, "ncols": 3},
    "triple-3x1": {"nrows": 3, "ncols": 1},
    "quad-2x2": {"nrows": 2, "ncols": 2},
    "quad-1x4": {"nrows": 1, "ncols": 4},
    "quad-4x1": {"nrows": 4, "ncols": 1},
    "hex-2x3": {"nrows": 2, "ncols": 3},
    "hex-3x2": {"nrows": 3, "ncols": 2},
}

LAYOUT_TO_ADJUST_KEY = {
    "single": "single",
    "double": "single",
    "pair-1x2": "pair12",
    "pair-2x1": "pair21",
    "triple-1x3": "triple13",
    "triple-3x1": "triple31",
    "quad-2x2": "multi",
    "quad-1x4": "quad14",
    "quad-4x1": "quad41",
    "hex-2x3": "hex23",
    "hex-3x2": "hex32",
}

PANEL_TYPE_SEQUENCE = [
    "line",
    "scatter",
    "bar",
    "hist",
    "box",
    "violin",
    "heatmap",
    "contour",
    "hexbin",
    "errorbar",
    "stem",
]

SUPPORTED_PANEL_TYPES = set(PANEL_TYPE_SEQUENCE)
CHART_TYPE_CHOICES = [*PANEL_TYPE_SEQUENCE, "multi", "custom"]
DEFAULT_MULTI_ORDER = ["line", "bar", "scatter", "heatmap"]

AXIS_MODE_CHOICES = {"auto", "shared_axis", "independent"}
LIBRARY_CHOICES = {"matplotlib", "seaborn"}
ART_TYPE_CHOICES = {"line", "photo", "combo"}
