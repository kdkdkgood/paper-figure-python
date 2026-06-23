#!/usr/bin/env python3
"""统一 orchestrator 入口。"""

from __future__ import annotations

from typing import Any

from orchestrator.service import run


def run_orchestrator(mode: str, request: dict[str, Any]) -> dict[str, Any]:
    """Run orchestrator by mode.

    支持两种 request 形式：
    1) 直接参数字典；
    2) {"args": argparse.Namespace}。
    """

    if "args" in request:
        args = request.get("args")
        kwargs = vars(args) if args is not None else {}
    else:
        kwargs = dict(request)
    kwargs.pop("cli_argv", None)
    return run(mode, **kwargs)


__all__ = ["run_orchestrator"]
