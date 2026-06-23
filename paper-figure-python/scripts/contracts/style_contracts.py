#!/usr/bin/env python3
"""样式与校验 profile 约定。"""

from __future__ import annotations

STYLE_TO_VALIDATE_PROFILE = {
    "elsevier": "elsevier",
    "ieee": "ieee",
    "plos": "plos",
    "nature": "thesis-journal",
    "paper-serif": "thesis-journal",
    "paper-sans": "thesis-journal",
    "presentation": "general",
}


def map_validate_profile(style_profile: str, fallback: str = "thesis-journal") -> str:
    """按 style_profile 映射默认 validate_profile。"""

    key = str(style_profile).strip().lower()
    return STYLE_TO_VALIDATE_PROFILE.get(key, fallback)


__all__ = [
    "STYLE_TO_VALIDATE_PROFILE",
    "map_validate_profile",
]
