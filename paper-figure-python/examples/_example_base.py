#!/usr/bin/env python3
"""Example gallery 公共工具。

- 把 ``scripts/`` 加入 ``sys.path``（相对定位，可移植，不写死绝对路径）。
- ``demo_config`` 走真实参数编译链产出完整可运行的 thin CONFIG。
- 每个范例 ``python examples/<name>.py`` 直接运行，输出写到 ``examples/_output/<name>/``。

注意：范例中的数据均为**合成 DEMO 数据**（``np.random.default_rng`` 固定种子），仅用于演示
绘图模式，不是真实任务数据；真实任务请按 SKILL 流程从用户数据文件读取。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from params import build_compiled_config  # noqa: E402


def demo_config(
    *,
    layout: str = "single",
    axis_mode: str = "independent",
    style_profile: str = "elsevier",
    overrides: dict | None = None,
    **route,
) -> dict:
    """用真实编译链构建一个完整 flat_config（可直接传给 run_figure）。"""

    args = argparse.Namespace(
        task="example",
        chart_type="custom",
        layout=layout,
        axis_mode=axis_mode,
        library="matplotlib",
        style_profile=style_profile,
        style_stack="",
        multi_order="line",
        seed=42,
        art_type="combo",
        dpi=0,
    )
    for key, value in route.items():
        setattr(args, key, value)
    return build_compiled_config(args, overrides or {}).flat_config


def example_job_dir(example_file: str) -> Path:
    out = Path(__file__).resolve().parent / "_output" / Path(example_file).stem
    out.mkdir(parents=True, exist_ok=True)
    return out


__all__ = ["SCRIPTS_ROOT", "demo_config", "example_job_dir"]
