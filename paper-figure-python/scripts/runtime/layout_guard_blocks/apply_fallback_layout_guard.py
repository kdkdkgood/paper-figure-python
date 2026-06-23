def _snapshot_adjust(adjust: dict) -> tuple[float, float, float, float, float, float]:
    return (
        float(adjust.get("left", 0.0)),
        float(adjust.get("right", 1.0)),
        float(adjust.get("top", 1.0)),
        float(adjust.get("bottom", 0.0)),
        float(adjust.get("wspace", 0.0)),
        float(adjust.get("hspace", 0.0)),
    )


def _derive_subplot_space_ratio(
    *,
    gap_px: float,
    inner_span_px: float,
    n_panels: int,
    max_space: float,
) -> float:
    if n_panels <= 1:
        return 0.0
    if gap_px <= 0.0 or inner_span_px <= 1e-6:
        return 0.0
    denom = float(inner_span_px) - float(gap_px) * float(n_panels - 1)
    if denom <= 1e-6:
        return float(max_space)
    ratio = (float(gap_px) * float(n_panels)) / denom
    return float(min(max_space, max(0.0, ratio)))


def _renderer_size_px(fig: plt.Figure) -> tuple[float, float]:
    """返回与 bbox 同坐标系的画布尺寸。"""

    try:
        renderer = fig.canvas.get_renderer()
    except Exception:
        renderer = None
    if renderer is not None:
        width = float(getattr(renderer, "width", 0.0))
        height = float(getattr(renderer, "height", 0.0))
        if width > 1e-6 and height > 1e-6:
            return width, height
    cw, ch = fig.canvas.get_width_height()
    return float(cw), float(ch)


def _relock_spacing_to_font_basis(
    adjust: dict,
    *,
    guard_spec: dict,
    fig_w_px: float,
    fig_h_px: float,
    nrows: int,
    ncols: int,
) -> None:
    left = float(adjust.get("left", 0.0))
    right = float(adjust.get("right", 1.0))
    bottom = float(adjust.get("bottom", 0.0))
    top = float(adjust.get("top", 1.0))
    inner_w_px = max(1.0, (right - left) * float(fig_w_px))
    inner_h_px = max(1.0, (top - bottom) * float(fig_h_px))

    if ncols <= 1:
        adjust["wspace"] = 0.0
    else:
        target = _derive_subplot_space_ratio(
            gap_px=float(guard_spec.get("min_subplot_gap_px", 0.0)),
            inner_span_px=inner_w_px,
            n_panels=ncols,
            max_space=float(guard_spec.get("max_wspace", 0.80)),
        )
        adjust["wspace"] = float(target)

    if nrows <= 1:
        adjust["hspace"] = 0.0
    else:
        target = _derive_subplot_space_ratio(
            gap_px=float(guard_spec.get("min_subplot_vgap_px", 0.0)),
            inner_span_px=inner_h_px,
            n_panels=nrows,
            max_space=float(guard_spec.get("max_hspace", 0.90)),
        )
        adjust["hspace"] = float(target)


def _gap_step_px(*, amount_px: float, pass_idx: int, mode: str) -> float:
    """步长控制策略（新）：close 激进、trim 保守，避免旧策略的来回振荡。"""
    if amount_px <= 0.0:
        return 0.0
    if mode == "close":
        gain = min(1.0, 0.80 + 0.06 * max(0, pass_idx - 1))
        min_step_px = 0.30
    else:
        gain = max(0.35, 0.62 - 0.05 * max(0, pass_idx - 1))
        min_step_px = 0.20
    step_px = max(min_step_px, float(amount_px) * gain)
    return float(min(float(amount_px), step_px))


def _remaining_side_adjust_budget(
    *,
    side: str,
    current: float,
    baseline: float,
    total_budget: float,
) -> float:
    if side in {"left", "bottom"}:
        used = max(0.0, float(current) - float(baseline))
    elif side in {"right", "top"}:
        used = max(0.0, float(baseline) - float(current))
    else:
        return 0.0
    return max(0.0, float(total_budget) - float(used))


def apply_fallback_layout_guard(
    fig: plt.Figure,
    cfg: dict,
    adjust: dict,
    *,
    axes_grid=None,
    nrows=None,
    ncols=None,
    axis_mode=None,
) -> dict:
    guard_spec = dict(cfg["layout_guard_spec"])
    report = {
        "applied": False,
        "scale_triggered": False,
        "passes": [],
        "baseline_adjust": {},
        "baseline_size_in": [],
        "final_adjust": {},
        "final_adjust_delta_from_baseline": {},
        "final_size_in": [],
        "final_scale_from_baseline": {},
    }
    if not bool(guard_spec.get("enabled", True)) or not bool(guard_spec.get("fallback_enabled", True)):
        report["final_adjust"] = {
            "left": float(adjust.get("left", 0.0)),
            "right": float(adjust.get("right", 1.0)),
            "top": float(adjust.get("top", 1.0)),
            "bottom": float(adjust.get("bottom", 0.0)),
            "wspace": float(adjust.get("wspace", 0.0)),
            "hspace": float(adjust.get("hspace", 0.0)),
        }
        report["final_size_in"] = [float(fig.get_size_inches()[0]), float(fig.get_size_inches()[1])]
        return report

    guard_intent = str(guard_spec.get("intent", "balanced")).strip().lower()
    if guard_intent not in {"compact", "balanced", "roomy", "preserve_data"}:
        guard_intent = "balanced"
    preferred_canvas_scale = max(1.0, float(guard_spec.get("preferred_canvas_scale", 1.0)))
    if guard_intent == "roomy":
        preferred_canvas_scale = max(preferred_canvas_scale, 1.10)
        guard_spec["max_side_adjust_frac"] = min(float(guard_spec.get("max_side_adjust_frac", 0.18)), 0.12)
        guard_spec["overflow_scale_trigger_ratio"] = min(float(guard_spec.get("overflow_scale_trigger_ratio", 0.08)), 0.05)
    elif guard_intent == "preserve_data":
        preferred_canvas_scale = max(preferred_canvas_scale, 1.05)
        guard_spec["max_side_adjust_frac"] = min(float(guard_spec.get("max_side_adjust_frac", 0.18)), 0.08)
        guard_spec["overflow_scale_trigger_ratio"] = min(float(guard_spec.get("overflow_scale_trigger_ratio", 0.08)), 0.03)
        guard_spec["min_inner_width_frac"] = max(float(guard_spec.get("min_inner_width_frac", 0.42)), 0.60)
        guard_spec["min_inner_height_frac"] = max(float(guard_spec.get("min_inner_height_frac", 0.42)), 0.60)

    max_passes = max(0, int(guard_spec.get("max_fallback_passes", 4)))
    if max_passes <= 0:
        report["final_adjust"] = {
            "left": float(adjust.get("left", 0.0)),
            "right": float(adjust.get("right", 1.0)),
            "top": float(adjust.get("top", 1.0)),
            "bottom": float(adjust.get("bottom", 0.0)),
            "wspace": float(adjust.get("wspace", 0.0)),
            "hspace": float(adjust.get("hspace", 0.0)),
        }
        report["final_size_in"] = [float(fig.get_size_inches()[0]), float(fig.get_size_inches()[1])]
        return report

    edge_tolerance_px = float(guard_spec.get("edge_tolerance_px", 0.8))
    gap_tolerance_px = max(edge_tolerance_px, float(guard_spec.get("subplot_overlap_tolerance_px", 0.8)))
    overflow_pad_px = float(guard_spec.get("overflow_pad_px", 4.0))
    # max_side_adjust_frac 按"单侧累计预算"解释：超过预算后优先放大图幅，不再继续挤压边距。
    max_side_adjust_frac = max(0.0, float(guard_spec.get("max_side_adjust_frac", 0.12)))
    # 单轮步进上限与预算/轮数联动，确保在 max_passes 内能用完全部预算。
    max_side_adjust_step_frac = min(max_side_adjust_frac, max(0.015, max_side_adjust_frac / max(max_passes, 1)))
    overflow_scale_trigger_ratio = float(guard_spec.get("overflow_scale_trigger_ratio", 0.08))
    max_total_scale = max(float(guard_spec.get("max_total_scale", 2.0)), float(preferred_canvas_scale))
    # 单轮等比放大步长上限，避免图幅变化过猛。
    max_scale_step_per_pass = max(0.05, float(guard_spec.get("max_scale_step_per_pass", 0.30)))
    # 相对初始宽高比的最大允许偏移比例。
    max_aspect_ratio_drift_frac = max(0.0, float(guard_spec.get("max_aspect_ratio_drift_frac", 0.03)))

    nrows_eff = int(nrows if nrows is not None else (axes_grid.shape[0] if axes_grid is not None else 1))
    ncols_eff = int(ncols if ncols is not None else (axes_grid.shape[1] if axes_grid is not None else 1))
    min_hgap_px = float(guard_spec.get("min_subplot_gap_px", 0.0))
    min_vgap_px = float(guard_spec.get("min_subplot_vgap_px", 0.0))
    mode_eff = str(axis_mode if axis_mode is not None else cfg.get("effective_axis_mode", cfg.get("axis_mode", ""))).lower()
    shared_axis_zero_gap = mode_eff == "shared_axis"
    if shared_axis_zero_gap:
        min_hgap_px = 0.0
        min_vgap_px = 0.0
        adjust["wspace"] = 0.0
        adjust["hspace"] = 0.0

    baseline_adjust = {
        "left": float(adjust.get("left", 0.0)),
        "right": float(adjust.get("right", 1.0)),
        "top": float(adjust.get("top", 1.0)),
        "bottom": float(adjust.get("bottom", 0.0)),
    }

    base_w_in, base_h_in = fig.get_size_inches()
    if preferred_canvas_scale > 1.0 + 1e-9:
        fig.set_size_inches(float(base_w_in) * float(preferred_canvas_scale), float(base_h_in) * float(preferred_canvas_scale), forward=True)
        report["applied"] = True
        report["preferred_canvas_scale_applied"] = float(preferred_canvas_scale)
    report["baseline_adjust"] = {
        "left": float(baseline_adjust["left"]),
        "right": float(baseline_adjust["right"]),
        "top": float(baseline_adjust["top"]),
        "bottom": float(baseline_adjust["bottom"]),
        "wspace": float(adjust.get("wspace", 0.0)),
        "hspace": float(adjust.get("hspace", 0.0)),
    }
    report["baseline_size_in"] = [float(base_w_in), float(base_h_in)]
    base_aspect_ratio = float(base_w_in) / max(float(base_h_in), 1e-9)
    aspect_ratio_min = max(1e-6, float(base_aspect_ratio) * (1.0 - float(max_aspect_ratio_drift_frac)))
    aspect_ratio_max = float(base_aspect_ratio) * (1.0 + float(max_aspect_ratio_drift_frac))
    # 双向收敛：目标 gap 既可因缺口增大，也可在过大时回缩到基线。
    target_hgap_px = float(min_hgap_px)
    target_vgap_px = float(min_vgap_px)

    for pass_idx in range(1, max_passes + 1):
        fig.canvas.draw()
        bbox = _collect_figure_bbox_px(fig)
        if bbox is None:
            report["passes"].append({"pass": pass_idx, "status": "empty_bbox", "actions": []})
            break

        fig_w_px, fig_h_px = _renderer_size_px(fig)
        overflow = _compute_overflow_px(bbox, float(fig_w_px), float(fig_h_px), overflow_pad_px)
        has_overflow = max(overflow.values()) > edge_tolerance_px
        overflow_ratio = {
            "x": max(float(overflow["left"]), float(overflow["right"])) / max(float(fig_w_px), 1.0),
            "y": max(float(overflow["bottom"]), float(overflow["top"])) / max(float(fig_h_px), 1.0),
        }
        remaining_budget = {
            "left": _remaining_side_adjust_budget(
                side="left",
                current=float(adjust.get("left", 0.0)),
                baseline=float(baseline_adjust["left"]),
                total_budget=max_side_adjust_frac,
            ),
            "right": _remaining_side_adjust_budget(
                side="right",
                current=float(adjust.get("right", 1.0)),
                baseline=float(baseline_adjust["right"]),
                total_budget=max_side_adjust_frac,
            ),
            "top": _remaining_side_adjust_budget(
                side="top",
                current=float(adjust.get("top", 1.0)),
                baseline=float(baseline_adjust["top"]),
                total_budget=max_side_adjust_frac,
            ),
            "bottom": _remaining_side_adjust_budget(
                side="bottom",
                current=float(adjust.get("bottom", 0.0)),
                baseline=float(baseline_adjust["bottom"]),
                total_budget=max_side_adjust_frac,
            ),
        }
        used_from_baseline = {
            "left": max(0.0, float(adjust.get("left", 0.0)) - float(baseline_adjust["left"])),
            "right": max(0.0, float(baseline_adjust["right"]) - float(adjust.get("right", 1.0))),
            "top": max(0.0, float(baseline_adjust["top"]) - float(adjust.get("top", 1.0))),
            "bottom": max(0.0, float(adjust.get("bottom", 0.0)) - float(baseline_adjust["bottom"])),
        }
        budget_denom = max(float(max_side_adjust_frac), 1e-9)
        used_ratio_from_baseline = {
            k: float(v) / float(budget_denom) for k, v in used_from_baseline.items()
        }
        baseline_budget_exhausted_x = bool(
            ((float(overflow["left"]) > edge_tolerance_px) and (float(used_ratio_from_baseline["left"]) >= 1.0 - 1e-6))
            or ((float(overflow["right"]) > edge_tolerance_px) and (float(used_ratio_from_baseline["right"]) >= 1.0 - 1e-6))
        )
        baseline_budget_exhausted_y = bool(
            ((float(overflow["bottom"]) > edge_tolerance_px) and (float(used_ratio_from_baseline["bottom"]) >= 1.0 - 1e-6))
            or ((float(overflow["top"]) > edge_tolerance_px) and (float(used_ratio_from_baseline["top"]) >= 1.0 - 1e-6))
        )
        prefer_scale_x = bool(
            (overflow_ratio["x"] > overflow_scale_trigger_ratio)
            or baseline_budget_exhausted_x
        )
        prefer_scale_y = bool(
            (overflow_ratio["y"] > overflow_scale_trigger_ratio)
            or baseline_budget_exhausted_y
        )
        force_scale_due_to_baseline_budget = bool(
            has_overflow and (baseline_budget_exhausted_x or baseline_budget_exhausted_y)
        )

        gap_deficit = {"horizontal": 0.0, "vertical": 0.0}
        raw_gap_excess = {"horizontal": 0.0, "vertical": 0.0}
        gap_excess = {"horizontal": 0.0, "vertical": 0.0}
        if (not shared_axis_zero_gap) and axes_grid is not None and ((nrows_eff > 1) or (ncols_eff > 1)):
            panel_bboxes = _collect_panel_group_bboxes_px(fig, axes_grid)
            if panel_bboxes:
                gap_deficit = _compute_subplot_gap_deficit_px(
                    panel_bboxes=panel_bboxes,
                    nrows=nrows_eff,
                    ncols=ncols_eff,
                    min_hgap_px=min_hgap_px,
                    min_vgap_px=min_vgap_px,
                    tolerance_px=gap_tolerance_px,
                )
                raw_gap_excess = {
                    "horizontal": float(gap_deficit.get("horizontal_excess", 0.0)),
                    "vertical": float(gap_deficit.get("vertical_excess", 0.0)),
                }
                # 回缩只针对“超过当前目标 gap”的部分，避免把已修复的安全间距回缩到基线后再次重叠。
                target_margin_h = max(0.0, float(target_hgap_px) - float(min_hgap_px))
                target_margin_v = max(0.0, float(target_vgap_px) - float(min_vgap_px))
                gap_excess = {
                    "horizontal": max(0.0, float(raw_gap_excess["horizontal"]) - target_margin_h),
                    "vertical": max(0.0, float(raw_gap_excess["vertical"]) - target_margin_v),
                }
        has_gap_deficit = (
            float(gap_deficit["horizontal"]) > gap_tolerance_px
            or float(gap_deficit["vertical"]) > gap_tolerance_px
        )
        has_gap_excess = (
            float(gap_excess["horizontal"]) > gap_tolerance_px
            or float(gap_excess["vertical"]) > gap_tolerance_px
        )

        pass_report = {
            "pass": pass_idx,
            "overflow_px": {k: float(v) for k, v in overflow.items()},
            "overflow_ratio": {k: float(v) for k, v in overflow_ratio.items()},
            "gap_deficit_px": {
                "horizontal": float(gap_deficit["horizontal"]),
                "vertical": float(gap_deficit["vertical"]),
            },
            "gap_excess_base_px": {k: float(v) for k, v in raw_gap_excess.items()},
            "gap_excess_px": {k: float(v) for k, v in gap_excess.items()},
            "guard_intent": str(guard_intent),
            "preferred_canvas_scale": float(preferred_canvas_scale),
            "overflow_resolve_strategy": {
                "prefer_scale_x": prefer_scale_x,
                "prefer_scale_y": prefer_scale_y,
                "scale_trigger_ratio": float(overflow_scale_trigger_ratio),
            },
            "scale_policy": {
                "mode": "uniform_with_aspect_drift_guard",
                "max_total_scale": float(max_total_scale),
                "max_scale_step_per_pass": float(max_scale_step_per_pass),
                "base_aspect_ratio": float(base_aspect_ratio),
                "max_aspect_ratio_drift_frac": float(max_aspect_ratio_drift_frac),
            },
            "side_adjust_budget": {
                "max_total_per_side_frac": float(max_side_adjust_frac),
                "max_step_per_pass_frac": float(max_side_adjust_step_frac),
                "used_from_baseline": {k: float(v) for k, v in used_from_baseline.items()},
                "used_ratio_from_baseline": {k: float(v) for k, v in used_ratio_from_baseline.items()},
                "remaining": {k: float(v) for k, v in remaining_budget.items()},
                "baseline_budget_exhausted_x": bool(baseline_budget_exhausted_x),
                "baseline_budget_exhausted_y": bool(baseline_budget_exhausted_y),
            },
            "gap_step_policy": {
                "close_mode": "adaptive_gain",
                "trim_mode": "adaptive_gain",
            },
            "actions": [],
        }

        if (not has_overflow) and (not has_gap_deficit) and (not has_gap_excess):
            report["passes"].append(pass_report)
            break

        prev_state = _snapshot_adjust(adjust)
        if overflow["left"] > edge_tolerance_px:
            delta = min(
                max_side_adjust_step_frac,
                remaining_budget["left"],
                overflow["left"] / max(float(fig_w_px), 1.0) + 0.002,
            )
            if delta > 1e-9:
                adjust["left"] = float(adjust.get("left", 0.0)) + float(delta)
                pass_report["actions"].append("fix_overflow_left")
        if overflow["right"] > edge_tolerance_px:
            delta = min(
                max_side_adjust_step_frac,
                remaining_budget["right"],
                overflow["right"] / max(float(fig_w_px), 1.0) + 0.002,
            )
            if delta > 1e-9:
                adjust["right"] = float(adjust.get("right", 1.0)) - float(delta)
                pass_report["actions"].append("fix_overflow_right")
        if overflow["bottom"] > edge_tolerance_px:
            delta = min(
                max_side_adjust_step_frac,
                remaining_budget["bottom"],
                overflow["bottom"] / max(float(fig_h_px), 1.0) + 0.002,
            )
            if delta > 1e-9:
                adjust["bottom"] = float(adjust.get("bottom", 0.0)) + float(delta)
                pass_report["actions"].append("fix_overflow_bottom")
        if overflow["top"] > edge_tolerance_px:
            delta = min(
                max_side_adjust_step_frac,
                remaining_budget["top"],
                overflow["top"] / max(float(fig_h_px), 1.0) + 0.002,
            )
            if delta > 1e-9:
                adjust["top"] = float(adjust.get("top", 1.0)) - float(delta)
                pass_report["actions"].append("fix_overflow_top")

        clamp_adjust_spec(adjust, guard_spec)
        relock_guard_spec = dict(guard_spec)
        if float(gap_deficit["horizontal"]) > gap_tolerance_px:
            h_close_step = _gap_step_px(
                amount_px=float(gap_deficit["horizontal"]),
                pass_idx=pass_idx,
                mode="close",
            )
            target_hgap_px = max(float(min_hgap_px), float(target_hgap_px) + float(h_close_step))
            pass_report["actions"].append("close_hgap_deficit")
        elif float(gap_excess["horizontal"]) > gap_tolerance_px:
            h_trim_step = _gap_step_px(
                amount_px=float(gap_excess["horizontal"]),
                pass_idx=pass_idx,
                mode="trim",
            )
            target_hgap_px = max(float(min_hgap_px), float(target_hgap_px) - float(h_trim_step))
            pass_report["actions"].append("trim_hgap_excess")
        if float(gap_deficit["vertical"]) > gap_tolerance_px:
            v_close_step = _gap_step_px(
                amount_px=float(gap_deficit["vertical"]),
                pass_idx=pass_idx,
                mode="close",
            )
            target_vgap_px = max(float(min_vgap_px), float(target_vgap_px) + float(v_close_step))
            pass_report["actions"].append("close_vgap_deficit")
        elif float(gap_excess["vertical"]) > gap_tolerance_px:
            v_trim_step = _gap_step_px(
                amount_px=float(gap_excess["vertical"]),
                pass_idx=pass_idx,
                mode="trim",
            )
            target_vgap_px = max(float(min_vgap_px), float(target_vgap_px) - float(v_trim_step))
            pass_report["actions"].append("trim_vgap_excess")
        relock_guard_spec["min_subplot_gap_px"] = float(target_hgap_px)
        relock_guard_spec["min_subplot_vgap_px"] = float(target_vgap_px)
        _relock_spacing_to_font_basis(
            adjust,
            guard_spec=relock_guard_spec,
            fig_w_px=float(fig_w_px),
            fig_h_px=float(fig_h_px),
            nrows=nrows_eff,
            ncols=ncols_eff,
        )
        if shared_axis_zero_gap:
            adjust["wspace"] = 0.0
            adjust["hspace"] = 0.0
        next_state = _snapshot_adjust(adjust)
        adjust_changed = not np.allclose(prev_state, next_state, atol=1e-6)
        if adjust_changed:
            fig.subplots_adjust(**adjust)
            report["applied"] = True

        if (has_overflow or has_gap_deficit) and (
            (not adjust_changed)
            or force_scale_due_to_baseline_budget
            or (has_overflow and (prefer_scale_x or prefer_scale_y))
        ):
            # 当“相对初始 baseline 预算”耗尽时，直接触发放大，不再继续压缩主图比例。
            grow_w_px = overflow["left"] + overflow["right"] + max(0.0, float(gap_deficit["horizontal"]))
            grow_h_px = overflow["bottom"] + overflow["top"] + max(0.0, float(gap_deficit["vertical"]))
            w_growth_frac = max(0.0, grow_w_px / max(float(fig_w_px), 1.0))
            h_growth_frac = max(0.0, grow_h_px / max(float(fig_h_px), 1.0))
            raw_growth_frac = max(float(w_growth_frac), float(h_growth_frac))
            cur_w_in, cur_h_in = fig.get_size_inches()
            w_cap_in = float(base_w_in) * float(max_total_scale)
            h_cap_in = float(base_h_in) * float(max_total_scale)
            cap_factor_w = float(w_cap_in) / max(float(cur_w_in), 1e-9)
            cap_factor_h = float(h_cap_in) / max(float(cur_h_in), 1e-9)
            cap_factor = min(float(cap_factor_w), float(cap_factor_h))
            step_factor = 1.0 + float(max_scale_step_per_pass)
            target_factor = min(1.0 + float(raw_growth_frac), float(step_factor), float(cap_factor))

            target_w_in = float(cur_w_in) * float(target_factor)
            target_h_in = float(cur_h_in) * float(target_factor)

            # 比例偏移守卫：若已超过允许偏移，优先扩展短边纠偏，且不压缩长边。
            target_aspect = float(target_w_in) / max(float(target_h_in), 1e-9)
            if target_aspect > float(aspect_ratio_max):
                desired_h = float(target_w_in) / max(float(aspect_ratio_max), 1e-9)
                target_h_in = min(float(h_cap_in), max(float(target_h_in), float(desired_h)))
            elif target_aspect < float(aspect_ratio_min):
                desired_w = float(target_h_in) * float(aspect_ratio_min)
                target_w_in = min(float(w_cap_in), max(float(target_w_in), float(desired_w)))

            final_aspect = float(target_w_in) / max(float(target_h_in), 1e-9)
            drift_frac = abs(float(final_aspect) - float(base_aspect_ratio)) / max(float(base_aspect_ratio), 1e-9)
            pass_report["scale_policy"]["raw_growth_frac"] = float(raw_growth_frac)
            pass_report["scale_policy"]["target_factor"] = float(target_factor)
            pass_report["scale_policy"]["final_aspect_ratio"] = float(final_aspect)
            pass_report["scale_policy"]["final_aspect_drift_frac"] = float(drift_frac)
            pass_report["scale_policy"]["forced_by_baseline_budget"] = bool(force_scale_due_to_baseline_budget)

            grows_w = float(target_w_in) > float(cur_w_in) + 1e-6
            grows_h = float(target_h_in) > float(cur_h_in) + 1e-6
            can_scale_more = bool(grows_w or grows_h)
            if can_scale_more:
                fig.set_size_inches(float(target_w_in), float(target_h_in), forward=True)
                scale_guard_spec = dict(guard_spec)
                scale_guard_spec["min_subplot_gap_px"] = float(target_hgap_px)
                scale_guard_spec["min_subplot_vgap_px"] = float(target_vgap_px)
                _relock_spacing_to_font_basis(
                    adjust,
                    guard_spec=scale_guard_spec,
                    fig_w_px=float(target_w_in) * float(fig.get_dpi()),
                    fig_h_px=float(target_h_in) * float(fig.get_dpi()),
                    nrows=nrows_eff,
                    ncols=ncols_eff,
                )
                if shared_axis_zero_gap:
                    adjust["wspace"] = 0.0
                    adjust["hspace"] = 0.0
                fig.subplots_adjust(**adjust)
                report["applied"] = True
                if np.isclose(float(target_w_in) / max(float(cur_w_in), 1e-9), float(target_h_in) / max(float(cur_h_in), 1e-9), atol=1e-6):
                    pass_report["actions"].append("scale_canvas_uniform")
                else:
                    pass_report["actions"].append("scale_canvas_aspect_corrective")
                report["scale_triggered"] = True
                report["passes"].append(pass_report)
                continue

        if adjust_changed:
            report["passes"].append(pass_report)
            continue

        report["passes"].append(pass_report)
        break

    # ── 终态验证：只读 draw+测量，不做调整，记录最终残余溢出供下游诊断 ──
    try:
        fig.canvas.draw()
        _final_bbox = _collect_figure_bbox_px(fig)
        if _final_bbox is not None:
            _final_fw, _final_fh = _renderer_size_px(fig)
            _final_overflow = _compute_overflow_px(_final_bbox, _final_fw, _final_fh, overflow_pad_px)
            report["final_overflow_px"] = {k: float(v) for k, v in _final_overflow.items()}
            report["final_overflow_resolved"] = bool(max(_final_overflow.values()) <= edge_tolerance_px)
    except Exception:
        pass

    report["final_adjust"] = {
        "left": float(adjust.get("left", 0.0)),
        "right": float(adjust.get("right", 1.0)),
        "top": float(adjust.get("top", 1.0)),
        "bottom": float(adjust.get("bottom", 0.0)),
        "wspace": float(adjust.get("wspace", 0.0)),
        "hspace": float(adjust.get("hspace", 0.0)),
    }
    final_w_in = float(fig.get_size_inches()[0])
    final_h_in = float(fig.get_size_inches()[1])
    report["final_adjust_delta_from_baseline"] = {
        "left": float(report["final_adjust"]["left"]) - float(baseline_adjust["left"]),
        "right": float(report["final_adjust"]["right"]) - float(baseline_adjust["right"]),
        "top": float(report["final_adjust"]["top"]) - float(baseline_adjust["top"]),
        "bottom": float(report["final_adjust"]["bottom"]) - float(baseline_adjust["bottom"]),
    }
    report["final_size_in"] = [float(final_w_in), float(final_h_in)]
    report["final_scale_from_baseline"] = {
        "x": float(final_w_in) / max(float(base_w_in), 1e-9),
        "y": float(final_h_in) / max(float(base_h_in), 1e-9),
    }
    return report
