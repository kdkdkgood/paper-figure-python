#!/usr/bin/env python3
"""CLI 参数定义与统一输出。"""

from __future__ import annotations

import argparse
import json
from typing import Any

from orchestrator.core import classify_generic_error
from orchestrator.runner import run_orchestrator


def parse_create_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new figure job.")
    parser.add_argument("--task", default="科研绘图任务")
    parser.add_argument("--job-name", default="")
    parser.add_argument("--chart-type", default="custom")
    parser.add_argument("--layout", default="")
    parser.add_argument("--style-profile", default="elsevier")
    parser.add_argument("--style-stack", default="")
    parser.add_argument("--axis-mode", default="auto")
    parser.add_argument("--library", default="matplotlib")
    parser.add_argument("--multi-order", default="line")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--art-type", default="combo")
    parser.add_argument("--dpi", type=int, default=0)
    parser.add_argument("--overrides", default="")
    parser.add_argument("--out-root", default="output")
    parser.add_argument("--layout-priors", dest="layout_priors", action="store_true")
    parser.add_argument("--no-layout-priors", dest="layout_priors", action="store_false")
    parser.add_argument("--run", dest="run", action="store_true")
    parser.add_argument("--no-run", dest="run", action="store_false")
    parser.add_argument("--validate", dest="validate", action="store_true")
    parser.add_argument("--no-validate", dest="validate", action="store_false")
    parser.add_argument("--validate-profile", default="")
    parser.add_argument("--validate-art-type", default="auto")
    parser.add_argument("--output-mode", choices=["json", "text"], default="json")
    parser.add_argument("--template-mode", choices=["thin"], default="thin")
    parser.set_defaults(layout_priors=True, run=False, validate=False)
    return parser.parse_args()


def parse_patch_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch existing plot.py by structured JSON patch.")
    parser.add_argument("--plot", required=True)
    parser.add_argument("--patch", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-patch-l3", action="store_true")
    parser.add_argument("--backup", dest="backup", action="store_true")
    parser.add_argument("--no-backup", dest="backup", action="store_false")
    parser.add_argument("--backup-dir", default="")
    parser.add_argument("--layout-priors", dest="layout_priors", action="store_true")
    parser.add_argument("--no-layout-priors", dest="layout_priors", action="store_false")
    parser.add_argument("--run", dest="run", action="store_true")
    parser.add_argument("--no-run", dest="run", action="store_false")
    parser.add_argument("--validate", dest="validate", action="store_true")
    parser.add_argument("--no-validate", dest="validate", action="store_false")
    parser.add_argument("--validate-profile", default="")
    parser.add_argument("--validate-art-type", default="auto")
    parser.add_argument("--output-mode", choices=["json", "text"], default="json")
    parser.set_defaults(backup=True, layout_priors=True, run=False, validate=False)
    return parser.parse_args()


def _print_text_result(mode: str, payload: dict[str, Any]) -> None:
    print(f"[OK] mode={mode}")
    if mode == "create":
        print(f"[OK] job_dir={payload.get('job_dir')}")
    print(f"[OK] plot={payload.get('plot')}")
    if payload.get("backup"):
        print(f"[OK] backup={payload.get('backup')}")
    if payload.get("figure"):
        print(f"[OK] figure={payload.get('figure')}")
    print(f"[OK] report={payload.get('report')}")


def run_create_cli() -> None:
    args = parse_create_args()
    _run_cli(mode="create", args=args)


def run_patch_cli() -> None:
    args = parse_patch_args()
    _run_cli(mode="fast_patch", args=args)


def _run_cli(*, mode: str, args: argparse.Namespace) -> None:
    output_mode = str(getattr(args, "output_mode", "json"))
    try:
        payload = run_orchestrator(mode=mode, request={"args": args})
    except Exception as exc:  # noqa: BLE001
        error_type, hint = classify_generic_error(exc, json_label=mode)
        payload = {
            "status": "error",
            "mode": mode,
            "error_type": error_type,
            "error": str(exc),
            "hint": hint,
        }
        if output_mode == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"[ERROR] {exc}")
        raise SystemExit(1)

    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_text_result(mode, payload)


__all__ = [
    "parse_create_args",
    "parse_patch_args",
    "run_create_cli",
    "run_patch_cli",
]
