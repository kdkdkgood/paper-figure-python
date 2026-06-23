#!/usr/bin/env python3
"""最终编译配置结构。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class LayerSnapshot:
    l0_route: dict[str, Any] = field(default_factory=dict)
    l1_profile: dict[str, Any] = field(default_factory=dict)
    l2_style_tokens: dict[str, Any] = field(default_factory=dict)
    l3_layout_geometry: dict[str, Any] = field(default_factory=dict)
    l4_chart_behavior: dict[str, Any] = field(default_factory=dict)
    l5_render_policy: dict[str, Any] = field(default_factory=dict)
    l6_runtime_derived: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "l0_route": deepcopy(self.l0_route),
            "l1_profile": deepcopy(self.l1_profile),
            "l2_style_tokens": deepcopy(self.l2_style_tokens),
            "l3_layout_geometry": deepcopy(self.l3_layout_geometry),
            "l4_chart_behavior": deepcopy(self.l4_chart_behavior),
            "l5_render_policy": deepcopy(self.l5_render_policy),
            "l6_runtime_derived": deepcopy(self.l6_runtime_derived),
        }


@dataclass
class CompiledConfig:
    flat_config: dict[str, Any]
    layers: LayerSnapshot

    def as_dict(self) -> dict[str, Any]:
        payload = deepcopy(self.flat_config)
        payload["layers_snapshot"] = self.layers.to_dict()
        return payload


__all__ = ["CompiledConfig", "LayerSnapshot"]
