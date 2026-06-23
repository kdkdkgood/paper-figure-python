#!/usr/bin/env python3
"""Stage D: 运行时派生层。"""

from __future__ import annotations

from typing import Any

from params.defaults.l0_route_defaults import DEFAULT_MULTI_ORDER


def _collect_panel_types(cfg: dict[str, Any], n_panels: int) -> list[str]:
    if cfg.get("chart_type") != "multi":
        return [str(cfg.get("chart_type", "line")) for _ in range(max(1, n_panels))]

    order = cfg.get("multi_order", DEFAULT_MULTI_ORDER)
    if not isinstance(order, list) or not order:
        order = DEFAULT_MULTI_ORDER
    return [str(order[idx % len(order)]) for idx in range(max(1, n_panels))]


def _resolve_effective_axis_mode(
    requested: str,
    nrows: int,
    ncols: int,
    is_mixed_multi: bool,
) -> str:
    if requested != "shared_axis":
        return "independent"
    if (nrows * ncols) <= 1:
        return "independent"
    if is_mixed_multi:
        return "independent"
    return "shared_axis"


def derive_runtime(flat_config: dict[str, Any]) -> dict[str, Any]:
    nrows = int(flat_config["layout_spec"]["nrows"])
    ncols = int(flat_config["layout_spec"]["ncols"])
    n_panels = max(1, nrows * ncols)

    panel_types = _collect_panel_types(flat_config, n_panels)
    is_mixed_multi = flat_config.get("chart_type") == "multi" and len(set(panel_types)) > 1

    requested_axis_mode = str(flat_config.get("requested_axis_mode", flat_config.get("axis_mode", "independent")))
    compile_axis_mode = str(flat_config.get("axis_mode", "independent"))
    effective_axis_mode = _resolve_effective_axis_mode(
        requested=compile_axis_mode,
        nrows=nrows,
        ncols=ncols,
        is_mixed_multi=is_mixed_multi,
    )

    return {
        "requested_axis_mode": requested_axis_mode,
        "compile_axis_mode": compile_axis_mode,
        "effective_axis_mode": effective_axis_mode,
        "panel_types": panel_types,
        "share_axes": effective_axis_mode == "shared_axis",
    }


__all__ = ["derive_runtime"]
