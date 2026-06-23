#!/usr/bin/env python3
"""Stage A: 输入规整。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _parse_style_stack(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(raw, list):
        return [str(part).strip() for part in raw if str(part).strip()]
    return []


def build_ingest_request(args: Any, overrides: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": str(getattr(args, "task", "科研绘图任务")),
        "route": {
            "chart_type": str(getattr(args, "chart_type", "multi")),
            "layout": str(getattr(args, "layout", "")).strip(),
            "axis_mode": str(getattr(args, "axis_mode", "auto")),
            "library": str(getattr(args, "library", "matplotlib")),
            "art_type": str(getattr(args, "art_type", "combo")),
            "multi_order": getattr(args, "multi_order", "line,bar,scatter,heatmap"),
            "seed": int(getattr(args, "seed", 42)),
            "dpi": int(getattr(args, "dpi", 0)),
        },
        "profile": {
            "style_profile": str(getattr(args, "style_profile", "elsevier")),
            "style_stack": _parse_style_stack(getattr(args, "style_stack", "")),
        },
        "overrides": deepcopy(overrides or {}),
    }


__all__ = ["build_ingest_request"]
