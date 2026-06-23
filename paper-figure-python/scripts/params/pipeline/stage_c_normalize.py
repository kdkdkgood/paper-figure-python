#!/usr/bin/env python3
"""Stage C: 编译态归一化。"""

from __future__ import annotations

from typing import Any

from params.defaults.l0_route_defaults import LIBRARY_CHOICES
from params.defaults.l1_profile_defaults import STYLE_PROFILES
from params.defaults.l3_layout_defaults import LAYOUT_SPEC_DEFAULTS


def normalize_compiled(flat_config: dict[str, Any]) -> dict[str, Any]:
    chart_type = flat_config.get("chart_type")
    if not isinstance(chart_type, str) or not chart_type.strip():
        raise ValueError("chart_type 必须是非空字符串")

    layout = flat_config.get("layout")
    if layout not in LAYOUT_SPEC_DEFAULTS:
        raise ValueError(f"layout 不支持: {layout}")

    axis_mode = flat_config.get("axis_mode")
    if axis_mode not in {"shared_axis", "independent"}:
        raise ValueError(f"axis_mode 不支持: {axis_mode}")

    library = flat_config.get("library")
    if library not in LIBRARY_CHOICES:
        raise ValueError(f"library 不支持: {library}")

    style_profile = flat_config.get("style_profile")
    if style_profile not in STYLE_PROFILES:
        raise ValueError(f"style_profile 不支持: {style_profile}")

    return flat_config


__all__ = ["normalize_compiled"]
