#!/usr/bin/env python3
"""Stage B: 分层参数合成（唯一裁决点）。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from palette_registry import DEFAULT_PRESET
from palette_registry import PALETTE_PRESETS
from palette_registry import PRESET_NAMES
from palette_registry import VALID_PALETTE_STRINGS

from params.defaults.l0_route_defaults import DEFAULT_MULTI_ORDER
from params.defaults.l0_route_defaults import LAYOUT_GRID
from params.defaults.l0_route_defaults import LAYOUT_TO_ADJUST_KEY
from params.defaults.l0_route_defaults import SUPPORTED_PANEL_TYPES
from params.defaults.l1_profile_defaults import DEFAULT_STYLE_PROFILE
from params.defaults.l1_profile_defaults import LOCAL_STYLE_STACK_OVERRIDES
from params.defaults.l1_profile_defaults import PROFILE_DPI
from params.defaults.l1_profile_defaults import STYLE_LAYERS
from params.defaults.l1_profile_defaults import STYLE_PROFILES
from params.defaults.l1_profile_defaults import resolve_style_stack
from params.defaults.l3_layout_defaults import ADJUST_SPEC_DEFAULTS
from params.defaults.l3_layout_defaults import LAYOUT_SPEC_DEFAULTS
from params.defaults.l4_chart_defaults import CHART_SPEC_DEFAULTS
from params.defaults.l4_chart_defaults import COLOR_SPEC_DEFAULTS
from params.defaults.l4_chart_defaults import DATA_SPEC_DEFAULTS
from params.defaults.l4_chart_defaults import PRIMITIVE_SPEC_DEFAULTS
from params.defaults.l5_render_defaults import AXIS_SPEC_DEFAULTS
from params.defaults.l5_render_defaults import CROP_SPEC_DEFAULTS
from params.defaults.l5_render_defaults import LAYOUT_GUARD_SPEC_DEFAULTS
from params.defaults.l5_render_defaults import LEGEND_SPEC_DEFAULTS
from params.defaults.l5_render_defaults import PANEL_LABEL_SPEC_DEFAULTS

DEFAULT_DPI_BY_ART_TYPE = dict(PROFILE_DPI.get("thesis-journal", {"line": 1000, "photo": 600, "combo": 600}))


def deep_update(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def resolve_layout(chart_type: str, layout: str) -> str:
    if layout:
        if layout not in LAYOUT_SPEC_DEFAULTS:
            raise ValueError(f"不支持的 layout: {layout}")
        return layout
    if chart_type == "multi":
        return "quad-2x2"
    return "single"


def resolve_axis_mode(axis_mode: str, layout: str) -> str:
    if axis_mode != "auto":
        return axis_mode
    spec = LAYOUT_GRID[layout]
    return "shared_axis" if spec["nrows"] * spec["ncols"] > 1 else "independent"


def build_style_spec(style_profile: str, style_stack: list[str], style_override: dict) -> dict:
    if style_profile not in STYLE_PROFILES:
        raise ValueError(f"不支持的 style_profile: {style_profile}")

    _, style_spec, _ = resolve_style_stack(profile=style_profile, stack=None)
    style_spec = deepcopy(style_spec)
    style_spec.setdefault("axes_grid", False)
    style_spec.setdefault("grid_alpha", 0.35)
    style_spec.setdefault("grid_linewidth", 0.5)

    for layer in style_stack:
        if layer in STYLE_LAYERS:
            patch = STYLE_LAYERS[layer].get("style_spec", {})
            if isinstance(patch, dict):
                deep_update(style_spec, deepcopy(patch))
            mpl_patch = STYLE_LAYERS[layer].get("mpl_rc", {})
            if isinstance(mpl_patch, dict):
                if "axes.grid" in mpl_patch:
                    style_spec["axes_grid"] = bool(mpl_patch["axes.grid"])
                if "grid.alpha" in mpl_patch:
                    style_spec["grid_alpha"] = float(mpl_patch["grid.alpha"])
                if "grid.linewidth" in mpl_patch:
                    style_spec["grid_linewidth"] = float(mpl_patch["grid.linewidth"])
            continue
        if layer in LOCAL_STYLE_STACK_OVERRIDES:
            deep_update(style_spec, deepcopy(LOCAL_STYLE_STACK_OVERRIDES[layer]))
            continue
        raise ValueError(f"不支持的 style_stack layer: {layer}")

    deep_update(style_spec, style_override)
    return style_spec


def build_layout_spec(layout: str, override_layout_spec: dict) -> dict:
    layout_spec = deepcopy(LAYOUT_SPEC_DEFAULTS[layout])
    layout_spec.update(deepcopy(LAYOUT_GRID[layout]))
    if override_layout_spec:
        if layout in override_layout_spec and isinstance(override_layout_spec[layout], dict):
            deep_update(layout_spec, override_layout_spec[layout])
        elif all(k in {"width_mm", "aspect_ratio", "nrows", "ncols"} for k in override_layout_spec.keys()):
            deep_update(layout_spec, override_layout_spec)
    return layout_spec


def normalize_multi_order(cli_value: Any, override_value: Any) -> list[str]:
    if override_value is None:
        raw = cli_value
    elif isinstance(override_value, str):
        raw = override_value
    elif isinstance(override_value, list):
        raw = ",".join(str(x) for x in override_value)
    else:
        raise ValueError("multi_order 必须是字符串或列表。")

    if isinstance(raw, list):
        order = [str(x).strip() for x in raw if str(x).strip()]
    else:
        order = [x.strip() for x in str(raw).split(",") if x.strip()]
    if not order:
        order = list(DEFAULT_MULTI_ORDER)
    return order


def _resolve_axis_label_aspect_compensation(layout_spec: dict) -> float:
    """基于单子图横纵比返回 Y 轴标题补偿系数。

    规则：
    - 单子图越“扁宽”（width/height 越大），Y 轴标题基准适度增大。
    - 单子图越“瘦高”，保持基准不缩小。
    - 使用单一连续函数并限制补偿范围，避免跳变。
    - 奥卡姆约束：仅做“放大补偿”，不做缩小补偿。
    """

    nrows = max(1, int(layout_spec.get("nrows", 1)))
    ncols = max(1, int(layout_spec.get("ncols", 1)))
    fig_aspect = max(1e-6, float(layout_spec.get("aspect_ratio", 1.0)))
    panel_aspect = fig_aspect * (float(nrows) / float(ncols))
    factor = float(panel_aspect) ** 0.2
    return float(min(1.25, max(1.0, factor)))


def apply_layout_typography_compensation(style_spec: dict, layout_spec: dict, style_override: dict) -> dict:
    """基于 Y 轴标题字号为基准，统一派生所有字号。

    - 基准值：axis_label_size（若 override 提供则用 override）。
    - 其他字号按比例自动推导，避免多处叠加放大。
    """

    # 1) 基准字号
    base_y = style_override.get("axis_label_size", style_spec.get("axis_label_size", 10.0))
    try:
        base_y = float(base_y)
    except Exception:
        base_y = 10.0

    # 2) 按单子图横纵比补偿 Y 轴标题基准（全局单一补偿）
    axis_comp = _resolve_axis_label_aspect_compensation(layout_spec)
    base_y = round(base_y * axis_comp, 2)

    # 3) 按比例派生所有字号（仅在未被 override 时生效）
    derived = {
        "axis_label_size": base_y,
        "title_size": base_y * 0.95,
        "tick_label_size": base_y * 0.80,
        "annotation_size": base_y * 0.82,
        "legend_size": base_y * 0.85,
        "legend_title_size": base_y * 0.92,
    }
    # marker 与基准的经验比例保持在 0.40
    derived_marker = base_y * 0.40

    for key, value in derived.items():
        if key in style_override:
            continue
        style_spec[key] = round(float(value), 1)

    if "marker_size" not in style_override and "marker_size" in style_spec:
        style_spec["marker_size"] = round(float(derived_marker), 1)

    return style_spec


def derive_spacing_basis_pt(style_spec: dict) -> float:
    """统一间距基准字号（pt）。

    奥卡姆收口：仅以补偿后的 axis_label_size 作为唯一间距基准，
    让“字体补偿 -> 间距控制”成为单链路。
    """

    try:
        axis_label = float(style_spec.get("axis_label_size", 10.0))
    except Exception:
        axis_label = 10.0
    return max(0.1, axis_label)


def _derive_subplot_space_ratio(
    *,
    gap_px: float,
    inner_span_px: float,
    n_panels: int,
    max_space: float,
) -> float:
    if n_panels <= 1:
        return 0.0
    if gap_px <= 0.0 or inner_span_px <= 1e-6:
        return 0.0
    # matplotlib 定义：space = ratio * avg_axes_span。
    # 求解 ratio，使目标像素间距与字号基准一致。
    denom = float(inner_span_px) - float(gap_px) * float(n_panels - 1)
    if denom <= 1e-6:
        return float(max_space)
    ratio = (float(gap_px) * float(n_panels)) / denom
    return float(min(max_space, max(0.0, ratio)))


def _normalize_chart_spec(chart_spec: dict) -> dict:
    chart_spec["line"]["n_points"] = max(10, int(chart_spec["line"].get("n_points", 120)))
    chart_spec["line"]["noise_std"] = max(0.0, float(chart_spec["line"].get("noise_std", 0.028)))

    chart_spec["scatter"]["n_points"] = max(10, int(chart_spec["scatter"].get("n_points", 96)))
    chart_spec["scatter"]["fit_line"] = bool(chart_spec["scatter"].get("fit_line", True))
    chart_spec["scatter"]["x_col"] = str(chart_spec["scatter"].get("x_col", "")).strip()
    chart_spec["scatter"]["y_col"] = str(chart_spec["scatter"].get("y_col", "")).strip()
    chart_spec["scatter"]["group_col"] = str(chart_spec["scatter"].get("group_col", "")).strip()
    chart_spec["scatter"]["x_label"] = str(chart_spec["scatter"].get("x_label", "")).strip()
    chart_spec["scatter"]["y_label"] = str(chart_spec["scatter"].get("y_label", "")).strip()

    chart_spec["bar"]["n_groups"] = max(2, int(chart_spec["bar"].get("n_groups", 4)))
    chart_spec["bar"]["y_min"] = float(chart_spec["bar"].get("y_min", 0.55))
    chart_spec["bar"]["y_max"] = float(chart_spec["bar"].get("y_max", 1.00))
    if chart_spec["bar"]["y_max"] <= chart_spec["bar"]["y_min"]:
        chart_spec["bar"]["y_max"] = chart_spec["bar"]["y_min"] + 0.1
    chart_spec["bar"]["x_col"] = str(chart_spec["bar"].get("x_col", "")).strip()
    chart_spec["bar"]["y_col"] = str(chart_spec["bar"].get("y_col", "")).strip()
    chart_spec["bar"]["group_col"] = str(chart_spec["bar"].get("group_col", "")).strip()
    chart_spec["bar"]["aggregate"] = str(chart_spec["bar"].get("aggregate", "mean")).strip().lower() or "mean"
    if chart_spec["bar"]["aggregate"] not in {"mean", "median"}:
        chart_spec["bar"]["aggregate"] = "mean"
    chart_spec["bar"]["overlay_scatter"] = bool(chart_spec["bar"].get("overlay_scatter", True))
    chart_spec["bar"]["jitter"] = float(chart_spec["bar"].get("jitter", 0.08))
    chart_spec["bar"]["x_label"] = str(chart_spec["bar"].get("x_label", "")).strip()
    chart_spec["bar"]["y_label"] = str(chart_spec["bar"].get("y_label", "")).strip()

    chart_spec["hist"]["n_samples"] = max(20, int(chart_spec["hist"].get("n_samples", 300)))
    chart_spec["hist"]["bins"] = max(3, int(chart_spec["hist"].get("bins", 24)))
    chart_spec["hist"]["alpha"] = min(1.0, max(0.05, float(chart_spec["hist"].get("alpha", 0.72))))
    chart_spec["hist"]["density"] = bool(chart_spec["hist"].get("density", False))
    chart_spec["hist"]["multicolor"] = bool(chart_spec["hist"].get("multicolor", False))
    chart_spec["hist"]["edgecolor"] = str(chart_spec["hist"].get("edgecolor", "#2B2B2B")).strip() or "#2B2B2B"
    chart_spec["hist"]["edgewidth"] = max(0.0, float(chart_spec["hist"].get("edgewidth", 0.85)))

    chart_spec["box"]["n_groups"] = max(2, int(chart_spec["box"].get("n_groups", 4)))
    chart_spec["box"]["n_samples_per_group"] = max(10, int(chart_spec["box"].get("n_samples_per_group", 80)))
    chart_spec["box"]["width"] = min(0.95, max(0.1, float(chart_spec["box"].get("width", 0.55))))
    chart_spec["box"]["showfliers"] = bool(chart_spec["box"].get("showfliers", False))
    chart_spec["box"]["notch"] = bool(chart_spec["box"].get("notch", False))

    chart_spec["violin"]["n_groups"] = max(2, int(chart_spec["violin"].get("n_groups", 4)))
    chart_spec["violin"]["n_samples_per_group"] = max(10, int(chart_spec["violin"].get("n_samples_per_group", 100)))
    chart_spec["violin"]["showmeans"] = bool(chart_spec["violin"].get("showmeans", False))
    chart_spec["violin"]["showmedians"] = bool(chart_spec["violin"].get("showmedians", True))

    chart_spec["heatmap"]["matrix_size"] = max(3, int(chart_spec["heatmap"].get("matrix_size", 6)))
    chart_spec["heatmap"]["vmin"] = float(chart_spec["heatmap"].get("vmin", -1.0))
    chart_spec["heatmap"]["vmax"] = float(chart_spec["heatmap"].get("vmax", 1.0))
    if chart_spec["heatmap"]["vmax"] <= chart_spec["heatmap"]["vmin"]:
        chart_spec["heatmap"]["vmax"] = chart_spec["heatmap"]["vmin"] + 0.1

    chart_spec["contour"]["grid_size"] = max(20, int(chart_spec["contour"].get("grid_size", 80)))
    chart_spec["contour"]["levels"] = max(3, int(chart_spec["contour"].get("levels", 12)))
    chart_spec["contour"]["filled"] = bool(chart_spec["contour"].get("filled", True))

    chart_spec["hexbin"]["n_points"] = max(80, int(chart_spec["hexbin"].get("n_points", 1200)))
    chart_spec["hexbin"]["gridsize"] = max(3, int(chart_spec["hexbin"].get("gridsize", 26)))
    chart_spec["hexbin"]["mincnt"] = max(0, int(chart_spec["hexbin"].get("mincnt", 1)))

    chart_spec["errorbar"]["n_points"] = max(3, int(chart_spec["errorbar"].get("n_points", 14)))
    chart_spec["errorbar"]["capsize"] = max(0.0, float(chart_spec["errorbar"].get("capsize", 3.0)))
    chart_spec["errorbar"]["elinewidth"] = max(0.0, float(chart_spec["errorbar"].get("elinewidth", 1.0)))

    chart_spec["stem"]["n_points"] = max(3, int(chart_spec["stem"].get("n_points", 22)))
    chart_spec["stem"]["baseline"] = float(chart_spec["stem"].get("baseline", 0.0))
    chart_spec["stem"]["linefmt"] = str(chart_spec["stem"].get("linefmt", "-"))
    chart_spec["stem"]["markerfmt"] = str(chart_spec["stem"].get("markerfmt", "o"))
    chart_spec["stem"]["basefmt"] = str(chart_spec["stem"].get("basefmt", "k-"))
    return chart_spec


def compile_layers(request: dict[str, Any]) -> dict[str, Any]:
    route = request["route"]
    profile = request["profile"]
    overrides = deepcopy(request["overrides"])

    chart_type = str(route["chart_type"])
    layout = resolve_layout(chart_type=chart_type, layout=str(route.get("layout", "")))
    requested_axis_mode = str(route.get("axis_mode", "auto"))
    axis_mode = resolve_axis_mode(axis_mode=requested_axis_mode, layout=layout)
    style_profile = str(profile.get("style_profile", DEFAULT_STYLE_PROFILE))
    style_stack = [x for x in profile.get("style_stack", []) if x]

    style_override = overrides.get("style_spec", {})
    if style_override and not isinstance(style_override, dict):
        raise ValueError("style_spec override 必须是对象。")
    style_spec = build_style_spec(style_profile=style_profile, style_stack=style_stack, style_override=style_override)

    layout_override = overrides.get("layout_spec", {})
    if layout_override and not isinstance(layout_override, dict):
        raise ValueError("layout_spec override 必须是对象。")
    layout_spec = build_layout_spec(layout=layout, override_layout_spec=layout_override)
    style_spec = apply_layout_typography_compensation(
        style_spec=style_spec,
        layout_spec=layout_spec,
        style_override=style_override,
    )

    default_adjust = {"left": 0.09, "right": 0.985, "top": 0.98, "bottom": 0.16}
    adjust_key = LAYOUT_TO_ADJUST_KEY.get(layout)
    if adjust_key and adjust_key in ADJUST_SPEC_DEFAULTS and isinstance(ADJUST_SPEC_DEFAULTS[adjust_key], dict):
        adjust_spec = deepcopy(ADJUST_SPEC_DEFAULTS[adjust_key])
    else:
        adjust_spec = deepcopy(default_adjust)
    patch_adjust = overrides.get("adjust_spec", {})
    if patch_adjust:
        if not isinstance(patch_adjust, dict):
            raise ValueError("adjust_spec override 必须是对象。")
        deep_update(adjust_spec, patch_adjust)
    by_layout = overrides.get("adjust_by_layout", {})
    if by_layout and isinstance(by_layout, dict) and layout in by_layout and isinstance(by_layout[layout], dict):
        deep_update(adjust_spec, by_layout[layout])

    axis_spec = deepcopy(AXIS_SPEC_DEFAULTS)
    patch_axis = overrides.get("axis_spec", {})
    if patch_axis:
        if not isinstance(patch_axis, dict):
            raise ValueError("axis_spec override 必须是对象。")
        deep_update(axis_spec, patch_axis)
    axis_spec["tick_direction"] = str(axis_spec.get("tick_direction", "out")).lower()
    if axis_spec["tick_direction"] not in {"in", "out", "inout"}:
        raise ValueError(f"axis_spec.tick_direction 不支持: {axis_spec['tick_direction']}")
    axis_spec["tick_length"] = float(axis_spec.get("tick_length", 4.0))
    axis_spec["tick_width"] = float(axis_spec.get("tick_width", 0.8))
    axis_spec["show_top_spine"] = bool(axis_spec.get("show_top_spine", True))
    axis_spec["show_right_spine"] = bool(axis_spec.get("show_right_spine", True))
    axis_spec["minor_ticks"] = bool(axis_spec.get("minor_ticks", False))

    legend_spec = deepcopy(LEGEND_SPEC_DEFAULTS)
    patch_legend = overrides.get("legend_spec", {})
    if patch_legend:
        if not isinstance(patch_legend, dict):
            raise ValueError("legend_spec override 必须是对象。")
        deep_update(legend_spec, patch_legend)
    legend_spec["loc"] = str(legend_spec.get("loc", "best"))
    legend_spec["ncol"] = max(1, int(legend_spec.get("ncol", 1)))
    legend_spec["frameon"] = bool(legend_spec.get("frameon", False))
    legend_spec["columnspacing"] = float(legend_spec.get("columnspacing", 1.0))
    legend_spec["borderaxespad"] = float(legend_spec.get("borderaxespad", 0.4))

    panel_label_spec = deepcopy(PANEL_LABEL_SPEC_DEFAULTS)
    patch_panel_label = overrides.get("panel_label_spec", {})
    if patch_panel_label:
        if not isinstance(patch_panel_label, dict):
            raise ValueError("panel_label_spec override 必须是对象。")
        deep_update(panel_label_spec, patch_panel_label)
    panel_label_spec["mode"] = str(panel_label_spec.get("mode", "auto")).lower()
    if panel_label_spec["mode"] not in {"auto", "inside", "outside", "off"}:
        raise ValueError(f"panel_label_spec.mode 不支持: {panel_label_spec['mode']}")
    panel_label_spec["corner"] = str(panel_label_spec.get("corner", "top_left")).lower()
    if panel_label_spec["corner"] not in {"top_left", "top_right", "bottom_left", "bottom_right"}:
        raise ValueError(f"panel_label_spec.corner 不支持: {panel_label_spec['corner']}")
    panel_label_spec["label_style"] = str(panel_label_spec.get("label_style", "lower_paren")).lower()
    if panel_label_spec["label_style"] not in {"upper_paren", "lower_paren", "upper", "lower"}:
        raise ValueError(f"panel_label_spec.label_style 不支持: {panel_label_spec['label_style']}")
    # inside_x/inside_y 为精确 transAxes 逃生口；None 表示按 corner 自动取角。
    for _k in ("inside_x", "inside_y"):
        if panel_label_spec.get(_k) is not None:
            panel_label_spec[_k] = float(panel_label_spec[_k])
    panel_label_spec["outside_x"] = float(panel_label_spec.get("outside_x", 0.5))
    if panel_label_spec.get("labels") is not None:
        if not isinstance(panel_label_spec["labels"], (list, tuple)):
            raise ValueError("panel_label_spec.labels 必须是列表（元素为字符串或 null）。")
        panel_label_spec["labels"] = [None if x is None else str(x) for x in panel_label_spec["labels"]]

    primitive_spec = deepcopy(PRIMITIVE_SPEC_DEFAULTS)
    patch_primitive = overrides.get("primitive_spec", {})
    if patch_primitive:
        if not isinstance(patch_primitive, dict):
            raise ValueError("primitive_spec override 必须是对象。")
        deep_update(primitive_spec, patch_primitive)
    line_style_cycle = primitive_spec.get("line_style_cycle", ["-", "--"])
    if not isinstance(line_style_cycle, list) or not line_style_cycle:
        raise ValueError("primitive_spec.line_style_cycle 必须是非空列表。")
    primitive_spec["line_style_cycle"] = [str(x) for x in line_style_cycle]
    line_marker_cycle = primitive_spec.get("line_marker_cycle", ["o", ""])
    if not isinstance(line_marker_cycle, list) or not line_marker_cycle:
        raise ValueError("primitive_spec.line_marker_cycle 必须是非空列表。")
    primitive_spec["line_marker_cycle"] = [str(x) for x in line_marker_cycle]
    primitive_spec["line_markevery"] = max(1, int(primitive_spec.get("line_markevery", 12)))
    primitive_spec["bar_width"] = float(primitive_spec.get("bar_width", 0.34))
    primitive_spec["bar_capsize"] = float(primitive_spec.get("bar_capsize", 3.0))
    primitive_spec["bar_elinewidth"] = float(primitive_spec.get("bar_elinewidth", 1.0))
    primitive_spec["scatter_size"] = float(primitive_spec.get("scatter_size", 18.0))
    primitive_spec["scatter_alpha"] = float(primitive_spec.get("scatter_alpha", 0.75))
    primitive_spec["heatmap_cbar_fraction"] = float(primitive_spec.get("heatmap_cbar_fraction", 0.048))
    primitive_spec["heatmap_cbar_pad"] = float(primitive_spec.get("heatmap_cbar_pad", 0.04))

    chart_spec = deepcopy(CHART_SPEC_DEFAULTS)
    patch_chart = overrides.get("chart_spec", {})
    if patch_chart:
        if not isinstance(patch_chart, dict):
            raise ValueError("chart_spec override 必须是对象。")
        for chart_name, patch in patch_chart.items():
            if not isinstance(patch, dict):
                raise ValueError(f"chart_spec.{chart_name} 必须是对象。")
            if chart_name not in chart_spec:
                chart_spec[str(chart_name)] = deepcopy(patch)
                continue
            unknown_keys = sorted(set(patch.keys()) - set(chart_spec[chart_name].keys()))
            if unknown_keys:
                raise ValueError(f"chart_spec.{chart_name} 含未知键: {unknown_keys}")
            deep_update(chart_spec[chart_name], patch)
    chart_spec = _normalize_chart_spec(chart_spec)

    color_spec = deepcopy(COLOR_SPEC_DEFAULTS)
    patch_color = overrides.get("color_spec", {})
    if patch_color:
        if not isinstance(patch_color, dict):
            raise ValueError("color_spec override 必须是对象。")
        deep_update(color_spec, patch_color)

    # 领域预设：palette_preset 是唯一"换配色"入口。
    # 分类色板由 resolve_palette 在运行时直接按 preset 解析，stage 不再覆盖 categorical_palette；
    # 这里仅为预设填充 cmap 类子键（顺序/发散/热图模式），且用户显式值始终优先。
    preset_name = str(color_spec.get("palette_preset", DEFAULT_PRESET)).strip().lower()
    if preset_name not in PRESET_NAMES:
        raise ValueError(
            f"color_spec.palette_preset 不支持: {preset_name}；可选: {sorted(PRESET_NAMES)}。"
        )
    color_spec["palette_preset"] = preset_name
    explicit_color_keys = set(patch_color.keys()) if isinstance(patch_color, dict) else set()
    if preset_name != DEFAULT_PRESET:
        preset_bundle = PALETTE_PRESETS[preset_name]
        for key in ("sequential_cmap", "diverging_cmap", "heatmap_cmap_mode"):
            if key not in explicit_color_keys:
                color_spec[key] = preset_bundle[key]

    # categorical_palette 仅作自定义 hex 列表逃生口；字符串只允许 "auto"（=交给 preset）。
    categorical_palette = color_spec.get("categorical_palette", "auto")
    if isinstance(categorical_palette, list):
        if not categorical_palette:
            raise ValueError("color_spec.categorical_palette 列表不能为空。")
        color_spec["categorical_palette"] = [str(x) for x in categorical_palette]
    else:
        palette_name = str(categorical_palette).strip().lower()
        if palette_name not in VALID_PALETTE_STRINGS:
            raise ValueError(
                "color_spec.categorical_palette 仅支持 'auto'（交给 palette_preset）或自定义颜色列表；"
                f"换配色请用 color_spec.palette_preset，可选: {sorted(PRESET_NAMES)}。"
            )
        color_spec["categorical_palette"] = palette_name
    color_spec["sequential_cmap"] = str(color_spec.get("sequential_cmap", "viridis"))
    color_spec["diverging_cmap"] = str(color_spec.get("diverging_cmap", "RdBu_r"))
    cmap_mode = str(color_spec.get("heatmap_cmap_mode", "sequential")).lower()
    if cmap_mode not in {"sequential", "diverging"}:
        raise ValueError(f"color_spec.heatmap_cmap_mode 不支持: {cmap_mode}")
    color_spec["heatmap_cmap_mode"] = cmap_mode
    color_spec["colorblind_safe"] = bool(color_spec.get("colorblind_safe", True))

    data_spec = deepcopy(DATA_SPEC_DEFAULTS)
    patch_data = overrides.get("data_spec", {})
    if patch_data:
        if not isinstance(patch_data, dict):
            raise ValueError("data_spec override 必须是对象。")
        deep_update(data_spec, patch_data)

    data_spec["enabled"] = bool(data_spec.get("enabled", False))
    data_spec["path"] = str(data_spec.get("path", "")).strip()
    data_format = str(data_spec.get("format", "auto")).strip().lower() or "auto"
    if data_format not in {"auto", "csv", "xlsx", "h5"}:
        raise ValueError(f"data_spec.format 不支持: {data_spec.get('format')}")
    data_spec["format"] = data_format
    data_spec["sheet"] = str(data_spec.get("sheet", "")).strip()
    h5_mode = str(data_spec.get("h5_mode", "auto")).strip().lower() or "auto"
    if h5_mode not in {"auto", "hdfstore", "dataset"}:
        raise ValueError(f"data_spec.h5_mode 不支持: {data_spec.get('h5_mode')}")
    data_spec["h5_mode"] = h5_mode
    data_spec["h5_key"] = str(data_spec.get("h5_key", "")).strip()
    data_spec["h5_dataset"] = str(data_spec.get("h5_dataset", "")).strip()
    data_spec["sample_id_column"] = str(data_spec.get("sample_id_column", "")).strip()

    columns = data_spec.get("columns", [])
    if not isinstance(columns, list):
        raise ValueError("data_spec.columns 必须是字符串列表。")
    data_spec["columns"] = [str(x).strip() for x in columns if str(x).strip()]

    panel_mappings_raw = data_spec.get("panel_mappings", {})
    if not isinstance(panel_mappings_raw, dict):
        raise ValueError("data_spec.panel_mappings 必须是对象。")
    panel_mappings: dict[str, dict[str, Any]] = {}
    for key, value in panel_mappings_raw.items():
        if not isinstance(value, dict):
            raise ValueError(f"data_spec.panel_mappings.{key} 必须是对象。")
        mapping = {str(k): deepcopy(v) for k, v in value.items()}
        panel_mappings[str(key)] = mapping
    data_spec["panel_mappings"] = panel_mappings

    if data_spec["path"]:
        data_spec["enabled"] = True
    if data_spec["enabled"] and not data_spec["path"]:
        raise ValueError("data_spec.enabled=true 时必须提供 data_spec.path。")

    crop_spec = deepcopy(CROP_SPEC_DEFAULTS)
    patch_crop = overrides.get("crop_spec", {})
    if patch_crop:
        if not isinstance(patch_crop, dict):
            raise ValueError("crop_spec override 必须是对象。")
        deep_update(crop_spec, patch_crop)
    crop_spec["mode"] = str(crop_spec.get("mode", "auto")).lower()
    if crop_spec["mode"] not in {"auto", "alpha", "white"}:
        raise ValueError(f"crop_spec.mode 不支持: {crop_spec['mode']}")
    crop_spec["enabled"] = bool(crop_spec.get("enabled", True))
    crop_spec["alpha_threshold"] = max(0, min(255, int(crop_spec.get("alpha_threshold", 0))))
    crop_spec["white_threshold"] = max(0, min(255, int(crop_spec.get("white_threshold", 250))))
    crop_spec["padding_px"] = max(0, int(crop_spec.get("padding_px", 6)))
    crop_spec["keep_raw"] = bool(crop_spec.get("keep_raw", False))
    crop_spec["max_trim_ratio_per_axis"] = min(0.45, max(0.0, float(crop_spec.get("max_trim_ratio_per_axis", 0.12))))

    layout_guard_spec = deepcopy(LAYOUT_GUARD_SPEC_DEFAULTS)
    patch_layout_guard = overrides.get("layout_guard_spec", {})
    if patch_layout_guard:
        if not isinstance(patch_layout_guard, dict):
            raise ValueError("layout_guard_spec override 必须是对象。")
        deep_update(layout_guard_spec, patch_layout_guard)
    layout_guard_spec["enabled"] = bool(layout_guard_spec["enabled"])
    layout_guard_spec["fallback_enabled"] = bool(layout_guard_spec["fallback_enabled"])
    layout_guard_spec["intent"] = str(layout_guard_spec.get("intent", "balanced")).strip().lower()
    if layout_guard_spec["intent"] not in {"compact", "balanced", "roomy", "preserve_data"}:
        raise ValueError(f"layout_guard_spec.intent 不支持: {layout_guard_spec['intent']}")
    layout_guard_spec["preferred_canvas_scale"] = min(3.0, max(1.0, float(layout_guard_spec.get("preferred_canvas_scale", 1.0))))
    layout_guard_spec["max_fallback_passes"] = max(0, int(layout_guard_spec["max_fallback_passes"]))
    layout_guard_spec["overflow_pad_px"] = max(0.0, float(layout_guard_spec["overflow_pad_px"]))
    layout_guard_spec["edge_tolerance_px"] = max(0.0, float(layout_guard_spec["edge_tolerance_px"]))
    layout_guard_spec["subplot_overlap_tolerance_px"] = max(0.0, float(layout_guard_spec["subplot_overlap_tolerance_px"]))
    layout_guard_spec["min_subplot_gap_px"] = min(120.0, max(0.0, float(layout_guard_spec["min_subplot_gap_px"])))
    layout_guard_spec["min_subplot_vgap_px"] = min(120.0, max(0.0, float(layout_guard_spec["min_subplot_vgap_px"])))
    layout_guard_spec["min_inner_width_frac"] = min(0.95, max(0.10, float(layout_guard_spec["min_inner_width_frac"])))
    layout_guard_spec["min_inner_height_frac"] = min(0.95, max(0.10, float(layout_guard_spec["min_inner_height_frac"])))
    layout_guard_spec["max_side_adjust_frac"] = min(0.45, max(0.0, float(layout_guard_spec["max_side_adjust_frac"])))
    layout_guard_spec["overflow_scale_trigger_ratio"] = min(0.60, max(0.0, float(layout_guard_spec["overflow_scale_trigger_ratio"])))
    layout_guard_spec["subplot_hgap_ylabel_ratio"] = min(2.0, max(0.05, float(layout_guard_spec["subplot_hgap_ylabel_ratio"])))
    layout_guard_spec["subplot_vgap_xlabel_ratio"] = min(2.0, max(0.05, float(layout_guard_spec["subplot_vgap_xlabel_ratio"])))
    layout_guard_spec["panel_label_gap_ylabel_ratio"] = min(1.2, max(0.05, float(layout_guard_spec["panel_label_gap_ylabel_ratio"])))
    layout_guard_spec["max_total_scale"] = min(3.0, max(1.0, float(layout_guard_spec["max_total_scale"])))
    layout_guard_spec["max_scale_step_per_pass"] = min(1.0, max(0.05, float(layout_guard_spec["max_scale_step_per_pass"])))
    layout_guard_spec["max_aspect_ratio_drift_frac"] = min(0.25, max(0.0, float(layout_guard_spec["max_aspect_ratio_drift_frac"])))
    layout_guard_spec["max_wspace"] = min(1.6, max(0.0, float(layout_guard_spec["max_wspace"])))
    layout_guard_spec["max_hspace"] = min(1.8, max(0.0, float(layout_guard_spec["max_hspace"])))
    layout_guard_spec["crop_audit_enabled"] = bool(layout_guard_spec["crop_audit_enabled"])
    layout_guard_spec["crop_audit_max_trim_ratio"] = min(0.45, max(0.0, float(layout_guard_spec["crop_audit_max_trim_ratio"])))

    art_type = str(route.get("art_type", "combo"))
    dpi_default = int(DEFAULT_DPI_BY_ART_TYPE[art_type])
    dpi_input = int(route.get("dpi", 0))
    dpi = int(dpi_input if dpi_input > 0 else overrides.get("dpi", dpi_default))

    # 基于“子图整体文字基准字号”反推布局像素间距。
    # 注意：布局计算发生在 matplotlib 运行时画布（默认约 100 DPI），
    # 不应直接使用导出 DPI（如 600），否则会把间距放大约 6 倍。
    layout_dpi_for_spacing = 100.0
    spacing_basis_pt = derive_spacing_basis_pt(style_spec)
    hgap_ratio = float(layout_guard_spec["subplot_hgap_ylabel_ratio"])
    vgap_ratio = float(layout_guard_spec["subplot_vgap_xlabel_ratio"])
    gap_x_px = (spacing_basis_pt * hgap_ratio * layout_dpi_for_spacing) / 72.0
    gap_y_px = (spacing_basis_pt * vgap_ratio * layout_dpi_for_spacing) / 72.0
    if "min_subplot_gap_px" not in patch_layout_guard:
        layout_guard_spec["min_subplot_gap_px"] = round(max(0.6, gap_x_px), 2)
    if "min_subplot_vgap_px" not in patch_layout_guard:
        layout_guard_spec["min_subplot_vgap_px"] = round(max(0.6, gap_y_px), 2)
    if axis_mode == "shared_axis":
        # 共轴模式不保留子图间隙：间距由外边距与共享轴标签规则承担。
        layout_guard_spec["min_subplot_gap_px"] = 0.0
        layout_guard_spec["min_subplot_vgap_px"] = 0.0
    if patch_panel_label.get("xlabel_gap_pt") is None:
        panel_gap_ratio = float(layout_guard_spec["panel_label_gap_ylabel_ratio"])
        panel_label_spec["xlabel_gap_pt"] = round(max(0.6, spacing_basis_pt * panel_gap_ratio), 2)
    else:
        panel_label_spec["xlabel_gap_pt"] = max(0.0, float(panel_label_spec.get("xlabel_gap_pt", 0.0)))

    # 裁切 padding 仅做最小保护，不再注入“目标图幅回填”参数，避免透明留白被放大。
    min_padding_px = (spacing_basis_pt * 0.10 * dpi) / 72.0
    crop_spec["padding_px"] = int(max(crop_spec["padding_px"], min_padding_px))

    # 将“字号基准像素间距”映射成初始 wspace/hspace，避免仅 guard 阶段才响应。
    nrows = max(1, int(layout_spec.get("nrows", 1)))
    ncols = max(1, int(layout_spec.get("ncols", 1)))
    width_in = float(layout_spec.get("width_mm", 0.0)) / 25.4
    aspect = max(1e-6, float(layout_spec.get("aspect_ratio", 1.0)))
    height_in = width_in / aspect
    inner_w_px = max(
        1.0,
        (float(adjust_spec.get("right", 1.0)) - float(adjust_spec.get("left", 0.0))) * width_in * layout_dpi_for_spacing,
    )
    inner_h_px = max(
        1.0,
        (float(adjust_spec.get("top", 1.0)) - float(adjust_spec.get("bottom", 0.0))) * height_in * layout_dpi_for_spacing,
    )
    derived_wspace = round(
        _derive_subplot_space_ratio(
            gap_px=float(layout_guard_spec["min_subplot_gap_px"]),
            inner_span_px=inner_w_px,
            n_panels=ncols,
            max_space=float(layout_guard_spec["max_wspace"]),
        ),
        4,
    )
    derived_hspace = round(
        _derive_subplot_space_ratio(
            gap_px=float(layout_guard_spec["min_subplot_vgap_px"]),
            inner_span_px=inner_h_px,
            n_panels=nrows,
            max_space=float(layout_guard_spec["max_hspace"]),
        ),
        4,
    )

    explicit_wspace = isinstance(patch_adjust, dict) and ("wspace" in patch_adjust)
    explicit_hspace = isinstance(patch_adjust, dict) and ("hspace" in patch_adjust)
    if isinstance(by_layout, dict) and isinstance(by_layout.get(layout), dict):
        explicit_wspace = explicit_wspace or ("wspace" in by_layout[layout])
        explicit_hspace = explicit_hspace or ("hspace" in by_layout[layout])
    if axis_mode == "shared_axis":
        adjust_spec["wspace"] = 0.0 if ncols > 1 else 0.0
        adjust_spec["hspace"] = 0.0 if nrows > 1 else 0.0
    elif ncols <= 1:
        adjust_spec["wspace"] = 0.0
    elif not explicit_wspace:
        adjust_spec["wspace"] = float(derived_wspace)
    if axis_mode != "shared_axis" and nrows <= 1:
        adjust_spec["hspace"] = 0.0
    elif axis_mode != "shared_axis" and not explicit_hspace:
        adjust_spec["hspace"] = float(derived_hspace)

    multi_order = normalize_multi_order(route.get("multi_order", DEFAULT_MULTI_ORDER), overrides.get("multi_order"))

    config = {
        "task": request["task"],
        "chart_type": chart_type,
        "layout": layout,
        "axis_mode": axis_mode,
        "requested_axis_mode": requested_axis_mode,
        "library": str(route.get("library", "matplotlib")),
        "style_profile": style_profile,
        "style_stack": style_stack,
        "seed": int(route.get("seed", 42)),
        "dpi": dpi,
        "art_type": art_type,
        "style_spec": style_spec,
        "layout_spec": layout_spec,
        "adjust_spec": adjust_spec,
        "axis_spec": axis_spec,
        "legend_spec": legend_spec,
        "panel_label_spec": panel_label_spec,
        "primitive_spec": primitive_spec,
        "chart_spec": chart_spec,
        "color_spec": color_spec,
        "data_spec": data_spec,
        "crop_spec": crop_spec,
        "layout_guard_spec": layout_guard_spec,
        "multi_order": multi_order,
    }

    extra_config = overrides.get("extra_config", {})
    if extra_config:
        if not isinstance(extra_config, dict):
            raise ValueError("extra_config override 必须是对象。")
        collision_keys = sorted(set(extra_config.keys()) & set(config.keys()))
        if collision_keys:
            raise ValueError(f"extra_config 不能覆盖已编译配置键: {collision_keys}")
        deep_update(config, extra_config)

    return {
        "l0_route": {
            "chart_type": chart_type,
            "layout": layout,
            "axis_mode": axis_mode,
            "requested_axis_mode": requested_axis_mode,
            "library": config["library"],
            "art_type": art_type,
            "multi_order": multi_order,
        },
        "l1_profile": {"style_profile": style_profile, "style_stack": style_stack},
        "l2_style_tokens": {"style_spec": deepcopy(style_spec)},
        "l3_layout_geometry": {
            "layout_spec": deepcopy(layout_spec),
            "adjust_spec": deepcopy(adjust_spec),
        },
        "l4_chart_behavior": {
            "primitive_spec": deepcopy(primitive_spec),
            "chart_spec": deepcopy(chart_spec),
            "color_spec": deepcopy(color_spec),
            "data_spec": deepcopy(data_spec),
        },
        "l5_render_policy": {
            "axis_spec": deepcopy(axis_spec),
            "legend_spec": deepcopy(legend_spec),
            "panel_label_spec": deepcopy(panel_label_spec),
            "crop_spec": deepcopy(crop_spec),
            "layout_guard_spec": deepcopy(layout_guard_spec),
        },
        "flat_config": config,
    }


__all__ = ["compile_layers", "deep_update"]
