#!/usr/bin/env python3
"""参数层依赖图定义。"""

from __future__ import annotations

LAYER_ORDER = [
    "l0_route",
    "l1_profile",
    "l2_style_tokens",
    "l3_layout_geometry",
    "l4_chart_behavior",
    "l5_render_policy",
    "l6_runtime_derived",
]

LAYER_DEPENDENCIES = {
    "l0_route": set(),
    "l1_profile": set(),
    "l2_style_tokens": {"l1_profile"},
    "l3_layout_geometry": {"l0_route"},
    "l4_chart_behavior": {"l0_route"},
    "l5_render_policy": {"l2_style_tokens", "l3_layout_geometry", "l4_chart_behavior"},
    "l6_runtime_derived": {"l0_route", "l3_layout_geometry", "l4_chart_behavior", "l5_render_policy"},
}

__all__ = ["LAYER_DEPENDENCIES", "LAYER_ORDER"]
