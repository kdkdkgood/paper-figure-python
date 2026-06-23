#!/usr/bin/env python3
"""L4 图型行为默认值。"""

from __future__ import annotations

PRIMITIVE_SPEC_DEFAULTS = {
    "line_style_cycle": ["-", "--"],
    "line_marker_cycle": ["o", ""],
    "line_markevery": 12,
    "bar_width": 0.34,
    "bar_capsize": 3.0,
    "bar_elinewidth": 1.0,
    "scatter_size": 18.0,
    "scatter_alpha": 0.75,
    "heatmap_cbar_fraction": 0.048,
    "heatmap_cbar_pad": 0.04,
}

CHART_SPEC_DEFAULTS = {
    "line": {"n_points": 120, "noise_std": 0.028},
    "scatter": {
        "fit_line": True,
    },
    "bar": {},
    "hist": {
        "n_samples": 300,
        "bins": 24,
        "alpha": 0.72,
        "density": False,
        "multicolor": False,
        "edgecolor": "#2B2B2B",
        "edgewidth": 0.85,
    },
    "box": {"n_groups": 4, "n_samples_per_group": 80, "width": 0.55, "showfliers": False, "notch": False},
    "violin": {
        "n_groups": 4,
        "n_samples_per_group": 100,
        "showmeans": False,
        "showmedians": True,
    },
    "heatmap": {"matrix_size": 6, "vmin": -1.0, "vmax": 1.0},
    "contour": {"grid_size": 80, "levels": 12, "filled": True},
    "hexbin": {"n_points": 1200, "gridsize": 26, "mincnt": 1},
    "errorbar": {"n_points": 14, "capsize": 3.0, "elinewidth": 1.0},
    "stem": {"n_points": 22, "baseline": 0.0, "linefmt": "-", "markerfmt": "o", "basefmt": "k-"},
}

COLOR_SPEC_DEFAULTS = {
    # palette_preset 是唯一的"换配色"入口；categorical_palette 默认 auto（交给 preset），
    # 仅在需要时传自定义 hex 列表作为逃生口。
    "palette_preset": "default",
    "categorical_palette": "auto",
    "sequential_cmap": "viridis",
    "diverging_cmap": "RdBu_r",
    "heatmap_cmap_mode": "sequential",
    "colorblind_safe": True,
}

DATA_SPEC_DEFAULTS = {
    "enabled": False,
    "path": "",
    "format": "auto",
    "sheet": "",
    "h5_mode": "auto",
    "h5_key": "",
    "h5_dataset": "",
    "columns": [],
    "panel_mappings": {},
    "sample_id_column": "",
}

__all__ = ["PRIMITIVE_SPEC_DEFAULTS", "CHART_SPEC_DEFAULTS", "COLOR_SPEC_DEFAULTS", "DATA_SPEC_DEFAULTS"]
