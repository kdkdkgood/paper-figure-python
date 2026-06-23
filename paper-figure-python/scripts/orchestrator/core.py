#!/usr/bin/env python3
"""共享 orchestrator 内核能力。"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any
from datetime import datetime


ORCHESTRATOR_REPORT_NAME = "orchestrator_report.json"
ORCHESTRATOR_REPORT_HISTORY_DIR = "orchestrator_reports"


def run_command(
    cmd: list[str],
    cwd: Path,
    capture: bool,
    env_extra: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """统一子进程执行。"""

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    if capture:
        proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=env, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    proc = subprocess.run(cmd, cwd=cwd, check=False, env=env)
    return proc.returncode, "", ""


def build_runtime_env(job_dir: Path) -> dict[str, str]:
    """构造 matplotlib 运行环境变量。

    默认使用 job-local 缓存目录，避免访问用户 home 下不可写缓存导致 stderr 噪声；
    可通过 PF_MPLCONFIGDIR 覆盖。
    """

    override = str(os.environ.get("PF_MPLCONFIGDIR", "")).strip()
    if not override:
        override = str((Path(job_dir) / ".mplconfig").resolve())
    mplconfig_dir = Path(override).expanduser()
    mplconfig_dir.mkdir(parents=True, exist_ok=True)
    xdg_cache_home = (Path(job_dir) / ".cache").resolve()
    xdg_cache_home.mkdir(parents=True, exist_ok=True)
    return {
        "MPLCONFIGDIR": str(mplconfig_dir),
        "XDG_CACHE_HOME": str(xdg_cache_home),
    }


def emit_json_and_exit(payload: dict[str, Any], code: int) -> None:
    """统一 JSON 输出并退出。"""

    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(code)


def write_orchestrator_report(job_dir: Path, payload: dict[str, Any]) -> Path:
    """Write canonical report and append history snapshot."""

    report_path = job_dir / ORCHESTRATOR_REPORT_NAME
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    history_dir = job_dir / ORCHESTRATOR_REPORT_HISTORY_DIR
    history_dir.mkdir(parents=True, exist_ok=True)
    mode = str(payload.get("mode", "create")).strip().lower() or "create"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    snapshot_path = history_dir / f"{ts}_{mode}.json"
    snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def classify_generic_error(exc: Exception, *, json_label: str) -> tuple[str, str]:
    """统一错误类型映射。"""

    if isinstance(exc, json.JSONDecodeError):
        return "invalid_json", f"请检查 {json_label} JSON 格式。"
    if isinstance(exc, ValueError):
        return "invalid_argument", "请根据报错提示修正输入参数。"
    if isinstance(exc, FileNotFoundError):
        return "file_not_found", "请检查输入路径和输出文件是否存在。"
    return "runtime_error", "请查看 error_stage 与 stderr 信息定位问题。"


__all__ = [
    "ORCHESTRATOR_REPORT_NAME",
    "ORCHESTRATOR_REPORT_HISTORY_DIR",
    "classify_generic_error",
    "emit_json_and_exit",
    "run_command",
    "write_orchestrator_report",
]
