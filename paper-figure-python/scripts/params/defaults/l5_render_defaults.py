#!/usr/bin/env python3
"""L5 渲染策略默认值。"""

from __future__ import annotations

AXIS_SPEC_DEFAULTS = {
    "tick_direction": "out",
    "tick_length": 4.0,
    "tick_width": 0.8,
    "show_top_spine": True,
    "show_right_spine": True,
    "minor_ticks": False,
}

LEGEND_SPEC_DEFAULTS = {
    "loc": "best",
    "ncol": 1,
    "frameon": False,
    "columnspacing": 1.0,
    "borderaxespad": 0.4,
}

PANEL_LABEL_SPEC_DEFAULTS = {
    "mode": "auto",
    "corner": "top_left",
    "label_style": "lower_paren",
    "inside_x": None,
    "inside_y": None,
    "outside_x": 0.5,
    "xlabel_gap_pt": None,
    "labels": None,
}

CROP_SPEC_DEFAULTS = {
    "enabled": True,
    "mode": "auto",
    "alpha_threshold": 0,
    "white_threshold": 250,
    "padding_px": 6,
    "keep_raw": False,
    "max_trim_ratio_per_axis": 0.12,
}

LAYOUT_GUARD_SPEC_DEFAULTS = {
    "enabled": True,
    "fallback_enabled": True,
    "intent": "balanced",
    "preferred_canvas_scale": 1.0,
    "max_fallback_passes": 8,
    "overflow_pad_px": 4.0,
    "edge_tolerance_px": 0.8,
    "subplot_overlap_tolerance_px": 0.8,
    "min_subplot_gap_px": 12.0,
    "min_subplot_vgap_px": 10.0,
    "min_inner_width_frac": 0.42,
    "min_inner_height_frac": 0.42,
    "max_side_adjust_frac": 0.18,
    "overflow_scale_trigger_ratio": 0.08,
    "subplot_hgap_ylabel_ratio": 0.50,
    "subplot_vgap_xlabel_ratio": 0.75,
    "panel_label_gap_ylabel_ratio": 0.15,
    "max_total_scale": 2.4,
    "max_scale_step_per_pass": 0.35,
    "max_aspect_ratio_drift_frac": 0.05,
    "max_wspace": 1.00,
    "max_hspace": 1.10,
    "crop_audit_enabled": True,
    "crop_audit_max_trim_ratio": 0.18,
}

__all__ = [
    "AXIS_SPEC_DEFAULTS",
    "CROP_SPEC_DEFAULTS",
    "LAYOUT_GUARD_SPEC_DEFAULTS",
    "LEGEND_SPEC_DEFAULTS",
    "PANEL_LABEL_SPEC_DEFAULTS",
]
