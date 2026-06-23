#!/usr/bin/env python3
"""参数编译单入口。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from params.contracts.dataclasses import CompiledConfig
from params.contracts.dataclasses import LayerSnapshot
from params.graph.validators import assert_graph_contract
from params.layout_priors import resolve_layout_prior_adjust
from params.pipeline.stage_a_ingest import build_ingest_request
from params.pipeline.stage_b_compile import compile_layers
from params.pipeline.stage_c_normalize import normalize_compiled
from params.pipeline.stage_d_derive import derive_runtime


_LAYOUT_DPI_FOR_SPACING = 100.0


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
    denom = float(inner_span_px) - float(gap_px) * float(n_panels - 1)
    if denom <= 1e-6:
        return float(max_space)
    ratio = (float(gap_px) * float(n_panels)) / denom
    return float(min(max_space, max(0.0, ratio)))


def _sync_spacing_when_axis_mode_downgraded(
    flat_config: dict[str, Any],
    runtime_derived: dict[str, Any],
) -> None:
    compile_axis_mode = str(runtime_derived.get("compile_axis_mode", flat_config.get("axis_mode", "independent")))
    effective_axis_mode = str(runtime_derived.get("effective_axis_mode", compile_axis_mode))
    if effective_axis_mode == compile_axis_mode:
        return

    layout_spec = flat_config.get("layout_spec", {})
    adjust_spec = flat_config.get("adjust_spec", {})
    style_spec = flat_config.get("style_spec", {})
    layout_guard_spec = flat_config.get("layout_guard_spec", {})

    nrows = max(1, int(layout_spec.get("nrows", 1)))
    ncols = max(1, int(layout_spec.get("ncols", 1)))

    if effective_axis_mode == "shared_axis":
        layout_guard_spec["min_subplot_gap_px"] = 0.0
        layout_guard_spec["min_subplot_vgap_px"] = 0.0
        adjust_spec["wspace"] = 0.0
        adjust_spec["hspace"] = 0.0
        return

    spacing_basis_pt = float(style_spec.get("axis_label_size", 10.0))
    hgap_ratio = float(layout_guard_spec.get("subplot_hgap_ylabel_ratio", 0.50))
    vgap_ratio = float(layout_guard_spec.get("subplot_vgap_xlabel_ratio", 0.75))
    gap_x_px = (spacing_basis_pt * hgap_ratio * _LAYOUT_DPI_FOR_SPACING) / 72.0
    gap_y_px = (spacing_basis_pt * vgap_ratio * _LAYOUT_DPI_FOR_SPACING) / 72.0
    layout_guard_spec["min_subplot_gap_px"] = round(max(0.6, gap_x_px), 2)
    layout_guard_spec["min_subplot_vgap_px"] = round(max(0.6, gap_y_px), 2)

    width_in = float(layout_spec.get("width_mm", 0.0)) / 25.4
    aspect = max(1e-6, float(layout_spec.get("aspect_ratio", 1.0)))
    height_in = width_in / aspect
    inner_w_px = max(
        1.0,
        (float(adjust_spec.get("right", 1.0)) - float(adjust_spec.get("left", 0.0))) * width_in * _LAYOUT_DPI_FOR_SPACING,
    )
    inner_h_px = max(
        1.0,
        (float(adjust_spec.get("top", 1.0)) - float(adjust_spec.get("bottom", 0.0))) * height_in * _LAYOUT_DPI_FOR_SPACING,
    )
    if ncols <= 1:
        adjust_spec["wspace"] = 0.0
    else:
        adjust_spec["wspace"] = round(
            _derive_subplot_space_ratio(
                gap_px=float(layout_guard_spec["min_subplot_gap_px"]),
                inner_span_px=inner_w_px,
                n_panels=ncols,
                max_space=float(layout_guard_spec.get("max_wspace", 0.80)),
            ),
            4,
        )
    if nrows <= 1:
        adjust_spec["hspace"] = 0.0
    else:
        adjust_spec["hspace"] = round(
            _derive_subplot_space_ratio(
                gap_px=float(layout_guard_spec["min_subplot_vgap_px"]),
                inner_span_px=inner_h_px,
                n_panels=nrows,
                max_space=float(layout_guard_spec.get("max_hspace", 0.90)),
            ),
            4,
        )


def _has_explicit_adjust_override(overrides: dict[str, Any], layout: str) -> bool:
    explicit_adjust_keys = {"left", "right", "top", "bottom", "wspace", "hspace"}

    patch_adjust = overrides.get("adjust_spec", {})
    if isinstance(patch_adjust, dict):
        if any(key in patch_adjust for key in explicit_adjust_keys):
            return True

    by_layout = overrides.get("adjust_by_layout", {})
    if isinstance(by_layout, dict):
        layout_patch = by_layout.get(layout)
        if isinstance(layout_patch, dict):
            if any(key in layout_patch for key in explicit_adjust_keys):
                return True
    return False


def _apply_layout_prior_adjust(
    *,
    flat_config: dict[str, Any],
    runtime_derived: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    layout = str(flat_config.get("layout", ""))
    trace: dict[str, Any] = {
        "enabled": True,
        "applied": False,
        "reason": "",
        "layout": layout,
    }
    if _has_explicit_adjust_override(overrides=overrides, layout=layout):
        trace["reason"] = "skip_explicit_adjust_override"
        return trace

    layout_spec = flat_config.get("layout_spec", {})
    if not isinstance(layout_spec, dict):
        trace["reason"] = "skip_invalid_layout_spec"
        return trace

    prior_adjust, prior_trace = resolve_layout_prior_adjust(
        layout=layout,
        layout_spec=layout_spec,
        runtime_derived=runtime_derived,
    )
    trace.update(prior_trace)
    if not prior_adjust:
        trace["reason"] = f"skip_{trace.get('reason', 'not_matched')}"
        return trace

    adjust_spec = flat_config.setdefault("adjust_spec", {})
    if not isinstance(adjust_spec, dict):
        flat_config["adjust_spec"] = {}
        adjust_spec = flat_config["adjust_spec"]
    for key, value in prior_adjust.items():
        adjust_spec[key] = float(value)
    trace["applied"] = True
    trace["reason"] = "applied"
    return trace


def build_compiled_config(args: Any, overrides: dict[str, Any]) -> CompiledConfig:
    return _build_compiled_config(args=args, overrides=overrides, use_layout_prior=True)


def _build_compiled_config(
    *,
    args: Any,
    overrides: dict[str, Any],
    use_layout_prior: bool,
) -> CompiledConfig:
    assert_graph_contract()

    request = build_ingest_request(args=args, overrides=overrides)
    compiled = compile_layers(request=request)

    flat_config = normalize_compiled(deepcopy(compiled["flat_config"]))
    runtime_derived = derive_runtime(flat_config=flat_config)
    _sync_spacing_when_axis_mode_downgraded(flat_config=flat_config, runtime_derived=runtime_derived)
    if use_layout_prior:
        layout_prior_trace = _apply_layout_prior_adjust(
            flat_config=flat_config,
            runtime_derived=runtime_derived,
            overrides=overrides,
        )
    else:
        layout_prior_trace = {
            "enabled": False,
            "applied": False,
            "reason": "disabled_for_fast_assemble",
            "layout": str(flat_config.get("layout", "")),
        }

    # 让层快照与 flat_config 保持一致，避免排查时出现“显示值与实际执行值不一致”。
    compiled["l3_layout_geometry"]["adjust_spec"] = deepcopy(flat_config.get("adjust_spec", {}))
    compiled["l5_render_policy"]["layout_guard_spec"] = deepcopy(flat_config.get("layout_guard_spec", {}))

    flat_config["requested_axis_mode"] = runtime_derived["requested_axis_mode"]
    flat_config["effective_axis_mode"] = runtime_derived["effective_axis_mode"]
    flat_config["runtime_derived"] = deepcopy(runtime_derived)
    flat_config["layout_prior_trace"] = deepcopy(layout_prior_trace)

    layers = LayerSnapshot(
        l0_route=deepcopy(compiled["l0_route"]),
        l1_profile=deepcopy(compiled["l1_profile"]),
        l2_style_tokens=deepcopy(compiled["l2_style_tokens"]),
        l3_layout_geometry=deepcopy(compiled["l3_layout_geometry"]),
        l4_chart_behavior=deepcopy(compiled["l4_chart_behavior"]),
        l5_render_policy=deepcopy(compiled["l5_render_policy"]),
        l6_runtime_derived=deepcopy(runtime_derived),
    )

    return CompiledConfig(flat_config=flat_config, layers=layers)


def build_compiled_config_with_options(
    *,
    args: Any,
    overrides: dict[str, Any],
    use_layout_prior: bool = True,
) -> CompiledConfig:
    return _build_compiled_config(
        args=args,
        overrides=overrides,
        use_layout_prior=bool(use_layout_prior),
    )


__all__ = ["build_compiled_config", "build_compiled_config_with_options"]
