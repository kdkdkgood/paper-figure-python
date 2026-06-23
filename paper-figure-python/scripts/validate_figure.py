#!/usr/bin/env python3
"""科研图技术规范检查器。"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # noqa: BLE001
    Image = None

from params.defaults.l1_profile_defaults import PROFILE_DPI
from params.defaults.l3_layout_defaults import LAYOUT_SPEC_DEFAULTS


PROFILE_RULES: dict[str, dict[str, Any]] = {
    "thesis-journal": {
        "allowed_ext": {".png"},
        "dpi": dict(PROFILE_DPI["thesis-journal"]),
        "max_mb": None,
        "min_width_px": 1200,
    },
    "general": {
        "allowed_ext": {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg"},
        "dpi": dict(PROFILE_DPI["general"]),
        "max_mb": None,
        "min_width_px": None,
    },
    "elsevier": {
        "allowed_ext": {".tif", ".tiff", ".jpg", ".jpeg", ".png", ".eps", ".pdf"},
        "dpi": dict(PROFILE_DPI["elsevier"]),
        "max_mb": None,
        "min_width_px": None,
    },
    "ieee": {
        "allowed_ext": {".ps", ".eps", ".pdf", ".png", ".tif", ".tiff"},
        "dpi": dict(PROFILE_DPI["ieee"]),
        "max_mb": None,
        "min_width_px": 1050,
    },
    "plos": {
        "allowed_ext": {".tif", ".tiff", ".png", ".eps"},
        "dpi": dict(PROFILE_DPI["plos"]),
        "max_mb": 10.0,
        "min_width_px": 789,
    },
}

def _build_layout_rules() -> dict[str, dict[str, float]]:
    rules: dict[str, dict[str, float]] = {}
    for layout_name, spec in LAYOUT_SPEC_DEFAULTS.items():
        tolerance = 0.10 if layout_name in {"single", "double"} else 0.12
        rules[layout_name] = {
            "aspect_ratio": float(spec["aspect_ratio"]),
            "aspect_tolerance": tolerance,
        }
    return rules


LAYOUT_RULES = _build_layout_rules()


RASTER_EXT = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
# PNG 等格式常出现 999.998 这类舍入值，使用小容差避免误判。
DPI_EPSILON = 0.01


def check_file_size(path: Path, max_mb: float | None) -> tuple[bool, str]:
    size_mb = path.stat().st_size / (1024 * 1024)
    if max_mb is None:
        return True, f"文件大小 {size_mb:.2f} MB（未设置上限）"
    if size_mb <= max_mb:
        return True, f"文件大小 {size_mb:.2f} MB（<= {max_mb:.2f} MB）"
    return False, f"文件大小 {size_mb:.2f} MB（超过 {max_mb:.2f} MB）"


def read_dpi(image: Image.Image) -> float | None:
    dpi = image.info.get("dpi")
    if not dpi:
        return None
    if isinstance(dpi, tuple) and len(dpi) >= 2:
        return float(min(dpi[0], dpi[1]))
    if isinstance(dpi, (int, float)):
        return float(dpi)
    return None


def run_checks(
    path: Path,
    profile: str,
    art_type: str,
    layout: str,
    crop_enabled: bool,
) -> int:
    rules = PROFILE_RULES[profile]
    failures = 0

    ext = path.suffix.lower()
    if ext in rules["allowed_ext"]:
        print(f"[PASS] 格式 {ext} 被 {profile} 接受")
    else:
        failures += 1
        print(f"[FAIL] 格式 {ext} 不在 {profile} 允许列表内")

    ok_size, size_msg = check_file_size(path, rules["max_mb"])
    if ok_size:
        print(f"[PASS] {size_msg}")
    else:
        failures += 1
        print(f"[FAIL] {size_msg}")

    if ext in RASTER_EXT:
        if Image is None:
            failures += 1
            print("[FAIL] 当前环境缺少 Pillow（PIL），无法读取栅格图 DPI 与像素尺寸")
            print("[INFO] 请安装 Pillow 后重试：python -m pip install Pillow")
            return failures
        with Image.open(path) as img:
            width, height = img.size
            dpi = read_dpi(img)

        print(f"[INFO] 像素尺寸: {width} x {height}")
        if dpi is None:
            print("[WARN] 未读取到 DPI 元数据，请手动确认导出参数")
        else:
            required_dpi = rules["dpi"][art_type]
            if dpi + DPI_EPSILON >= required_dpi:
                print(f"[PASS] DPI {dpi:.1f} >= {required_dpi}")
            else:
                failures += 1
                print(f"[FAIL] DPI {dpi:.1f} < {required_dpi}")

        min_width_px = rules["min_width_px"]
        if min_width_px is not None:
            if width >= min_width_px:
                print(f"[PASS] 宽度 {width}px >= {min_width_px}px")
            else:
                failures += 1
                print(f"[FAIL] 宽度 {width}px < {min_width_px}px")

        if crop_enabled:
            print(
                "[INFO] 图幅比例检查已跳过：当前启用 auto-crop，"
                "裁边后内容像素比例不再严格等于布局比例。"
            )
        else:
            layout_rule = LAYOUT_RULES[layout]
            actual_ratio = width / height
            target_ratio = layout_rule["aspect_ratio"]
            tolerance = layout_rule["aspect_tolerance"]
            if abs(actual_ratio - target_ratio) <= tolerance:
                print(
                    f"[PASS] 图幅比例 {actual_ratio:.2f} 接近 {target_ratio:.2f} "
                    f"(±{tolerance:.2f})"
                )
            else:
                failures += 1
                print(
                    f"[FAIL] 图幅比例 {actual_ratio:.2f} 偏离目标 {target_ratio:.2f} "
                    f"(允许 ±{tolerance:.2f})"
                )
    else:
        print("[INFO] 当前文件为矢量格式，DPI/像素检查跳过")

    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查科研图是否满足投稿技术规格。")
    parser.add_argument("figure", help="图像文件路径")
    parser.add_argument(
        "--profile",
        default="thesis-journal",
        choices=sorted(PROFILE_RULES.keys()),
        help="规范 profile",
    )
    parser.add_argument(
        "--art-type",
        default="photo",
        choices=["photo", "line", "combo"],
        help="图像类型：photo/line/combo",
    )
    parser.add_argument(
        "--layout",
        default="single",
        choices=sorted(LAYOUT_RULES.keys()),
        help="图幅布局规格",
    )
    parser.add_argument(
        "--crop-enabled",
        default="0",
        choices=["0", "1"],
        help="可选：是否启用 auto-crop（1=启用，0=关闭）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.figure).resolve()
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    failures = run_checks(
        path=path,
        profile=args.profile,
        art_type=args.art_type,
        layout=args.layout,
        crop_enabled=(args.crop_enabled == "1"),
    )
    if failures == 0:
        print("[OK] 全部检查通过")
        raise SystemExit(0)

    print(f"[ERROR] 检查失败项: {failures}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
