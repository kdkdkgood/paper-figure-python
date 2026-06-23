#!/usr/bin/env python3
"""fast_patch 变更分级策略（单一真值源）。"""

from __future__ import annotations

from typing import Any

from jobgen_schema import TOP_LEVEL_OVERRIDE_KEYS

ROUTE_PATCH_KEYS = {
    "task",
    "chart_type",
    "layout",
    "axis_mode",
    "library",
    "style_profile",
    "style_stack",
    "multi_order",
    "seed",
    "art_type",
    "dpi",
}

L3_FORCE_KEYS = {"chart_type", "library"}
L2_ROUTE_KEYS = {"layout", "multi_order"}
L2_OVERRIDE_KEYS = {"layout_spec", "adjust_by_layout", "layout_guard_spec", "adjust_spec"}
L1_ROUTE_KEYS = {"axis_mode", "style_profile", "style_stack"}
L1_OVERRIDE_KEYS = {
    "style_spec",
    "axis_spec",
    "legend_spec",
    "color_spec",
    "primitive_spec",
    "panel_label_spec",
}


def infer_change_level(
    *,
    route_patch: dict[str, Any],
    override_patch: dict[str, Any],
    requested_level: str,
    intent_entry: dict[str, Any] | None,
) -> str:
    """自动推断变更等级。"""

    level = str(requested_level).strip().upper()
    if level in {"L1", "L2", "L3"}:
        return level

    if isinstance(intent_entry, dict):
        intent_level = str(intent_entry.get("level", "")).strip().upper()
        if intent_level in {"L1", "L2", "L3"}:
            return intent_level

    route_keys = set(route_patch.keys())
    override_keys = set(override_patch.keys())
    if route_keys & L3_FORCE_KEYS:
        return "L3"
    if (route_keys & L2_ROUTE_KEYS) or (override_keys & L2_OVERRIDE_KEYS):
        return "L2"
    if (route_keys & L1_ROUTE_KEYS) or (override_keys & L1_OVERRIDE_KEYS):
        return "L1"
    return "L1"


def contract_violation_reason(
    *,
    level: str,
    route_patch: dict[str, Any],
    override_patch: dict[str, Any],
    route_allow: set[str],
    override_allow: set[str],
) -> str | None:
    """检查当前 patch 是否满足分级合同。"""

    if level == "L3":
        return "L3 级别变更：建议重生成项目。"

    unknown_route = sorted(set(route_patch.keys()) - ROUTE_PATCH_KEYS)
    if unknown_route:
        return f"route patch 含未知键: {unknown_route}"

    unknown_override = sorted(set(override_patch.keys()) - TOP_LEVEL_OVERRIDE_KEYS)
    if unknown_override:
        return f"overrides 含未知键: {unknown_override}"

    if route_allow:
        route_disallow = sorted(set(route_patch.keys()) - route_allow)
        if route_disallow:
            return f"{level} 不允许 route 键: {route_disallow}"

    if override_allow:
        override_disallow = sorted(set(override_patch.keys()) - override_allow)
        if override_disallow:
            return f"{level} 不允许 override 键: {override_disallow}"

    return None


__all__ = [
    "L1_OVERRIDE_KEYS",
    "L1_ROUTE_KEYS",
    "L2_OVERRIDE_KEYS",
    "L2_ROUTE_KEYS",
    "L3_FORCE_KEYS",
    "ROUTE_PATCH_KEYS",
    "contract_violation_reason",
    "infer_change_level",
]
