#!/usr/bin/env python3
"""L3 画布几何默认值。"""

from __future__ import annotations

LAYOUT_SPEC_DEFAULTS = {
    "single": {"width_mm": 88.0, "aspect_ratio": 1.60},
    "double": {"width_mm": 180.0, "aspect_ratio": 1.60},
    "pair-1x2": {"width_mm": 180.0, "aspect_ratio": 1.85},
    "pair-2x1": {"width_mm": 180.0, "aspect_ratio": 1.20},
    "triple-1x3": {"width_mm": 177.8, "aspect_ratio": 2.35},
    "triple-3x1": {"width_mm": 180.0, "aspect_ratio": 1.05},
    "quad-2x2": {"width_mm": 180.0, "aspect_ratio": 1.60},
    "quad-1x4": {"width_mm": 180.0, "aspect_ratio": 2.80},
    "quad-4x1": {"width_mm": 180.0, "aspect_ratio": 0.85},
    "hex-2x3": {"width_mm": 180.0, "aspect_ratio": 1.85},
    "hex-3x2": {"width_mm": 180.0, "aspect_ratio": 1.15},
}

_ADJUST_STATIC_DEFAULTS = {
    "triple31": {"left": 0.09, "right": 0.985, "top": 0.98, "bottom": 0.12, "hspace": 0.24},
    "single": {"left": 0.18, "right": 0.98, "top": 0.98, "bottom": 0.18},
    "single_heatmap": {"left": 0.18, "right": 0.92, "top": 0.98, "bottom": 0.18},
    "quad14": {"left": 0.06, "right": 0.99, "top": 0.98, "bottom": 0.28, "wspace": 0.14},
    "quad41": {"left": 0.09, "right": 0.985, "top": 0.98, "bottom": 0.10, "hspace": 0.24},
    "hex23": {"left": 0.07, "right": 0.99, "top": 0.98, "bottom": 0.18, "wspace": 0.12, "hspace": 0.36},
    "hex32": {"left": 0.09, "right": 0.985, "top": 0.98, "bottom": 0.16, "wspace": 0.14, "hspace": 0.42},
}

ADJUST_SPEC_DEFAULTS = {
    "multi": {
        "left": 0.09,
        "right": 0.985,
        "top": 0.98,
        "bottom": 0.17,
        "wspace": 0.0,
        "hspace": 0.0,
    },
    "pair12": {
        "left": 0.09,
        "right": 0.985,
        "top": 0.98,
        "bottom": 0.17,
        "wspace": 0.0,
    },
    "pair21": {
        "left": 0.09,
        "right": 0.985,
        "top": 0.98,
        "bottom": 0.17,
        "hspace": 0.0,
    },
    "triple13": {
        "left": 0.09,
        "right": 0.985,
        "top": 0.98,
        "bottom": 0.24,
        "wspace": 0.0,
    },
    **_ADJUST_STATIC_DEFAULTS,
}

__all__ = [
    "ADJUST_SPEC_DEFAULTS",
    "LAYOUT_SPEC_DEFAULTS",
]
