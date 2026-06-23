#!/usr/bin/env python3
"""参数层级归属与键约束。"""

from __future__ import annotations

from params.defaults.l1_profile_defaults import LOCAL_STYLE_STACK_OVERRIDES
from params.defaults.l1_profile_defaults import STYLE_LAYERS
from params.defaults.l1_profile_defaults import STYLE_PROFILES
from params.defaults.l1_profile_defaults import resolve_style_stack
from params.defaults.l3_layout_defaults import ADJUST_SPEC_DEFAULTS
from params.defaults.l3_layout_defaults import LAYOUT_SPEC_DEFAULTS
from params.defaults.l4_chart_defaults import CHART_SPEC_DEFAULTS

LAYER_KEYS = {
    "l0_route": {
        "chart_type",
        "layout",
        "axis_mode",
        "library",
        "art_type",
        "multi_order",
    },
    "l1_profile": {"style_profile", "style_stack"},
    "l2_style_tokens": {"style_spec"},
    "l3_layout_geometry": {"layout_spec", "adjust_spec"},
    "l4_chart_behavior": {"chart_spec", "primitive_spec", "color_spec", "data_spec"},
    "l5_render_policy": {
        "axis_spec",
        "legend_spec",
        "panel_label_spec",
        "crop_spec",
        "layout_guard_spec",
    },
    "l6_runtime_derived": {
        "requested_axis_mode",
        "effective_axis_mode",
        "panel_types",
        "share_axes",
    },
}

TOP_LEVEL_OVERRIDE_KEYS = {
    "style_spec",
    "layout_spec",
    "adjust_spec",
    "adjust_by_layout",
    "axis_spec",
    "legend_spec",
    "panel_label_spec",
    "primitive_spec",
    "chart_spec",
    "color_spec",
    "data_spec",
    "crop_spec",
    "layout_guard_spec",
    "multi_order",
    "dpi",
    "extra_config",
}

LAYOUT_SPEC_KEYS = {"width_mm", "aspect_ratio", "nrows", "ncols"}
ADJUST_KEYS = {"left", "right", "top", "bottom", "wspace", "hspace"}
AXIS_SPEC_KEYS = {
    "tick_direction",
    "tick_length",
    "tick_width",
    "show_top_spine",
    "show_right_spine",
    "minor_ticks",
}
LEGEND_SPEC_KEYS = {"loc", "ncol", "frameon", "columnspacing", "borderaxespad"}
PANEL_LABEL_SPEC_KEYS = {
    "mode",
    "corner",
    "label_style",
    "inside_x",
    "inside_y",
    "outside_x",
    "xlabel_gap_pt",
    "labels",
}
PRIMITIVE_SPEC_KEYS = {
    "line_style_cycle",
    "line_marker_cycle",
    "line_markevery",
    "bar_width",
    "bar_capsize",
    "bar_elinewidth",
    "scatter_size",
    "scatter_alpha",
    "heatmap_cbar_fraction",
    "heatmap_cbar_pad",
}
COLOR_SPEC_KEYS = {
    "palette_preset",
    "categorical_palette",
    "sequential_cmap",
    "diverging_cmap",
    "heatmap_cmap_mode",
    "colorblind_safe",
}
DATA_SPEC_KEYS = {
    "enabled",
    "path",
    "format",
    "sheet",
    "h5_mode",
    "h5_key",
    "h5_dataset",
    "columns",
    "panel_mappings",
    "sample_id_column",
}
CROP_SPEC_KEYS = {
    "enabled",
    "mode",
    "alpha_threshold",
    "white_threshold",
    "padding_px",
    "keep_raw",
    "max_trim_ratio_per_axis",
}
LAYOUT_GUARD_SPEC_KEYS = {
    "enabled",
    "fallback_enabled",
    "intent",
    "preferred_canvas_scale",
    "max_fallback_passes",
    "overflow_pad_px",
    "edge_tolerance_px",
    "subplot_overlap_tolerance_px",
    "min_subplot_gap_px",
    "min_subplot_vgap_px",
    "min_inner_width_frac",
    "min_inner_height_frac",
    "max_side_adjust_frac",
    "overflow_scale_trigger_ratio",
    "subplot_hgap_ylabel_ratio",
    "subplot_vgap_xlabel_ratio",
    "panel_label_gap_ylabel_ratio",
    "max_total_scale",
    "max_scale_step_per_pass",
    "max_aspect_ratio_drift_frac",
    "max_wspace",
    "max_hspace",
    "crop_audit_enabled",
    "crop_audit_max_trim_ratio",
}

CHART_SPEC_TYPE_KEYS = {chart_type: set(spec.keys()) for chart_type, spec in CHART_SPEC_DEFAULTS.items()}
ADJUST_LAYOUT_KEYS = set(LAYOUT_SPEC_DEFAULTS.keys()) | {"single_heatmap"}


def collect_allowed_style_keys() -> set[str]:
    keys: set[str] = set()
    for profile in STYLE_PROFILES:
        _, style_spec, _ = resolve_style_stack(profile=profile, stack=None)
        keys.update(style_spec.keys())
    for layer in STYLE_LAYERS.values():
        patch = layer.get("style_spec", {})
        if isinstance(patch, dict):
            keys.update(patch.keys())
    for patch in LOCAL_STYLE_STACK_OVERRIDES.values():
        keys.update(patch.keys())
    return keys


ALLOWED_STYLE_KEYS = collect_allowed_style_keys()

__all__ = [
    "ADJUST_KEYS",
    "ADJUST_LAYOUT_KEYS",
    "ALLOWED_STYLE_KEYS",
    "AXIS_SPEC_KEYS",
    "CHART_SPEC_TYPE_KEYS",
    "COLOR_SPEC_KEYS",
    "DATA_SPEC_KEYS",
    "CROP_SPEC_KEYS",
    "LAYOUT_GUARD_SPEC_KEYS",
    "LAYOUT_SPEC_KEYS",
    "LAYER_KEYS",
    "LEGEND_SPEC_KEYS",
    "PANEL_LABEL_SPEC_KEYS",
    "PRIMITIVE_SPEC_KEYS",
    "TOP_LEVEL_OVERRIDE_KEYS",
]
