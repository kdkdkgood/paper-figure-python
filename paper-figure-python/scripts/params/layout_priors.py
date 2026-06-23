#!/usr/bin/env python3
"""Layout prior resolver with a strict first-layer filter.

Lookup order:
1) shape_axis_key = "<nrows>x<ncols>|<effective_axis_mode>"
2) exact panel_types_signature, fallback to default_variant

v3: per-shape split files instead of monolith records.
"""

from __future__ import annotations

from collections import Counter
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_PRIORS_DIR = Path(__file__).resolve().parents[2] / "references" / "layout_priors"
_PRIORS_INDEX_FILE = Path(__file__).resolve().parents[2] / "references" / "layout_priors_index.json"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _build_shape_axis_key(layout_spec: dict[str, Any], effective_axis_mode: str) -> str:
    nrows = max(1, int(layout_spec.get("nrows", 1)))
    ncols = max(1, int(layout_spec.get("ncols", 1)))
    return f"{nrows}x{ncols}|{effective_axis_mode}"


def _build_panel_signature(runtime_derived: dict[str, Any]) -> str:
    panel_types = runtime_derived.get("panel_types", [])
    if not isinstance(panel_types, list) or not panel_types:
        return ""
    return "+".join(str(item) for item in panel_types)


def _tokenize_panel_signature(signature: str) -> list[str]:
    if not signature:
        return []
    return [part.strip() for part in str(signature).split("+") if part.strip()]


def _panel_signature_similarity(left: str, right: str) -> float:
    left_tokens = _tokenize_panel_signature(left)
    right_tokens = _tokenize_panel_signature(right)
    if not left_tokens or not right_tokens:
        return -1.0
    if len(left_tokens) != len(right_tokens):
        return -1.0

    total = float(len(left_tokens))
    positional_score = sum(1 for l_tok, r_tok in zip(left_tokens, right_tokens) if l_tok == r_tok) / total
    left_counter = Counter(left_tokens)
    right_counter = Counter(right_tokens)
    overlap_score = sum(min(count, right_counter.get(key, 0)) for key, count in left_counter.items()) / total
    return float(0.65 * overlap_score + 0.35 * positional_score)


def _pick_similar_variant(
    panel_signature: str,
    variants: set[str],
    default_variant: str,
) -> tuple[str, float] | None:
    if not panel_signature or not variants:
        return None

    best_key = ""
    best_score = -1.0
    for candidate in variants:
        if candidate == panel_signature:
            continue
        score = _panel_signature_similarity(panel_signature, candidate)
        if score > best_score:
            best_score = score
            best_key = candidate

    # 低分场景不使用相似匹配，交给 default 兜底。
    if best_score < 0.35 or not best_key:
        return None
    # 即使命中 default_variant，也透出"similar"来源，便于追踪。
    if best_key == default_variant:
        return best_key, best_score
    return best_key, best_score


@lru_cache(maxsize=None)
def _load_prior_for_shape(shape_axis_key: str) -> dict[str, Any]:
    """Load a single per-shape prior file."""
    filename = shape_axis_key.replace("|", "_") + ".json"
    filepath = _PRIORS_DIR / filename
    if not filepath.exists():
        return {}
    payload = json.loads(filepath.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return payload


@lru_cache(maxsize=1)
def _load_priors_index() -> dict[str, Any]:
    if not _PRIORS_INDEX_FILE.exists():
        return {}
    payload = json.loads(_PRIORS_INDEX_FILE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return payload


def resolve_layout_prior_adjust(
    *,
    layout: str,
    layout_spec: dict[str, Any],
    runtime_derived: dict[str, Any],
) -> tuple[dict[str, float] | None, dict[str, Any]]:
    priors_index = _load_priors_index()
    effective_axis_mode = str(runtime_derived.get("effective_axis_mode", "independent"))
    shape_axis_key = _build_shape_axis_key(layout_spec, effective_axis_mode)
    panel_signature = _build_panel_signature(runtime_derived)

    trace: dict[str, Any] = {
        "source": str(_PRIORS_DIR / (shape_axis_key.replace("|", "_") + ".json")),
        "index_source": str(_PRIORS_INDEX_FILE),
        "version": str(priors_index.get("version", "")),
        "layout": str(layout),
        "shape_axis_key": shape_axis_key,
        "shape_axis_key_used": "",
        "shape_axis_match_mode": "",
        "panel_types_signature": panel_signature,
        "matched": False,
        "reason": "",
        "variant_key": "",
        "variant_match_mode": "",
    }

    # 先用轻量索引做首层过滤，未命中时不读取分片文件。
    routes_map = priors_index.get("routes", {})
    if not isinstance(routes_map, dict):
        trace["reason"] = "index_invalid"
        return None, trace
    if shape_axis_key not in routes_map:
        trace["reason"] = "shape_axis_not_found"
        return None, trace
    trace["shape_axis_match_mode"] = "exact"
    trace["shape_axis_key_used"] = shape_axis_key

    # 加载对应的分片文件。
    bucket = _load_prior_for_shape(shape_axis_key)
    if not bucket:
        trace["reason"] = "record_bucket_missing"
        return None, trace

    allowed_layouts = bucket.get("allowed_layouts", [])
    if isinstance(allowed_layouts, list) and allowed_layouts:
        allowed_layout_set = {str(item) for item in allowed_layouts}
        layout_allowed = str(layout) in allowed_layout_set
        trace["layout_allowed"] = layout_allowed
        if not layout_allowed:
            trace["reason"] = "layout_not_allowed_in_bucket"
            return None, trace

    variants = bucket.get("variants", {})
    if not isinstance(variants, dict) or not variants:
        trace["reason"] = "variants_empty"
        return None, trace

    nav_variant_set = set(variants.keys())
    default_variant = str(bucket.get("default_variant", ""))

    if panel_signature in nav_variant_set:
        variant_key = panel_signature
        trace["variant_match_mode"] = "exact"
    else:
        similar_variant = _pick_similar_variant(panel_signature, nav_variant_set, default_variant)
        if similar_variant is not None:
            variant_key, variant_similarity_score = similar_variant
            trace["variant_match_mode"] = "similar"
            trace["variant_similarity_score"] = round(float(variant_similarity_score), 4)
        else:
            variant_key = default_variant
            trace["variant_match_mode"] = "default"
    if not variant_key or variant_key not in nav_variant_set:
        trace["reason"] = "variant_not_found"
        return None, trace

    record = variants.get(variant_key, {})
    if not isinstance(record, dict):
        trace["reason"] = "variant_invalid"
        return None, trace

    adjust_raw = record.get("adjust_spec", {})
    if not isinstance(adjust_raw, dict):
        trace["reason"] = "adjust_spec_invalid"
        return None, trace

    adjust: dict[str, float] = {}
    for key in ("left", "right", "top", "bottom", "wspace", "hspace"):
        value = adjust_raw.get(key)
        if _is_number(value):
            adjust[key] = float(value)
    if not adjust:
        trace["reason"] = "adjust_spec_empty"
        return None, trace

    trace["matched"] = True
    trace["reason"] = "ok"
    trace["variant_key"] = variant_key
    return adjust, trace


__all__ = ["resolve_layout_prior_adjust"]
