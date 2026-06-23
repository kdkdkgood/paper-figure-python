#!/usr/bin/env python3
"""create_figure 的脚本模板渲染。"""

from __future__ import annotations

import json
from pathlib import Path

from jobgen_schema import TEMPLATE_VERSION

ROUTE_SCRIPT_KEYS = (
    "task",
    "chart_type",
    "layout",
    "axis_mode",
    "requested_axis_mode",
    "effective_axis_mode",
    "library",
    "style_profile",
    "style_stack",
    "multi_order",
    "seed",
    "art_type",
    "dpi",
)

CORE_SCRIPT_KEYS = (
    "layout_spec",
    "style_spec",
    "axis_spec",
    "legend_spec",
    "adjust_spec",
    "panel_label_spec",
    "crop_spec",
    "layout_guard_spec",
)

OPTIONAL_SCRIPT_KEYS = (
    "color_spec",
    "data_spec",
    "layout_runtime",
    "runtime_derived",
)


def _copy_present(config: dict, keys: tuple[str, ...]) -> dict:
    return {key: config[key] for key in keys if key in config}


def _build_script_config(config: dict) -> dict:
    slim: dict[str, object] = {}
    slim.update(_copy_present(config, ROUTE_SCRIPT_KEYS))
    slim.update(_copy_present(config, CORE_SCRIPT_KEYS))
    slim.update(_copy_present(config, OPTIONAL_SCRIPT_KEYS))
    return slim


def config_block(config: dict) -> str:
    cfg_json = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    return (
        "# --- CONFIG START ---\n"
        f"CONFIG = json.loads({cfg_json!r})\n"
        "# --- CONFIG END ---"
    )


def build_tag_line(config: dict) -> str:
    return (
        "# FIGURE_TAG: "
        f"chart_type={config['chart_type']};layout={config['layout']};"
        f"axis_mode={config['axis_mode']};library={config['library']};"
        f"style_profile={config['style_profile']}"
    )


def render_cropper_module() -> str:
    return """#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

try:
    from PIL import Image
except Exception:
    Image = None


def _build_content_mask(rgba: np.ndarray, crop_spec: dict) -> np.ndarray:
    mode = str(crop_spec["mode"]).lower()
    alpha_threshold = int(crop_spec["alpha_threshold"])
    white_threshold = int(crop_spec["white_threshold"])
    alpha = rgba[..., 3]
    rgb = rgba[..., :3]
    has_alpha = alpha > alpha_threshold
    not_white = np.any(rgb < white_threshold, axis=2)

    if mode == "alpha":
        return has_alpha
    if mode == "white":
        return has_alpha & not_white

    has_transparent_pixels = bool(np.any(alpha <= alpha_threshold))
    if has_transparent_pixels:
        return has_alpha
    return has_alpha & not_white


def _build_empty_crop_info(reason: str, *, raw_w: int | None = None, raw_h: int | None = None) -> dict:
    payload = {
        "applied": False,
        "reason": str(reason),
        "box": None,
        "input_size": [int(raw_w), int(raw_h)] if raw_w is not None and raw_h is not None else None,
        "output_size": [int(raw_w), int(raw_h)] if raw_w is not None and raw_h is not None else None,
        "trim_px": {"left": 0, "right": 0, "bottom": 0, "top": 0},
        "trim_ratio": {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0},
        "axis_trim_ratio": {"x": 0.0, "y": 0.0},
        "total_trim_ratio": 0.0,
    }
    return payload


def _build_trim_metrics(raw_w: int, raw_h: int, left: int, top: int, right: int, bottom: int) -> dict:
    trim_px = {
        "left": max(0, int(left)),
        "right": max(0, int(raw_w - 1 - right)),
        "bottom": max(0, int(raw_h - 1 - bottom)),
        "top": max(0, int(top)),
    }
    width = max(1, int(raw_w))
    height = max(1, int(raw_h))
    trim_ratio = {
        "left": float(trim_px["left"]) / float(width),
        "right": float(trim_px["right"]) / float(width),
        "bottom": float(trim_px["bottom"]) / float(height),
        "top": float(trim_px["top"]) / float(height),
    }
    axis_trim_ratio = {
        "x": float(min(1.0, trim_ratio["left"] + trim_ratio["right"])),
        "y": float(min(1.0, trim_ratio["bottom"] + trim_ratio["top"])),
    }
    keep_ratio = max(0.0, 1.0 - axis_trim_ratio["x"]) * max(0.0, 1.0 - axis_trim_ratio["y"])
    return {
        "trim_px": trim_px,
        "trim_ratio": trim_ratio,
        "axis_trim_ratio": axis_trim_ratio,
        "total_trim_ratio": float(max(0.0, min(1.0, 1.0 - keep_ratio))),
    }


def autocrop_png(raw_path: Path, final_path: Path, crop_spec: dict) -> dict:
    keep_raw = bool(crop_spec["keep_raw"])
    if Image is None:
        shutil.copy2(raw_path, final_path)
        if not keep_raw:
            raw_path.unlink(missing_ok=True)
        return _build_empty_crop_info("PIL not installed")

    with Image.open(raw_path) as img:
        rgba = np.array(img.convert("RGBA"))
        raw_h, raw_w = rgba.shape[0], rgba.shape[1]
        mask = _build_content_mask(rgba, crop_spec)
        rows = np.where(mask.any(axis=1))[0]
        cols = np.where(mask.any(axis=0))[0]
        if rows.size == 0 or cols.size == 0:
            shutil.copy2(raw_path, final_path)
            if not keep_raw:
                raw_path.unlink(missing_ok=True)
            return _build_empty_crop_info("empty-mask", raw_w=raw_w, raw_h=raw_h)

        pad = int(crop_spec["padding_px"])
        top = max(0, int(rows[0]) - pad)
        bottom = min(raw_h - 1, int(rows[-1]) + pad)
        left = max(0, int(cols[0]) - pad)
        right = min(raw_w - 1, int(cols[-1]) + pad)
        raw_trim_metrics = _build_trim_metrics(raw_w=raw_w, raw_h=raw_h, left=left, top=top, right=right, bottom=bottom)
        crop_w = int(right - left + 1)
        crop_h = int(bottom - top + 1)
        # 防止“过裁切”导致版面看起来被异常放大：按配置限制单轴最大裁切比例。
        max_trim_ratio = min(0.45, max(0.0, float(crop_spec.get("max_trim_ratio_per_axis", 0.12))))
        min_keep_w = int(round(raw_w * (1.0 - max_trim_ratio)))
        min_keep_h = int(round(raw_h * (1.0 - max_trim_ratio)))
        if crop_w < min_keep_w:
            need = min_keep_w - crop_w
            grow_l = need // 2
            grow_r = need - grow_l
            left = max(0, left - grow_l)
            right = min(raw_w - 1, right + grow_r)
            # 触边后再二次补偿，尽量达到最小保留宽度
            crop_w2 = int(right - left + 1)
            if crop_w2 < min_keep_w:
                short = min_keep_w - crop_w2
                if left == 0:
                    right = min(raw_w - 1, right + short)
                elif right == raw_w - 1:
                    left = max(0, left - short)
        if crop_h < min_keep_h:
            need = min_keep_h - crop_h
            grow_t = need // 2
            grow_b = need - grow_t
            top = max(0, top - grow_t)
            bottom = min(raw_h - 1, bottom + grow_b)
            crop_h2 = int(bottom - top + 1)
            if crop_h2 < min_keep_h:
                short = min_keep_h - crop_h2
                if top == 0:
                    bottom = min(raw_h - 1, bottom + short)
                elif bottom == raw_h - 1:
                    top = max(0, top - short)
        cropped = img.crop((left, top, right + 1, bottom + 1))
        save_kwargs = {"compress_level": 3, "optimize": False} if final_path.suffix.lower() == ".png" else {}
        dpi_value = img.info.get("dpi")
        if (
            isinstance(dpi_value, tuple)
            and len(dpi_value) >= 2
            and isinstance(dpi_value[0], (int, float))
            and isinstance(dpi_value[1], (int, float))
        ):
            save_kwargs["dpi"] = (float(dpi_value[0]), float(dpi_value[1]))
        cropped.save(final_path, **save_kwargs)

    if not keep_raw:
        raw_path.unlink(missing_ok=True)
    trim_metrics = _build_trim_metrics(raw_w=raw_w, raw_h=raw_h, left=left, top=top, right=right, bottom=bottom)
    cap_applied = bool(
        abs(float(raw_trim_metrics["axis_trim_ratio"]["x"]) - float(trim_metrics["axis_trim_ratio"]["x"])) > 1e-9
        or abs(float(raw_trim_metrics["axis_trim_ratio"]["y"]) - float(trim_metrics["axis_trim_ratio"]["y"])) > 1e-9
    )
    return {
        "applied": True,
        "box": [left, top, right, bottom],
        "input_size": [int(raw_w), int(raw_h)],
        "output_size": [int(right - left + 1), int(bottom - top + 1)],
        "cap_applied": cap_applied,
        "pre_cap_trim_px": raw_trim_metrics["trim_px"],
        "pre_cap_trim_ratio": raw_trim_metrics["trim_ratio"],
        "pre_cap_axis_trim_ratio": raw_trim_metrics["axis_trim_ratio"],
        "pre_cap_total_trim_ratio": raw_trim_metrics["total_trim_ratio"],
        **trim_metrics,
    }
"""


def render_layout_guard_module() -> str:
    header = """#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
"""
    guard_function_order = [
        "layout_guard_mm_to_inch",
        "layout_guard_figure_size",
        "clamp_adjust_spec",
        "_collect_figure_bbox_px",
        "_compute_overflow_px",
        "_collect_panel_group_bboxes_px",
        "_compute_subplot_gap_deficit_px",
        "apply_fallback_layout_guard",
    ]
    blocks: list[str] = [header.rstrip("\n")]
    for name in guard_function_order:
        blocks.append(_read_block_text(LAYOUT_GUARD_BLOCKS_ROOT / f"{name}.py").rstrip("\n"))
    rendered = "\n\n".join(blocks)
    if not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


LAYOUT_GUARD_BLOCKS_ROOT = Path(__file__).resolve().parent / "runtime" / "layout_guard_blocks"


def _read_block_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"缺少 block 文件: {path}")
    text = path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def render_thin_plot_script(config: dict, source_template: str) -> str:
    script_config = _build_script_config(config)
    scripts_root = str(Path(__file__).resolve().parent)
    return f'''#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

_JOB_DIR = Path(__file__).resolve().parent
_GENERATED_SCRIPTS_ROOT = Path({scripts_root!r})


def _locate_scripts_root() -> Path:
    """运行时定位含 runtime 包的 scripts 目录，支持跨机器/跨工具迁移。"""
    candidates = []
    env = os.environ.get("PAPER_FIGURE_SKILL_ROOT")
    if env:
        base = Path(env).expanduser()
        candidates += [base, base / "scripts"]
    candidates.append(_GENERATED_SCRIPTS_ROOT)
    for root in (Path.home() / ".claude" / "skills", Path.home() / ".kiro" / "skills"):
        candidates.append(root / "paper-figure-python" / "scripts")
    candidates += [parent / "scripts" for parent in _JOB_DIR.parents]
    for cand in candidates:
        if (cand / "runtime" / "__init__.py").is_file():
            return cand
    raise ModuleNotFoundError(
        "无法定位 paper-figure-python runtime；"
        "请设置环境变量 PAPER_FIGURE_SKILL_ROOT 指向 skill 根目录。"
    )


_SCRIPTS_ROOT = _locate_scripts_root()
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

from runtime import FigureContext, run_figure

{config_block(script_config)}
# TEMPLATE_VERSION: {TEMPLATE_VERSION}
{build_tag_line(config)}
# SOURCE_TEMPLATE: {source_template}
# TEMPLATE_MODE: thin

# --- AI_EDIT_ZONE:imports START ---
# --- AI_EDIT_ZONE:imports END ---


def pre_draw(ctx: FigureContext) -> None:
    # --- AI_EDIT_ZONE:pre_draw START ---
    # AI 在此自主完成数据读取、清洗、转换
    # 将就绪的 DataFrame 赋给 ctx.df_override（全局）或 ctx.panel_dfs[idx]（按面板）
    # ctx.style / ctx.layout / ctx.colors 是推荐参数，不限制数据处理方式
    # --- AI_EDIT_ZONE:pre_draw END ---
    return None


def post_draw(ctx: FigureContext) -> None:
    # --- AI_EDIT_ZONE:post_draw START ---
    # 可选：在绘图循环完成后、保存前注入逻辑；也可以 ctx.ax(0).cla() 后完全自定义重绘
    # 可访问 ctx.fig, ctx.axes_grid, ctx.ax(index), ctx.style, ctx.layout, ctx.colors, ctx.cfg
    # 布局由 runtime layout_guard 统一管控，无需手动调用布局 API
    # --- AI_EDIT_ZONE:post_draw END ---
    return None


def main() -> None:
    out = run_figure(CONFIG, pre_draw=pre_draw, post_draw=post_draw, job_dir=_JOB_DIR)
    print(f"[OK] figure: {{out}}")
    print(
        f"[INFO] task={{CONFIG['task']}}, chart_type={{CONFIG['chart_type']}}, layout={{CONFIG['layout']}}, "
        f"axis_mode={{CONFIG['axis_mode']}}, style_profile={{CONFIG['style_profile']}}, "
        f"dpi={{CONFIG['dpi']}}, seed={{CONFIG['seed']}}, library={{CONFIG['library']}}"
    )


if __name__ == "__main__":
    main()
'''


__all__ = [
    "build_tag_line",
    "render_layout_guard_module",
    "render_cropper_module",
    "render_thin_plot_script",
]
