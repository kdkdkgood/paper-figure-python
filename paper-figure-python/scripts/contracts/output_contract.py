#!/usr/bin/env python3
"""统一输出契约工具。"""

from __future__ import annotations

from typing import Any


def resolve_axis_mode_state(config: dict[str, Any]) -> dict[str, Any]:
    """统一提取 requested/compile/effective 三态。"""

    runtime = config.get("runtime_derived", {})
    if not isinstance(runtime, dict):
        runtime = {}

    requested = str(
        config.get(
            "requested_axis_mode",
            runtime.get("requested_axis_mode", config.get("axis_mode", "independent")),
        )
    )
    compile_mode = str(runtime.get("compile_axis_mode", config.get("axis_mode", "independent")))
    effective = str(
        config.get(
            "effective_axis_mode",
            runtime.get("effective_axis_mode", compile_mode),
        )
    )
    share_axes = bool(runtime.get("share_axes", effective == "shared_axis"))

    return {
        "requested": requested,
        "compile": compile_mode,
        "effective": effective,
        "share_axes": share_axes,
    }


def build_route_key(config: dict[str, Any]) -> dict[str, Any]:
    """统一路由键输出，避免 axis_mode 语义歧义。"""

    return {
        "chart_type": str(config.get("chart_type", "")),
        "layout": str(config.get("layout", "")),
        "library": str(config.get("library", "")),
        "axis_mode": resolve_axis_mode_state(config),
    }


__all__ = [
    "build_route_key",
    "resolve_axis_mode_state",
]
