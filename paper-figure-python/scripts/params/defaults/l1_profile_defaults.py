#!/usr/bin/env python3
"""L1 风格档位与层叠规则。"""

from __future__ import annotations

from copy import deepcopy

from .l2_style_defaults import STYLE_SPEC_DEFAULTS

PROFILE_DPI = {
    "thesis-journal": {"photo": 600, "line": 1000, "combo": 600},
    "general": {"photo": 300, "line": 600, "combo": 500},
    "elsevier": {"photo": 300, "line": 1000, "combo": 500},
    "ieee": {"photo": 300, "line": 600, "combo": 500},
    "plos": {"photo": 300, "line": 600, "combo": 600},
}

STYLE_LAYERS = {
    "base": {
        "style_spec": {},
        "mpl_rc": {
            "text.usetex": False,
            "axes.grid": False,
            "grid.alpha": 0.3,
            "grid.linewidth": 0.5,
        },
    },
    "paper-serif": {
        "style_spec": {"font_family": "Times New Roman"},
        "mpl_rc": {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "mathtext.rm": "Times New Roman",
            "mathtext.it": "Times New Roman:italic",
        },
    },
    "paper-sans": {
        "style_spec": {"font_family": "Arial"},
        "mpl_rc": {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "mathtext.fontset": "dejavusans",
            "mathtext.rm": "Arial",
            "mathtext.it": "Arial:italic",
        },
    },
    "journal-ieee": {
        "style_spec": {
            "title_size": 8.0,
            "axis_label_size": 8.0,
            "tick_label_size": 7.0,
            "annotation_size": 7.5,
            "legend_size": 7.0,
            "legend_title_size": 7.5,
            "line_width": 1.0,
            "marker_size": 3.8,
            "axes_linewidth": 0.6,
        },
    },
    "journal-nature": {
        "style_spec": {
            "font_family": "Arial",
            "title_size": 8.0,
            "axis_label_size": 7.0,
            "tick_label_size": 7.0,
            "annotation_size": 7.0,
            "legend_size": 7.0,
            "legend_title_size": 7.0,
            "line_width": 1.0,
            "marker_size": 3.0,
            "axes_linewidth": 0.5,
        },
    },
    "journal-elsevier": {
        "style_spec": {
            "title_size": 10.0,
            "axis_label_size": 10.0,
            "tick_label_size": 8.5,
            "annotation_size": 8.5,
            "legend_size": 8.5,
            "legend_title_size": 9.0,
            "line_width": 1.2,
            "marker_size": 4.0,
            "axes_linewidth": 0.8,
        },
    },
    "journal-plos": {
        "style_spec": {
            "font_family": "Arial",
            "title_size": 11.0,
            "axis_label_size": 10.0,
            "tick_label_size": 9.0,
            "annotation_size": 9.0,
            "legend_size": 9.0,
            "legend_title_size": 9.5,
            "line_width": 1.2,
            "marker_size": 4.5,
            "axes_linewidth": 0.8,
        },
    },
    "presentation": {
        "style_spec": {
            "title_size": 14.0,
            "axis_label_size": 13.0,
            "tick_label_size": 11.0,
            "annotation_size": 11.0,
            "legend_size": 11.0,
            "legend_title_size": 11.0,
            "line_width": 1.8,
            "marker_size": 6.0,
            "axes_linewidth": 1.0,
        },
    },
    "grid": {
        "style_spec": {},
        "mpl_rc": {"axes.grid": True, "grid.alpha": 0.35},
    },
    "no-latex": {
        "style_spec": {},
        "mpl_rc": {"text.usetex": False},
    },
}

STYLE_PROFILES = {
    "paper-serif": ["base", "paper-serif", "no-latex"],
    "paper-sans": ["base", "paper-sans", "no-latex"],
    "ieee": ["base", "paper-serif", "journal-ieee", "no-latex"],
    "nature": ["base", "paper-sans", "journal-nature", "no-latex"],
    "elsevier": ["base", "paper-serif", "journal-elsevier", "no-latex"],
    "plos": ["base", "paper-sans", "journal-plos", "no-latex"],
    "presentation": ["base", "paper-serif", "presentation", "no-latex", "grid"],
}

DEFAULT_STYLE_PROFILE = "elsevier"

LOCAL_STYLE_STACK_OVERRIDES = {
    "compact": {
        "axis_label_size": 9.0,
        "tick_label_size": 8.0,
        "legend_size": 8.0,
        "annotation_size": 8.0,
    },
    "bold-lines": {"line_width": 1.8, "axes_linewidth": 1.0},
}


def _deep_update(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def resolve_style_stack(
    profile: str | None = None,
    stack: list[str] | tuple[str, ...] | None = None,
) -> tuple[list[str], dict, dict]:
    if stack:
        stack_names = [name for name in stack if name]
    else:
        profile_name = profile or DEFAULT_STYLE_PROFILE
        layers = STYLE_PROFILES.get(profile_name)
        if layers is None:
            raise KeyError(f"Unknown style profile: {profile_name}")
        stack_names = list(layers)

    merged_style_spec = deepcopy(STYLE_SPEC_DEFAULTS)
    merged_mpl_rc: dict = {}
    for layer_name in stack_names:
        layer = STYLE_LAYERS.get(layer_name)
        if layer is None:
            raise KeyError(f"Unknown style layer: {layer_name}")
        style_patch = layer.get("style_spec", {})
        mpl_rc_patch = layer.get("mpl_rc", {})
        if isinstance(style_patch, dict):
            _deep_update(merged_style_spec, deepcopy(style_patch))
        if isinstance(mpl_rc_patch, dict):
            _deep_update(merged_mpl_rc, deepcopy(mpl_rc_patch))

    return stack_names, merged_style_spec, merged_mpl_rc


__all__ = [
    "DEFAULT_STYLE_PROFILE",
    "LOCAL_STYLE_STACK_OVERRIDES",
    "PROFILE_DPI",
    "STYLE_LAYERS",
    "STYLE_PROFILES",
    "resolve_style_stack",
]
