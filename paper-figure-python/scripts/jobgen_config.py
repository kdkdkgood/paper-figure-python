#!/usr/bin/env python3
"""create_figure 的配置与覆盖解析。"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any
from typing import Callable

from params.registry import build_compiled_config as build_compiled_config_v3
from params.registry import build_compiled_config_with_options as build_compiled_config_v3_with_options

from palette_registry import PRESET_NAMES
from palette_registry import VALID_PALETTE_STRINGS

from jobgen_schema import ADJUST_KEYS
from jobgen_schema import ALLOWED_STYLE_KEYS
from jobgen_schema import BASE_CHART_SPEC
from jobgen_schema import BASE_LAYOUT_SPEC
from jobgen_schema import AXIS_SPEC_KEYS
from jobgen_schema import CHART_SPEC_TYPE_KEYS
from jobgen_schema import COLOR_SPEC_KEYS
from jobgen_schema import DATA_SPEC_KEYS
from jobgen_schema import CROP_SPEC_KEYS
from jobgen_schema import LAYOUT_GUARD_SPEC_KEYS
from jobgen_schema import LAYOUT_SPEC_KEYS
from jobgen_schema import LEGEND_SPEC_KEYS
from jobgen_schema import PANEL_LABEL_SPEC_KEYS
from jobgen_schema import PRIMITIVE_SPEC_KEYS
from jobgen_schema import SUPPORTED_PANEL_TYPES
from jobgen_schema import TOP_LEVEL_OVERRIDE_KEYS


def deep_update(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def parse_style_stack(text: str) -> list[str]:
    if not text.strip():
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def slugify_task(text: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", text.strip(), flags=re.UNICODE).strip("_")
    return cleaned[:48] if cleaned else "figure_job"


def load_overrides(raw_value: str, on_file_read: Callable[[str], None] | None = None) -> dict:
    text = raw_value.strip()
    if not text:
        return {}
    if text.startswith(("{", "[")):
        loaded = json.loads(text)
        if not isinstance(loaded, dict):
            raise ValueError("overrides 必须是 JSON 对象。")
        return loaded

    possible_path = Path(text)
    if possible_path.exists():
        if on_file_read is not None:
            on_file_read(str(possible_path.resolve()))
        loaded = json.loads(possible_path.read_text(encoding="utf-8"))
    else:
        loaded = json.loads(text)

    if not isinstance(loaded, dict):
        raise ValueError("overrides 必须是 JSON 对象。")
    return loaded


def _handle_override_issue(message: str, strict: bool, warnings: list[str]) -> None:
    if strict:
        raise ValueError(message)
    warnings.append(message)


def _is_real_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_non_empty_str(value: Any, scope: str, key: str, strict: bool, warnings: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        _handle_override_issue(f"{scope}.{key} 必须是非空字符串", strict=strict, warnings=warnings)


def _validate_bool(value: Any, scope: str, key: str, strict: bool, warnings: list[str]) -> None:
    if not isinstance(value, bool):
        _handle_override_issue(f"{scope}.{key} 必须是布尔值", strict=strict, warnings=warnings)


def _validate_number(
    value: Any,
    scope: str,
    key: str,
    strict: bool,
    warnings: list[str],
    *,
    min_value: float | None = None,
    max_value: float | None = None,
) -> None:
    if not _is_real_number(value):
        _handle_override_issue(f"{scope}.{key} 必须是数值", strict=strict, warnings=warnings)
        return
    fv = float(value)
    if min_value is not None and fv < min_value:
        _handle_override_issue(f"{scope}.{key} 不能小于 {min_value}", strict=strict, warnings=warnings)
    if max_value is not None and fv > max_value:
        _handle_override_issue(f"{scope}.{key} 不能大于 {max_value}", strict=strict, warnings=warnings)


def _validate_positive_number(
    value: Any,
    scope: str,
    key: str,
    strict: bool,
    warnings: list[str],
) -> None:
    _validate_number(value, scope, key, strict, warnings, min_value=1e-9)


def _validate_int(
    value: Any,
    scope: str,
    key: str,
    strict: bool,
    warnings: list[str],
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        _handle_override_issue(f"{scope}.{key} 必须是整数", strict=strict, warnings=warnings)
        return
    if min_value is not None and value < min_value:
        _handle_override_issue(f"{scope}.{key} 不能小于 {min_value}", strict=strict, warnings=warnings)
    if max_value is not None and value > max_value:
        _handle_override_issue(f"{scope}.{key} 不能大于 {max_value}", strict=strict, warnings=warnings)


def _validate_str_list(
    value: Any,
    scope: str,
    key: str,
    strict: bool,
    warnings: list[str],
    *,
    non_empty: bool = True,
) -> list[str]:
    if not isinstance(value, list):
        _handle_override_issue(f"{scope}.{key} 必须是字符串列表", strict=strict, warnings=warnings)
        return []
    items: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str):
            _handle_override_issue(f"{scope}.{key}[{idx}] 必须是字符串", strict=strict, warnings=warnings)
            continue
        text = item.strip()
        if not text:
            _handle_override_issue(f"{scope}.{key}[{idx}] 不能为空", strict=strict, warnings=warnings)
            continue
        items.append(text)
    if non_empty and not items:
        _handle_override_issue(f"{scope}.{key} 不能为空", strict=strict, warnings=warnings)
    return items


def validate_overrides(overrides: dict, strict: bool) -> list[str]:
    warnings: list[str] = []
    unknown_top = sorted(set(overrides.keys()) - TOP_LEVEL_OVERRIDE_KEYS)
    if unknown_top:
        _handle_override_issue(
            f"overrides 含未知顶层键: {unknown_top}",
            strict=strict,
            warnings=warnings,
        )

    if "dpi" in overrides:
        _validate_int(overrides["dpi"], "overrides", "dpi", strict, warnings, min_value=1)

    if "multi_order" in overrides:
        order_raw = overrides["multi_order"]
        if isinstance(order_raw, str):
            items = [x.strip() for x in order_raw.split(",") if x.strip()]
        elif isinstance(order_raw, list):
            items = _validate_str_list(order_raw, "overrides", "multi_order", strict, warnings, non_empty=True)
        else:
            items = []
            _handle_override_issue("overrides.multi_order 必须是字符串或列表", strict=strict, warnings=warnings)

    if "extra_config" in overrides and not isinstance(overrides.get("extra_config"), dict):
        _handle_override_issue("overrides.extra_config 必须是对象", strict=strict, warnings=warnings)

    style_spec = overrides.get("style_spec")
    if style_spec is not None and not isinstance(style_spec, dict):
        _handle_override_issue("style_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(style_spec, dict):
        unknown_style = sorted(set(style_spec.keys()) - ALLOWED_STYLE_KEYS)
        if unknown_style:
            _handle_override_issue(
                f"style_spec 含未知键: {unknown_style}",
                strict=strict,
                warnings=warnings,
            )
        if "font_family" in style_spec:
            _validate_non_empty_str(style_spec["font_family"], "style_spec", "font_family", strict, warnings)
        # 尺寸/线宽类必须为正数；偏移/间距类允许负值以支持精细定位。
        for key in {
            "title_size",
            "axis_label_size",
            "tick_label_size",
            "annotation_size",
            "legend_size",
            "legend_title_size",
            "line_width",
            "marker_size",
            "axes_linewidth",
            "legend_handlelength",
            "grid_linewidth",
            "legend_markerscale",
        }:
            if key in style_spec:
                _validate_positive_number(style_spec[key], "style_spec", key, strict, warnings)
        for key in {
            "legend_handletextpad",
            "legend_borderpad",
            "legend_labelspacing",
            "ylabel_pad",
            "xlabel_pad",
            "ytick_pad",
        }:
            if key in style_spec:
                _validate_number(style_spec[key], "style_spec", key, strict, warnings)
        if "grid_alpha" in style_spec:
            _validate_number(style_spec["grid_alpha"], "style_spec", "grid_alpha", strict, warnings, min_value=0.0, max_value=1.0)
        if "axes_grid" in style_spec:
            _validate_bool(style_spec["axes_grid"], "style_spec", "axes_grid", strict, warnings)

    layout_spec = overrides.get("layout_spec")
    def _validate_layout_patch(scope: str, patch: dict) -> None:
        if "width_mm" in patch:
            _validate_number(patch["width_mm"], scope, "width_mm", strict, warnings, min_value=1e-9)
        if "aspect_ratio" in patch:
            _validate_number(patch["aspect_ratio"], scope, "aspect_ratio", strict, warnings, min_value=1e-9)
        if "nrows" in patch:
            _validate_int(patch["nrows"], scope, "nrows", strict, warnings, min_value=1)
        if "ncols" in patch:
            _validate_int(patch["ncols"], scope, "ncols", strict, warnings, min_value=1)

    if layout_spec is not None and not isinstance(layout_spec, dict):
        _handle_override_issue("layout_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(layout_spec, dict):
        if any(k in BASE_LAYOUT_SPEC for k in layout_spec.keys()):
            for layout_name, patch in layout_spec.items():
                if layout_name not in BASE_LAYOUT_SPEC:
                    _handle_override_issue(
                        f"layout_spec 含未知布局键: {layout_name}",
                        strict=strict,
                        warnings=warnings,
                    )
                    continue
                if not isinstance(patch, dict):
                    _handle_override_issue(
                        f"layout_spec.{layout_name} 必须是对象",
                        strict=strict,
                        warnings=warnings,
                    )
                    continue
                unknown_layout_keys = sorted(set(patch.keys()) - LAYOUT_SPEC_KEYS)
                if unknown_layout_keys:
                    _handle_override_issue(
                        f"layout_spec.{layout_name} 含未知键: {unknown_layout_keys}",
                        strict=strict,
                        warnings=warnings,
                    )
                _validate_layout_patch(f"layout_spec.{layout_name}", patch)
        else:
            unknown_layout_keys = sorted(set(layout_spec.keys()) - LAYOUT_SPEC_KEYS)
            if unknown_layout_keys:
                _handle_override_issue(
                    f"layout_spec 含未知键: {unknown_layout_keys}",
                    strict=strict,
                    warnings=warnings,
                )
            _validate_layout_patch("layout_spec", layout_spec)

    adjust_spec = overrides.get("adjust_spec")
    if adjust_spec is not None and not isinstance(adjust_spec, dict):
        _handle_override_issue("adjust_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(adjust_spec, dict):
        unknown_adjust = sorted(set(adjust_spec.keys()) - ADJUST_KEYS)
        if unknown_adjust:
            _handle_override_issue(
                f"adjust_spec 含未知键: {unknown_adjust}",
                strict=strict,
                warnings=warnings,
            )
        for key in ADJUST_KEYS:
            if key in adjust_spec:
                _validate_number(adjust_spec[key], "adjust_spec", key, strict, warnings)

    adjust_by_layout = overrides.get("adjust_by_layout")
    if adjust_by_layout is not None and not isinstance(adjust_by_layout, dict):
        _handle_override_issue("adjust_by_layout 必须是对象", strict=strict, warnings=warnings)
    if isinstance(adjust_by_layout, dict):
        unknown_layout_names = sorted(set(adjust_by_layout.keys()) - set(BASE_LAYOUT_SPEC.keys()))
        if unknown_layout_names:
            _handle_override_issue(
                f"adjust_by_layout 含未知布局: {unknown_layout_names}",
                strict=strict,
                warnings=warnings,
            )
        for layout_name, patch in adjust_by_layout.items():
            if not isinstance(patch, dict):
                _handle_override_issue(
                    f"adjust_by_layout.{layout_name} 必须是对象",
                    strict=strict,
                    warnings=warnings,
                )
                continue
            unknown_adjust = sorted(set(patch.keys()) - ADJUST_KEYS)
            if unknown_adjust:
                _handle_override_issue(
                    f"adjust_by_layout.{layout_name} 含未知键: {unknown_adjust}",
                    strict=strict,
                    warnings=warnings,
                )
            for key in ADJUST_KEYS:
                if key in patch:
                    _validate_number(patch[key], f"adjust_by_layout.{layout_name}", key, strict, warnings)

    axis_spec = overrides.get("axis_spec")
    if axis_spec is not None and not isinstance(axis_spec, dict):
        _handle_override_issue("axis_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(axis_spec, dict):
        unknown_axis = sorted(set(axis_spec.keys()) - AXIS_SPEC_KEYS)
        if unknown_axis:
            _handle_override_issue(
                f"axis_spec 含未知键: {unknown_axis}",
                strict=strict,
                warnings=warnings,
            )
        if "tick_direction" in axis_spec:
            tick_direction = axis_spec["tick_direction"]
            _validate_non_empty_str(tick_direction, "axis_spec", "tick_direction", strict, warnings)
            if isinstance(tick_direction, str) and tick_direction.lower() not in {"in", "out", "inout"}:
                _handle_override_issue(
                    f"axis_spec.tick_direction 不支持: {tick_direction}",
                    strict=strict,
                    warnings=warnings,
                )
        if "tick_length" in axis_spec:
            _validate_number(axis_spec["tick_length"], "axis_spec", "tick_length", strict, warnings, min_value=0.0)
        if "tick_width" in axis_spec:
            _validate_number(axis_spec["tick_width"], "axis_spec", "tick_width", strict, warnings, min_value=0.0)
        for key in {"show_top_spine", "show_right_spine", "minor_ticks"}:
            if key in axis_spec:
                _validate_bool(axis_spec[key], "axis_spec", key, strict, warnings)

    legend_spec = overrides.get("legend_spec")
    if legend_spec is not None and not isinstance(legend_spec, dict):
        _handle_override_issue("legend_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(legend_spec, dict):
        unknown_legend = sorted(set(legend_spec.keys()) - LEGEND_SPEC_KEYS)
        if unknown_legend:
            _handle_override_issue(
                f"legend_spec 含未知键: {unknown_legend}",
                strict=strict,
                warnings=warnings,
            )
        if "loc" in legend_spec:
            _validate_non_empty_str(legend_spec["loc"], "legend_spec", "loc", strict, warnings)
        if "ncol" in legend_spec:
            _validate_int(legend_spec["ncol"], "legend_spec", "ncol", strict, warnings, min_value=1)
        if "frameon" in legend_spec:
            _validate_bool(legend_spec["frameon"], "legend_spec", "frameon", strict, warnings)
        if "columnspacing" in legend_spec:
            _validate_number(legend_spec["columnspacing"], "legend_spec", "columnspacing", strict, warnings)
        if "borderaxespad" in legend_spec:
            _validate_number(legend_spec["borderaxespad"], "legend_spec", "borderaxespad", strict, warnings)

    panel_label_spec = overrides.get("panel_label_spec")
    if panel_label_spec is not None and not isinstance(panel_label_spec, dict):
        _handle_override_issue("panel_label_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(panel_label_spec, dict):
        unknown_panel = sorted(set(panel_label_spec.keys()) - PANEL_LABEL_SPEC_KEYS)
        if unknown_panel:
            _handle_override_issue(
                f"panel_label_spec 含未知键: {unknown_panel}",
                strict=strict,
                warnings=warnings,
            )
        if "mode" in panel_label_spec:
            _validate_non_empty_str(panel_label_spec["mode"], "panel_label_spec", "mode", strict, warnings)
            if isinstance(panel_label_spec["mode"], str):
                mode = panel_label_spec["mode"].lower()
                if mode not in {"auto", "inside", "outside", "off"}:
                    _handle_override_issue(
                        f"panel_label_spec.mode 不支持: {panel_label_spec['mode']}",
                        strict=strict,
                        warnings=warnings,
                    )
        if "corner" in panel_label_spec:
            _validate_non_empty_str(panel_label_spec["corner"], "panel_label_spec", "corner", strict, warnings)
            if isinstance(panel_label_spec["corner"], str):
                if panel_label_spec["corner"].lower() not in {"top_left", "top_right", "bottom_left", "bottom_right"}:
                    _handle_override_issue(
                        f"panel_label_spec.corner 不支持: {panel_label_spec['corner']}",
                        strict=strict,
                        warnings=warnings,
                    )
        if "label_style" in panel_label_spec:
            _validate_non_empty_str(panel_label_spec["label_style"], "panel_label_spec", "label_style", strict, warnings)
            if isinstance(panel_label_spec["label_style"], str):
                if panel_label_spec["label_style"].lower() not in {"upper_paren", "lower_paren", "upper", "lower"}:
                    _handle_override_issue(
                        f"panel_label_spec.label_style 不支持: {panel_label_spec['label_style']}",
                        strict=strict,
                        warnings=warnings,
                    )
        if "labels" in panel_label_spec and panel_label_spec["labels"] is not None:
            if not isinstance(panel_label_spec["labels"], (list, tuple)):
                _handle_override_issue(
                    "panel_label_spec.labels 必须是列表（元素为字符串或 null）",
                    strict=strict,
                    warnings=warnings,
                )
        for key in {"inside_x", "inside_y", "outside_x", "xlabel_gap_pt"}:
            if key in panel_label_spec and panel_label_spec[key] is not None:
                _validate_number(panel_label_spec[key], "panel_label_spec", key, strict, warnings)

    primitive_spec = overrides.get("primitive_spec")
    if primitive_spec is not None and not isinstance(primitive_spec, dict):
        _handle_override_issue("primitive_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(primitive_spec, dict):
        unknown_primitive = sorted(set(primitive_spec.keys()) - PRIMITIVE_SPEC_KEYS)
        if unknown_primitive:
            _handle_override_issue(
                f"primitive_spec 含未知键: {unknown_primitive}",
                strict=strict,
                warnings=warnings,
            )
        if "line_style_cycle" in primitive_spec:
            _validate_str_list(primitive_spec["line_style_cycle"], "primitive_spec", "line_style_cycle", strict, warnings)
        if "line_marker_cycle" in primitive_spec:
            _validate_str_list(primitive_spec["line_marker_cycle"], "primitive_spec", "line_marker_cycle", strict, warnings)
        if "line_markevery" in primitive_spec:
            _validate_int(primitive_spec["line_markevery"], "primitive_spec", "line_markevery", strict, warnings, min_value=1)
        if "bar_width" in primitive_spec:
            _validate_number(primitive_spec["bar_width"], "primitive_spec", "bar_width", strict, warnings, min_value=1e-9)
        if "bar_capsize" in primitive_spec:
            _validate_number(primitive_spec["bar_capsize"], "primitive_spec", "bar_capsize", strict, warnings, min_value=0.0)
        if "bar_elinewidth" in primitive_spec:
            _validate_number(primitive_spec["bar_elinewidth"], "primitive_spec", "bar_elinewidth", strict, warnings, min_value=0.0)
        if "scatter_size" in primitive_spec:
            _validate_number(primitive_spec["scatter_size"], "primitive_spec", "scatter_size", strict, warnings, min_value=1e-9)
        if "scatter_alpha" in primitive_spec:
            _validate_number(primitive_spec["scatter_alpha"], "primitive_spec", "scatter_alpha", strict, warnings, min_value=0.0, max_value=1.0)
        if "heatmap_cbar_fraction" in primitive_spec:
            _validate_number(
                primitive_spec["heatmap_cbar_fraction"],
                "primitive_spec",
                "heatmap_cbar_fraction",
                strict,
                warnings,
                min_value=1e-9,
            )
        if "heatmap_cbar_pad" in primitive_spec:
            _validate_number(primitive_spec["heatmap_cbar_pad"], "primitive_spec", "heatmap_cbar_pad", strict, warnings)

    chart_spec = overrides.get("chart_spec")
    if chart_spec is not None and not isinstance(chart_spec, dict):
        _handle_override_issue("chart_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(chart_spec, dict):
        unknown_types = sorted(set(chart_spec.keys()) - set(CHART_SPEC_TYPE_KEYS.keys()))
        if unknown_types:
            warnings.append(f"chart_spec 含非内置键，将仅作为自定义绘图元数据保留: {unknown_types}")
        for chart_type, patch in chart_spec.items():
            if chart_type not in CHART_SPEC_TYPE_KEYS:
                continue
            if not isinstance(patch, dict):
                _handle_override_issue(
                    f"chart_spec.{chart_type} 必须是对象",
                    strict=strict,
                    warnings=warnings,
                )
                continue
            allowed_keys = CHART_SPEC_TYPE_KEYS[chart_type]
            unknown_patch_keys = sorted(set(patch.keys()) - allowed_keys)
            if unknown_patch_keys:
                _handle_override_issue(
                    f"chart_spec.{chart_type} 含未知键: {unknown_patch_keys}",
                    strict=strict,
                    warnings=warnings,
                )
            defaults = BASE_CHART_SPEC.get(chart_type, {})
            for key, value in patch.items():
                if key not in defaults:
                    continue
                default = defaults[key]
                scope = f"chart_spec.{chart_type}"
                if isinstance(default, bool):
                    _validate_bool(value, scope, key, strict, warnings)
                elif isinstance(default, int):
                    _validate_int(value, scope, key, strict, warnings, min_value=0)
                elif isinstance(default, float):
                    _validate_number(value, scope, key, strict, warnings)
                elif isinstance(default, str):
                    _validate_non_empty_str(value, scope, key, strict, warnings)
                elif isinstance(default, list):
                    if not isinstance(value, list):
                        _handle_override_issue(f"{scope}.{key} 必须是列表", strict=strict, warnings=warnings)

    color_spec = overrides.get("color_spec")
    if color_spec is not None and not isinstance(color_spec, dict):
        _handle_override_issue("color_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(color_spec, dict):
        unknown_color = sorted(set(color_spec.keys()) - COLOR_SPEC_KEYS)
        if unknown_color:
            _handle_override_issue(
                f"color_spec 含未知键: {unknown_color}",
                strict=strict,
                warnings=warnings,
            )
        if "palette_preset" in color_spec:
            preset = color_spec["palette_preset"]
            if not isinstance(preset, str) or not preset.strip():
                _handle_override_issue(
                    "color_spec.palette_preset 必须是非空字符串",
                    strict=strict,
                    warnings=warnings,
                )
            elif preset.strip().lower() not in PRESET_NAMES:
                _handle_override_issue(
                    f"color_spec.palette_preset 不支持: {preset}；可选: {sorted(PRESET_NAMES)}",
                    strict=strict,
                    warnings=warnings,
                )
        if "categorical_palette" in color_spec:
            palette = color_spec["categorical_palette"]
            if isinstance(palette, list):
                _validate_str_list(palette, "color_spec", "categorical_palette", strict, warnings, non_empty=True)
            elif isinstance(palette, str):
                if not palette.strip():
                    _handle_override_issue("color_spec.categorical_palette 不能为空字符串", strict=strict, warnings=warnings)
                elif palette.strip().lower() not in VALID_PALETTE_STRINGS:
                    _handle_override_issue(
                        f"color_spec.categorical_palette 仅支持 'auto'（交给 palette_preset）或自定义颜色列表；"
                        f"换配色请用 color_spec.palette_preset，可选: {sorted(PRESET_NAMES)}",
                        strict=strict,
                        warnings=warnings,
                    )
            else:
                _handle_override_issue(
                    "color_spec.categorical_palette 必须是 'auto' 或颜色列表",
                    strict=strict,
                    warnings=warnings,
                )
        if "sequential_cmap" in color_spec:
            _validate_non_empty_str(color_spec["sequential_cmap"], "color_spec", "sequential_cmap", strict, warnings)
        if "diverging_cmap" in color_spec:
            _validate_non_empty_str(color_spec["diverging_cmap"], "color_spec", "diverging_cmap", strict, warnings)
        if "heatmap_cmap_mode" in color_spec:
            _validate_non_empty_str(color_spec["heatmap_cmap_mode"], "color_spec", "heatmap_cmap_mode", strict, warnings)
            if isinstance(color_spec["heatmap_cmap_mode"], str):
                cmap_mode = color_spec["heatmap_cmap_mode"].lower()
                if cmap_mode not in {"sequential", "diverging"}:
                    _handle_override_issue(
                        f"color_spec.heatmap_cmap_mode 不支持: {color_spec['heatmap_cmap_mode']}",
                        strict=strict,
                        warnings=warnings,
                    )
        if "colorblind_safe" in color_spec:
            _validate_bool(color_spec["colorblind_safe"], "color_spec", "colorblind_safe", strict, warnings)

    data_spec = overrides.get("data_spec")
    if data_spec is not None and not isinstance(data_spec, dict):
        _handle_override_issue("data_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(data_spec, dict):
        unknown_data = sorted(set(data_spec.keys()) - DATA_SPEC_KEYS)
        if unknown_data:
            _handle_override_issue(
                f"data_spec 含未知键: {unknown_data}",
                strict=strict,
                warnings=warnings,
            )
        if "enabled" in data_spec:
            _validate_bool(data_spec["enabled"], "data_spec", "enabled", strict, warnings)
        if "path" in data_spec:
            _validate_non_empty_str(data_spec["path"], "data_spec", "path", strict, warnings)
        if "format" in data_spec:
            _validate_non_empty_str(data_spec["format"], "data_spec", "format", strict, warnings)
            if isinstance(data_spec["format"], str):
                fmt = data_spec["format"].lower()
                if fmt not in {"auto", "csv", "xlsx", "h5"}:
                    _handle_override_issue(
                        f"data_spec.format 不支持: {data_spec['format']}",
                        strict=strict,
                        warnings=warnings,
                    )
        if "sheet" in data_spec:
            _validate_non_empty_str(data_spec["sheet"], "data_spec", "sheet", strict, warnings)
        if "h5_mode" in data_spec:
            _validate_non_empty_str(data_spec["h5_mode"], "data_spec", "h5_mode", strict, warnings)
            if isinstance(data_spec["h5_mode"], str):
                mode = data_spec["h5_mode"].lower()
                if mode not in {"auto", "hdfstore", "dataset"}:
                    _handle_override_issue(
                        f"data_spec.h5_mode 不支持: {data_spec['h5_mode']}",
                        strict=strict,
                        warnings=warnings,
                    )
        if "h5_key" in data_spec:
            _validate_non_empty_str(data_spec["h5_key"], "data_spec", "h5_key", strict, warnings)
        if "h5_dataset" in data_spec:
            _validate_non_empty_str(data_spec["h5_dataset"], "data_spec", "h5_dataset", strict, warnings)
        if "sample_id_column" in data_spec:
            _validate_non_empty_str(data_spec["sample_id_column"], "data_spec", "sample_id_column", strict, warnings)
        if "columns" in data_spec:
            _validate_str_list(data_spec["columns"], "data_spec", "columns", strict, warnings, non_empty=False)
        if "panel_mappings" in data_spec:
            panel_mappings = data_spec["panel_mappings"]
            if not isinstance(panel_mappings, dict):
                _handle_override_issue("data_spec.panel_mappings 必须是对象", strict=strict, warnings=warnings)
            else:
                for key, mapping in panel_mappings.items():
                    if not isinstance(mapping, dict):
                        _handle_override_issue(
                            f"data_spec.panel_mappings.{key} 必须是对象",
                            strict=strict,
                            warnings=warnings,
                        )

    crop_spec = overrides.get("crop_spec")
    if crop_spec is not None and not isinstance(crop_spec, dict):
        _handle_override_issue("crop_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(crop_spec, dict):
        unknown_crop = sorted(set(crop_spec.keys()) - CROP_SPEC_KEYS)
        if unknown_crop:
            _handle_override_issue(
                f"crop_spec 含未知键: {unknown_crop}",
                strict=strict,
                warnings=warnings,
            )
        if "enabled" in crop_spec:
            _validate_bool(crop_spec["enabled"], "crop_spec", "enabled", strict, warnings)
        if "mode" in crop_spec:
            _validate_non_empty_str(crop_spec["mode"], "crop_spec", "mode", strict, warnings)
            if isinstance(crop_spec["mode"], str):
                mode = crop_spec["mode"].lower()
                if mode not in {"auto", "alpha", "white"}:
                    _handle_override_issue(f"crop_spec.mode 不支持: {crop_spec['mode']}", strict=strict, warnings=warnings)
        if "alpha_threshold" in crop_spec:
            _validate_int(crop_spec["alpha_threshold"], "crop_spec", "alpha_threshold", strict, warnings, min_value=0, max_value=255)
        if "white_threshold" in crop_spec:
            _validate_int(crop_spec["white_threshold"], "crop_spec", "white_threshold", strict, warnings, min_value=0, max_value=255)
        if "padding_px" in crop_spec:
            _validate_int(crop_spec["padding_px"], "crop_spec", "padding_px", strict, warnings, min_value=0)
        if "keep_raw" in crop_spec:
            _validate_bool(crop_spec["keep_raw"], "crop_spec", "keep_raw", strict, warnings)
        if "max_trim_ratio_per_axis" in crop_spec:
            _validate_number(
                crop_spec["max_trim_ratio_per_axis"],
                "crop_spec",
                "max_trim_ratio_per_axis",
                strict,
                warnings,
                min_value=0.0,
                max_value=0.45,
            )

    layout_guard_spec = overrides.get("layout_guard_spec")
    if layout_guard_spec is not None and not isinstance(layout_guard_spec, dict):
        _handle_override_issue("layout_guard_spec 必须是对象", strict=strict, warnings=warnings)
    if isinstance(layout_guard_spec, dict):
        unknown_guard = sorted(set(layout_guard_spec.keys()) - LAYOUT_GUARD_SPEC_KEYS)
        if unknown_guard:
            _handle_override_issue(
                f"layout_guard_spec 含未知键: {unknown_guard}",
                strict=strict,
                warnings=warnings,
            )
        for key in {
            "enabled",
            "fallback_enabled",
            "crop_audit_enabled",
        }:
            if key in layout_guard_spec:
                _validate_bool(layout_guard_spec[key], "layout_guard_spec", key, strict, warnings)
        if "intent" in layout_guard_spec:
            _validate_non_empty_str(layout_guard_spec["intent"], "layout_guard_spec", "intent", strict, warnings)
            if isinstance(layout_guard_spec["intent"], str):
                intent = layout_guard_spec["intent"].strip().lower()
                if intent not in {"compact", "balanced", "roomy", "preserve_data"}:
                    _handle_override_issue(
                        f"layout_guard_spec.intent 不支持: {layout_guard_spec['intent']}",
                        strict=strict,
                        warnings=warnings,
                    )
        for key in {"max_fallback_passes"}:
            if key not in layout_guard_spec:
                continue
            _validate_int(
                layout_guard_spec[key],
                "layout_guard_spec",
                key,
                strict,
                warnings,
                min_value=0,
            )
        for key in {
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
            "crop_audit_max_trim_ratio",
            "preferred_canvas_scale",
        }:
            if key in layout_guard_spec:
                _validate_number(layout_guard_spec[key], "layout_guard_spec", key, strict, warnings)

    return warnings


def build_config(
    args: Any,
    overrides: dict,
    *,
    use_layout_prior: bool = True,
) -> dict:
    if bool(use_layout_prior):
        compiled = build_compiled_config_v3(args=args, overrides=overrides)
    else:
        compiled = build_compiled_config_v3_with_options(
            args=args,
            overrides=overrides,
            use_layout_prior=False,
        )
    return compiled.as_dict()


RUNTIME_CORE_KEYS = {
    "task",
    "chart_type",
    "layout",
    "axis_mode",
    "requested_axis_mode",
    "effective_axis_mode",
    "library",
    "style_profile",
    "style_stack",
    "seed",
    "dpi",
    "art_type",
    "style_spec",
    "layout_spec",
    "adjust_spec",
    "axis_spec",
    "legend_spec",
    "panel_label_spec",
    "primitive_spec",
    "color_spec",
    "data_spec",
    "crop_spec",
    "layout_guard_spec",
    "multi_order",
    "runtime_derived",
}


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _resolve_required_panel_types(compiled_config: dict[str, Any]) -> list[str]:
    chart_type = str(compiled_config.get("chart_type", "line"))
    if chart_type != "multi":
        if chart_type not in SUPPORTED_PANEL_TYPES:
            return []
        return [chart_type]
    runtime_derived = compiled_config.get("runtime_derived", {})
    panel_types = runtime_derived.get("panel_types", [])
    if isinstance(panel_types, list) and panel_types:
        return _ordered_unique([str(x) for x in panel_types if str(x) in SUPPORTED_PANEL_TYPES])
    multi_order = compiled_config.get("multi_order", [])
    if isinstance(multi_order, list) and multi_order:
        return _ordered_unique([str(x) for x in multi_order if str(x) in SUPPORTED_PANEL_TYPES])
    return ["line"]


def build_runtime_config(compiled_config: dict[str, Any]) -> dict[str, Any]:
    runtime: dict[str, Any] = {}
    for key in RUNTIME_CORE_KEYS:
        if key in compiled_config:
            runtime[key] = deepcopy(compiled_config[key])

    required_panel_types = _resolve_required_panel_types(compiled_config)
    runtime["required_panel_types"] = required_panel_types

    chart_spec = compiled_config.get("chart_spec", {})
    if not isinstance(chart_spec, dict):
        raise ValueError("compiled_config.chart_spec 必须是对象。")
    runtime_chart_spec: dict[str, Any] = {}
    global_spec = chart_spec.get("global")
    if isinstance(global_spec, dict):
        runtime_chart_spec["global"] = deepcopy(global_spec)
    chart_type = str(compiled_config.get("chart_type", "custom"))
    for panel_type, value in chart_spec.items():
        if panel_type == "global" or panel_type in required_panel_types:
            continue
        if panel_type in SUPPORTED_PANEL_TYPES:
            continue
        if panel_type != chart_type:
            continue
        if isinstance(value, dict):
            runtime_chart_spec[str(panel_type)] = deepcopy(value)
    for panel_type in required_panel_types:
        if panel_type not in chart_spec:
            raise ValueError(f"chart_spec 缺少必需图型配置: {panel_type}")
        runtime_chart_spec[panel_type] = deepcopy(chart_spec[panel_type])
    runtime["chart_spec"] = runtime_chart_spec
    return runtime


__all__ = [
    "build_config",
    "build_runtime_config",
    "deep_update",
    "load_overrides",
    "parse_style_stack",
    "slugify_task",
    "validate_overrides",
]
