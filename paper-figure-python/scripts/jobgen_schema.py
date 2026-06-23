#!/usr/bin/env python3
"""create_figure 的共享常量与 schema。"""

from __future__ import annotations

import re

from params.contracts.layer_keys import ADJUST_KEYS
from params.contracts.layer_keys import ALLOWED_STYLE_KEYS
from params.contracts.layer_keys import AXIS_SPEC_KEYS
from params.contracts.layer_keys import CHART_SPEC_TYPE_KEYS
from params.contracts.layer_keys import COLOR_SPEC_KEYS
from params.contracts.layer_keys import DATA_SPEC_KEYS
from params.contracts.layer_keys import CROP_SPEC_KEYS
from params.contracts.layer_keys import LAYOUT_GUARD_SPEC_KEYS
from params.contracts.layer_keys import LAYOUT_SPEC_KEYS
from params.contracts.layer_keys import LEGEND_SPEC_KEYS
from params.contracts.layer_keys import PANEL_LABEL_SPEC_KEYS
from params.contracts.layer_keys import PRIMITIVE_SPEC_KEYS
from params.contracts.layer_keys import TOP_LEVEL_OVERRIDE_KEYS
from params.defaults.l0_route_defaults import CHART_TYPE_CHOICES
from params.defaults.l0_route_defaults import LAYOUT_GRID
from params.defaults.l0_route_defaults import LAYOUT_TO_ADJUST_KEY
from params.defaults.l0_route_defaults import PANEL_TYPE_SEQUENCE
from params.defaults.l0_route_defaults import SUPPORTED_PANEL_TYPES
from params.defaults.l1_profile_defaults import DEFAULT_STYLE_PROFILE
from params.defaults.l1_profile_defaults import LOCAL_STYLE_STACK_OVERRIDES
from params.defaults.l1_profile_defaults import PROFILE_DPI
from params.defaults.l1_profile_defaults import STYLE_LAYERS
from params.defaults.l1_profile_defaults import STYLE_PROFILES
from params.defaults.l3_layout_defaults import ADJUST_SPEC_DEFAULTS as BASE_ADJUST_SPEC
from params.defaults.l3_layout_defaults import LAYOUT_SPEC_DEFAULTS as BASE_LAYOUT_SPEC
from params.defaults.l4_chart_defaults import CHART_SPEC_DEFAULTS as BASE_CHART_SPEC
from params.defaults.l4_chart_defaults import COLOR_SPEC_DEFAULTS as BASE_COLOR_SPEC
from params.defaults.l4_chart_defaults import DATA_SPEC_DEFAULTS as BASE_DATA_SPEC
from params.defaults.l4_chart_defaults import PRIMITIVE_SPEC_DEFAULTS as BASE_PRIMITIVE_SPEC
from params.defaults.l5_render_defaults import AXIS_SPEC_DEFAULTS as BASE_AXIS_SPEC
from params.defaults.l5_render_defaults import CROP_SPEC_DEFAULTS as BASE_CROP_SPEC
from params.defaults.l5_render_defaults import LAYOUT_GUARD_SPEC_DEFAULTS as BASE_LAYOUT_GUARD_SPEC
from params.defaults.l5_render_defaults import LEGEND_SPEC_DEFAULTS as BASE_LEGEND_SPEC
from params.defaults.l5_render_defaults import PANEL_LABEL_SPEC_DEFAULTS as BASE_PANEL_LABEL_SPEC

DEFAULT_DPI_BY_ART_TYPE = dict(PROFILE_DPI.get("thesis-journal", {"line": 1000, "photo": 600, "combo": 600}))
TEMPLATE_VERSION = "3.0.0"

TAG_RE = re.compile(
    r"^# FIGURE_TAG:\s*chart_type=(?P<chart_type>[^;]+);layout=(?P<layout>[^;]+);"
    r"axis_mode=(?P<axis_mode>[^;]+);library=(?P<library>[^;]+);style_profile=(?P<style_profile>[^;\n]+)\s*$"
)
CONFIG_BLOCK_RE = re.compile(r"(?s)# --- CONFIG START ---\n.*?# --- CONFIG END ---")
TEMPLATE_VERSION_RE = re.compile(r"^# TEMPLATE_VERSION:\s*(?P<version>[^\s]+)\s*$")


__all__ = [
    "ADJUST_KEYS",
    "ALLOWED_STYLE_KEYS",
    "AXIS_SPEC_KEYS",
    "BASE_ADJUST_SPEC",
    "BASE_AXIS_SPEC",
    "BASE_CHART_SPEC",
    "BASE_COLOR_SPEC",
    "BASE_DATA_SPEC",
    "BASE_CROP_SPEC",
    "BASE_LAYOUT_GUARD_SPEC",
    "BASE_LAYOUT_SPEC",
    "BASE_LEGEND_SPEC",
    "BASE_PANEL_LABEL_SPEC",
    "BASE_PRIMITIVE_SPEC",
    "CHART_SPEC_TYPE_KEYS",
    "CHART_TYPE_CHOICES",
    "COLOR_SPEC_KEYS",
    "DATA_SPEC_KEYS",
    "CONFIG_BLOCK_RE",
    "CROP_SPEC_KEYS",
    "DEFAULT_DPI_BY_ART_TYPE",
    "DEFAULT_STYLE_PROFILE",
    "LAYOUT_GUARD_SPEC_KEYS",
    "LAYOUT_GRID",
    "LAYOUT_SPEC_KEYS",
    "LAYOUT_TO_ADJUST_KEY",
    "LEGEND_SPEC_KEYS",
    "LOCAL_STYLE_STACK_OVERRIDES",
    "PANEL_LABEL_SPEC_KEYS",
    "PANEL_TYPE_SEQUENCE",
    "PRIMITIVE_SPEC_KEYS",
    "STYLE_LAYERS",
    "STYLE_PROFILES",
    "SUPPORTED_PANEL_TYPES",
    "TAG_RE",
    "TEMPLATE_VERSION",
    "TEMPLATE_VERSION_RE",
    "TOP_LEVEL_OVERRIDE_KEYS",
]
