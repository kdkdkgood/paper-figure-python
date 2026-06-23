"""Thin runtime: style, layout, hooks, guard, save.

This runtime intentionally does not implement chart types. AI code in
pre_draw/post_draw owns the scientific drawing logic.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

if "MPLCONFIGDIR" not in os.environ:
    _MPLCONFIG_DIR = Path(os.environ.get("PF_MPLCONFIGDIR", "~/.cache/paper-figure-python/mplconfig")).expanduser()
    try:
        _MPLCONFIG_DIR.mkdir(parents=True, exist_ok=True)
        test_path = _MPLCONFIG_DIR / ".write-test"
        test_path.write_text("", encoding="utf-8")
        test_path.unlink(missing_ok=True)
    except Exception:
        _MPLCONFIG_DIR = Path(tempfile.gettempdir()) / "paper-figure-python-mplconfig"
        _MPLCONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(_MPLCONFIG_DIR)

import matplotlib as mpl

mpl.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler

from palette_registry import resolve_palette

from .context import FigureContext, Hook


_ACTIVE_CONTEXT: FigureContext | None = None
_HELPERS_LOADED = False


def _load_cropper() -> None:
    from jobgen_template import render_cropper_module

    exec(compile(render_cropper_module(), "<runtime.cropper>", "exec"), globals())


def _load_layout_guard() -> None:
    from jobgen_template import render_layout_guard_module

    exec(compile(render_layout_guard_module(), "<runtime.layout_guard>", "exec"), globals())


def _ensure_helpers_loaded() -> None:
    global _HELPERS_LOADED
    if _HELPERS_LOADED:
        return
    _load_cropper()
    _load_layout_guard()
    _HELPERS_LOADED = True


def _resolve_palette(cfg: dict[str, Any]) -> list[str]:
    return resolve_palette(cfg.get("color_spec", {}))


def _apply_style(cfg: dict[str, Any]) -> None:
    style = cfg["style_spec"]
    font_name = style["font_family"]
    font_name_lower = str(font_name).lower()
    use_sans = any(token in font_name_lower for token in ("arial", "helvetica", "sans"))
    font_family = "sans-serif" if use_sans else "serif"
    font_serif = ["Times New Roman", "Times", "DejaVu Serif"]
    font_sans = ["Arial", "Helvetica", "DejaVu Sans"]
    palette = _resolve_palette(cfg)

    if cfg.get("library") == "seaborn":
        try:
            import seaborn as sns
        except Exception:
            sns = None
        if sns is not None:
            sns.set_theme(style="ticks")

    mpl.rcParams.update(
        {
            "font.family": font_family,
            "font.serif": [font_name, *font_serif],
            "font.sans-serif": [font_name, *font_sans],
            "font.size": float(style["axis_label_size"]),
            "axes.labelsize": float(style["axis_label_size"]),
            "xtick.labelsize": float(style["tick_label_size"]),
            "ytick.labelsize": float(style["tick_label_size"]),
            "legend.fontsize": float(style["legend_size"]),
            "legend.title_fontsize": float(style["legend_title_size"]),
            "axes.linewidth": float(style["axes_linewidth"]),
            "lines.linewidth": float(style["line_width"]),
            "lines.markersize": float(style["marker_size"]),
            "axes.grid": bool(style["axes_grid"]),
            "grid.alpha": float(style["grid_alpha"]),
            "grid.linewidth": float(style["grid_linewidth"]),
            "mathtext.fontset": "stix",
            "mathtext.rm": font_name,
            "mathtext.it": f"{font_name}:italic",
            "text.usetex": False,
            "axes.prop_cycle": cycler(color=palette),
            "savefig.bbox": None,
            "savefig.pad_inches": 0.0,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def _figure_size(cfg: dict[str, Any]) -> tuple[float, float]:
    layout_spec = cfg["layout_spec"]
    width_in = float(layout_spec["width_mm"]) / 25.4
    height_in = width_in / float(layout_spec["aspect_ratio"])
    return width_in, height_in


def _apply_axis_details(ax: plt.Axes, cfg: dict[str, Any]) -> None:
    axis_spec = cfg.get("axis_spec", {})
    style = cfg.get("style_spec", {})
    tick_direction = str(axis_spec.get("tick_direction", "out"))
    tick_length = float(axis_spec.get("tick_length", 4.0))
    tick_width = float(axis_spec.get("tick_width", 0.8))
    show_top_spine = bool(axis_spec.get("show_top_spine", True))
    show_right_spine = bool(axis_spec.get("show_right_spine", True))
    minor_ticks = bool(axis_spec.get("minor_ticks", False))

    ax.tick_params(axis="both", direction=tick_direction, length=tick_length, width=tick_width)
    if "tick_label_size" in style:
        ax.tick_params(labelsize=float(style["tick_label_size"]))
    if minor_ticks:
        ax.minorticks_on()
        ax.tick_params(
            axis="both",
            which="minor",
            direction=tick_direction,
            length=max(1.0, tick_length * 0.6),
            width=max(0.4, tick_width * 0.8),
        )
    else:
        ax.minorticks_off()
    ax.spines["top"].set_visible(show_top_spine)
    ax.spines["right"].set_visible(show_right_spine)
    for spine in ax.spines.values():
        spine.set_linewidth(float(style.get("axes_linewidth", 0.8)))


def _save_and_report_figure(*, fig: plt.Figure, cfg: dict[str, Any], guard_report: dict[str, Any]) -> Path:
    out_dir = _ACTIVE_CONTEXT.job_dir if _ACTIVE_CONTEXT is not None else Path.cwd()
    raw_path = out_dir / "figure_raw.png"
    out_path = out_dir / "figure.png"
    crop_report_path = out_dir / "crop_report.json"

    fig.savefig(raw_path, dpi=int(cfg["dpi"]), pil_kwargs={"compress_level": 3, "optimize": False})
    plt.close(fig)

    crop_spec = cfg["crop_spec"]
    if bool(crop_spec["enabled"]):
        crop_info = autocrop_png(raw_path=raw_path, final_path=out_path, crop_spec=crop_spec)
    else:
        shutil.copy2(raw_path, out_path)
        if not bool(crop_spec["keep_raw"]):
            raw_path.unlink(missing_ok=True)
        crop_info = {"applied": False, "reason": "crop-disabled"}

    crop_report = {
        "layout_guard": guard_report,
        "crop_spec": {
            "enabled": bool(crop_spec.get("enabled", False)),
            "mode": str(crop_spec.get("mode", "auto")),
            "padding_px": int(crop_spec.get("padding_px", 0)),
            "max_trim_ratio_per_axis": float(crop_spec.get("max_trim_ratio_per_axis", 0.0)),
        },
        "crop_info": crop_info if isinstance(crop_info, dict) else {"applied": False, "reason": "invalid-crop-info"},
    }
    crop_report_path.write_text(json.dumps(crop_report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


_PANEL_LABEL_GID = "pf_user_panel_label"

_PANEL_LABEL_CORNERS = {
    "top_left": (0.03, 0.96, "left", "top"),
    "top_right": (0.97, 0.96, "right", "top"),
    "bottom_left": (0.03, 0.04, "left", "bottom"),
    "bottom_right": (0.97, 0.04, "right", "bottom"),
}


def _index_to_letter(index: int) -> str:
    """0->a, 1->b, ... 25->z, 26->aa（Excel 式进位，应对超长面板序列）。"""

    n = int(index)
    out = ""
    while True:
        out = chr(ord("a") + (n % 26)) + out
        n = n // 26 - 1
        if n < 0:
            break
    return out


def _format_panel_label(index: int, label_style: str) -> str:
    letter = _index_to_letter(index)
    if label_style == "upper":
        return letter.upper()
    if label_style == "lower":
        return letter
    if label_style == "lower_paren":
        return f"({letter})"
    return f"({letter})"  # lower_paren 默认


def _resolve_panel_label_texts(cfg: dict[str, Any], ctx: "FigureContext", n_panels: int) -> list[str | None]:
    """决定每个面板的编号文本：ctx.panel_labels > spec.labels > 自动生成。"""

    spec = cfg.get("panel_label_spec", {}) or {}
    label_style = str(spec.get("label_style", "lower_paren"))
    override = ctx.panel_labels
    if override is None:
        override = spec.get("labels")
    if override is not None:
        texts: list[str | None] = []
        for i in range(n_panels):
            val = override[i] if i < len(override) else None
            texts.append(None if val is None or str(val) == "" else str(val))
        return texts
    return [_format_panel_label(i, label_style) for i in range(n_panels)]


def _measure_bottom_drop_pt(ax: plt.Axes, fig: plt.Figure) -> float:
    """测量 ax 下脊柱到 tight 边界（含刻度标签 + xlabel）的距离，单位 pt。

    用于把外部编号稳定地摆在 xlabel 下方：该距离由字号决定、与画布缩放无关。
    """

    try:
        renderer = fig.canvas.get_renderer()
        spine_bbox = ax.get_window_extent(renderer)
        tight_bbox = ax.get_tightbbox(renderer)
    except Exception:
        return 0.0
    if tight_bbox is None:
        return 0.0
    drop_px = max(0.0, float(spine_bbox.y0) - float(tight_bbox.y0))
    return drop_px * 72.0 / float(fig.dpi)


def _place_panel_labels(fig: plt.Figure, cfg: dict[str, Any], ctx: "FigureContext", axes_grid) -> None:
    """引擎托管的字图编号摆放：读 panel_label_spec，inside 角标 / outside 贴 xlabel 下方。

    在 layout guard 之前调用：inside 用 transAxes（缩放不变），outside 用 point 偏移锚在
    轴下方（被 ax.get_tightbbox 计入，guard 自动预留底部空间、绝不裁切）。
    """

    spec = cfg.get("panel_label_spec", {}) or {}
    mode = str(spec.get("mode", "auto"))
    if mode == "off":
        return

    flat = list(axes_grid.ravel())
    visible = [ax for ax in flat if ax.get_visible()]
    n_panels = len(visible)

    explicit = ctx.panel_labels is not None or spec.get("labels") is not None
    # 默认规则：单图不标号；>=2 图自动标号。用户显式给 labels 时尊重其意图。
    if n_panels < 2 and not explicit:
        return

    # 若 AI 已手动 add_panel_label，则不重复自动摆放（向后兼容逃生口）。
    for ax in visible:
        for child in ax.texts:
            if child.get_gid() == _PANEL_LABEL_GID:
                return

    texts = _resolve_panel_label_texts(cfg, ctx, len(flat))
    style = cfg.get("style_spec", {}) or {}
    fontsize = float(style.get("axis_label_size", 9.0))
    nrows, ncols = axes_grid.shape
    effective_mode = _resolve_effective_label_mode(cfg, int(nrows), int(ncols))
    corner = str(spec.get("corner", "top_left"))
    cx, cy, ha, va = _PANEL_LABEL_CORNERS.get(corner, _PANEL_LABEL_CORNERS["top_left"])
    inside_x = spec.get("inside_x")
    inside_y = spec.get("inside_y")
    if inside_x is not None:
        cx = float(inside_x)
    if inside_y is not None:
        cy = float(inside_y)
    outside_x = float(spec.get("outside_x", 0.5) if spec.get("outside_x") is not None else 0.5)
    gap_pt = max(0.0, float(spec.get("xlabel_gap_pt", 2.0) or 0.0))

    if effective_mode == "outside":
        fig.canvas.draw()  # 让 tick/xlabel 进入最终布局，便于测量下沉量

    for ax in flat:
        if not ax.get_visible():
            continue
        idx = flat.index(ax)
        label = texts[idx] if idx < len(texts) else None
        if not label:
            continue
        if effective_mode == "outside":
            drop_pt = _measure_bottom_drop_pt(ax, fig) + gap_pt
            txt = ax.annotate(
                label,
                xy=(outside_x, 0.0),
                xycoords="axes fraction",
                xytext=(0.0, -drop_pt),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=fontsize,
                fontweight="bold",
                color="#111111",
                annotation_clip=False,
            )
        else:
            txt = ax.text(
                cx,
                cy,
                label,
                transform=ax.transAxes,
                ha=ha,
                va=va,
                fontsize=fontsize,
                fontweight="bold",
                color="#111111",
            )
        try:
            txt.set_gid(_PANEL_LABEL_GID)
        except Exception:
            pass


def _resolve_effective_label_mode(cfg: dict[str, Any], nrows: int, ncols: int) -> str:
    """把 panel_label_spec.mode=auto 依 axis_mode/布局形状解析成 inside/outside。

    沿用 panel-axis-rules.md：shared_axis ⇒ inside 角标；independent ⇒ outside（x 轴
    下方）；单列且 nrows>=3 的紧凑纵排 ⇒ 回退 inside，避免与 xlabel 干涉。
    """

    spec = cfg.get("panel_label_spec", {}) or {}
    mode = str(spec.get("mode", "auto"))
    if mode != "auto":
        return mode
    axis_mode = str(cfg.get("effective_axis_mode", cfg.get("axis_mode", "independent"))).lower()
    if axis_mode == "shared_axis":
        return "inside"
    if int(ncols) == 1 and int(nrows) >= 3:
        return "inside"
    return "outside"


def _resolve_share_axes(cfg: dict[str, Any]) -> bool:
    """判定是否启用 matplotlib 原生共享轴。

    单一事实源：pipeline 派生层写入的 ``runtime_derived.share_axes``。
    create/patch 两条流程都重跑派生层，该标志必然存在且权威。
    """

    runtime_derived = cfg.get("runtime_derived", {})
    if not isinstance(runtime_derived, dict):
        return False
    return bool(runtime_derived.get("share_axes", False))


def _build_blank_figure(cfg: dict[str, Any]) -> tuple[plt.Figure, np.ndarray, dict[str, float]]:
    nrows = int(cfg["layout_spec"]["nrows"])
    ncols = int(cfg["layout_spec"]["ncols"])
    width, height = _figure_size(cfg)

    # ── 根据 runtime_derived 决定是否走 matplotlib 原生共享轴 ──
    # 规则：单面板不共享；仅相应方向存在多面板时才共享该方向。
    share_axes = _resolve_share_axes(cfg)
    sharex = share_axes and nrows > 1
    sharey = share_axes and ncols > 1
    # ─────────────────────────────────────────────────────────

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(width, height),
        squeeze=False,
        constrained_layout=False,
        sharex=sharex,
        sharey=sharey,
    )
    axes_grid = np.array(axes, dtype=object).reshape(nrows, ncols)
    adjust = dict(cfg["adjust_spec"])
    adjust["wspace"] = 0.0 if ncols <= 1 else float(adjust.get("wspace", 0.0))
    adjust["hspace"] = 0.0 if nrows <= 1 else float(adjust.get("hspace", 0.0))
    fig.subplots_adjust(**adjust)
    return fig, axes_grid, adjust


def run_figure(
    cfg: dict[str, Any],
    *,
    pre_draw: Hook | None = None,
    post_draw: Hook | None = None,
    job_dir: str | Path | None = None,
) -> Path:
    """Run a custom figure job from a thin plot file."""

    _ensure_helpers_loaded()
    resolved_job_dir = Path(job_dir).resolve() if job_dir is not None else Path.cwd().resolve()
    resolved_job_dir.mkdir(parents=True, exist_ok=True)

    _apply_style(cfg)
    fig, axes_grid, adjust = _build_blank_figure(cfg)
    nrows, ncols = axes_grid.shape

    global _ACTIVE_CONTEXT
    previous_context = _ACTIVE_CONTEXT
    context = FigureContext(
        cfg=cfg,
        job_dir=resolved_job_dir,
        pre_draw=pre_draw,
        post_draw=post_draw,
        fig=fig,
        axes_grid=axes_grid,
        nrows=int(nrows),
        ncols=int(ncols),
    )
    _ACTIVE_CONTEXT = context
    try:
        if pre_draw is not None:
            pre_draw(context)
        if post_draw is not None:
            post_draw(context)

        for ax in axes_grid.ravel():
            _apply_axis_details(ax, cfg)

        _place_panel_labels(fig, cfg, context, axes_grid)

        guard_report = {
            "applied": False,
            "passes": [],
            "final_adjust": {k: float(adjust.get(k, 0.0)) for k in ("left", "right", "top", "bottom", "wspace", "hspace")},
            "final_size_in": [float(fig.get_size_inches()[0]), float(fig.get_size_inches()[1])],
        }
        if bool(cfg.get("layout_guard_spec", {}).get("enabled", True)):
            guard_report = apply_fallback_layout_guard(
                fig,
                cfg,
                adjust,
                axes_grid=axes_grid,
                nrows=int(nrows),
                ncols=int(ncols),
                axis_mode=str(cfg.get("effective_axis_mode", cfg.get("axis_mode", "independent"))),
            )
            cfg["adjust_spec"].update(guard_report.get("final_adjust", {}))

        out = _save_and_report_figure(fig=fig, cfg=cfg, guard_report=guard_report)
        context.report["figure"] = str(out)
        context.report["layout_guard"] = guard_report
        integrity = _check_runtime_integrity()
        _write_run_report(resolved_job_dir, cfg, guard_report, out, integrity)
        return out
    finally:
        _ACTIVE_CONTEXT = previous_context


# --- AI_EDIT_ZONE 区段抽取与 run report 自记录 ----------------------------

_EDIT_ZONE_RE = re.compile(
    r"#\s*---\s*AI_EDIT_ZONE:(?P<name>\w+)\s+START\s*---\n(?P<body>.*?)\n\s*#\s*---\s*AI_EDIT_ZONE:(?P=name)\s+END\s*---",
    re.DOTALL,
)


def _extract_edit_zone_hash(plot_path: Path) -> str | None:
    """提取 plot.py 三个 AI_EDIT_ZONE 区段内容并算 SHA256（前 12 位）。

    返回 None 表示无法读取或未命中任何区段——suggest 端据此跳过代码 diff，
    绝不因抽取失败而误判为"代码无演变"。
    """

    try:
        text = plot_path.read_text(encoding="utf-8")
    except OSError:
        return None
    zones = {m.group("name"): m.group("body") for m in _EDIT_ZONE_RE.finditer(text)}
    if not zones:
        return None
    # 按区段名排序拼接，保证哈希与区段书写顺序无关
    joined = "\n".join(f"<{name}>\n{zones[name]}" for name in sorted(zones))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]


def _run_report_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """与 create/patch report 严格同构的精简 config 白名单。

    必须只含这些键——否则 suggest 端 _flatten diff 会冒出大量假 delta。
    """

    return {
        "chart_type": cfg.get("chart_type"),
        "layout": cfg.get("layout"),
        "axis_mode": cfg.get("effective_axis_mode", cfg.get("axis_mode")),
        "library": cfg.get("library"),
        "style_profile": cfg.get("style_profile"),
        "seed": cfg.get("seed"),
        "dpi": cfg.get("dpi"),
        "runtime_derived": cfg.get("runtime_derived", {}),
        "template_mode": cfg.get("template_mode", "thin"),
    }


def _check_runtime_integrity() -> dict[str, Any]:
    """出图后自检共享底座是否被改动。

    drift 时向 stderr 打印醒目警告（不阻断），并返回结果供 run report 留痕。
    基线缺失或自检模块异常时静默返回 no_baseline，绝不影响出图。
    """

    try:
        import sys

        from runtime import integrity

        result = integrity.check_integrity()
        if result.get("status") == "drift":
            sys.stderr.write(integrity.format_warning(result) + "\n")
        return result
    except Exception:
        return {"status": "no_baseline", "drift": {}}


def _write_run_report(
    job_dir: Path,
    cfg: dict[str, Any],
    guard_report: dict[str, Any],
    figure_path: Path,
    integrity: dict[str, Any] | None = None,
) -> None:
    """每次 ``python plot.py`` 成功出图后写一条 mode="run" 报告。

    让 Edit→Run 迭代路径也被经验系统捕获。旁路降级：任何异常都吞掉，
    绝不影响已完成的出图。
    """

    try:
        from orchestrator.core import write_orchestrator_report

        payload = {
            "schema_version": "2.1",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "mode": "run",
            "config": _run_report_config(cfg),
            "ai_edit_zone_hash": _extract_edit_zone_hash(job_dir / "plot.py"),
            "runtime_integrity": integrity or {"status": "no_baseline", "drift": {}},
            "layout_guard": {
                "applied": bool(guard_report.get("applied", False)),
                "passes": len(guard_report.get("passes", []) or []),
            },
            "job": {
                "dir": str(job_dir),
                "figure": str(figure_path),
                "template_mode": "thin",
            },
            "render_validation": {"enabled": False, "passed": True},
            "metrics": {"render_count": 1},
        }
        write_orchestrator_report(job_dir=job_dir, payload=payload)
    except Exception:
        pass  # 旁路降级，绝不影响出图


__all__ = ["FigureContext", "run_figure"]
