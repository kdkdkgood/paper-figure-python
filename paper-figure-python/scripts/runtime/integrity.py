"""共享底座完整性自检。

paper-figure-python 的 ``scripts/runtime/`` 与 ``scripts/orchestrator/core.py``
是所有 job 共享的底座。它们被设计为稳定不变——具体图型的灵活性全部落在每个
job 独立的 ``plot.py`` 的 AI_EDIT_ZONE 中。

本模块在每次出图时对底座文件算指纹并与基线比对：底座一旦被改（无论是 AI 在
调试压力下误改引擎，还是 git pull 引入的版本漂移），出图时会在 stderr 打印醒目
警告、并在 run report 中留痕，但**绝不阻断出图**——护栏是诊断信号，不是闸门。

基线文件 ``scripts/.runtime_baseline.json`` 由 ``memory.py baseline`` 命令生成/刷新：
故意升级底座后刷新一次，警告即消失。基线缺失时自检静默跳过（首装即无噪音）。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# 受保护的共享底座文件（相对 scripts/ 根目录）。
# 只列真正跨 job 共享、不该被单张图改动的稳定底座。
PROTECTED_FILES: tuple[str, ...] = (
    "runtime/__init__.py",
    "runtime/engine.py",
    "runtime/context.py",
    "runtime/helpers.py",
    "runtime/integrity.py",
    "orchestrator/core.py",
)

BASELINE_NAME = ".runtime_baseline.json"


def scripts_root() -> Path:
    """含 runtime/ 与 orchestrator/ 的 scripts 目录（本文件的祖父目录）。"""
    return Path(__file__).resolve().parent.parent


def _hash_file(path: Path) -> str | None:
    """文件 SHA256 前 16 位；不存在或不可读返回 None。"""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def compute_fingerprints(root: Path | None = None) -> dict[str, str | None]:
    """对所有受保护文件算指纹。值为 None 表示该文件缺失/不可读。"""
    base = root or scripts_root()
    return {rel: _hash_file(base / rel) for rel in PROTECTED_FILES}


def baseline_path(root: Path | None = None) -> Path:
    return (root or scripts_root()) / BASELINE_NAME


def write_baseline(root: Path | None = None) -> dict[str, Any]:
    """把当前底座指纹写入基线文件。故意升级底座后调用一次。"""
    base = root or scripts_root()
    fingerprints = compute_fingerprints(base)
    payload = {
        "schema": "runtime-baseline/1",
        "protected_files": list(PROTECTED_FILES),
        "fingerprints": fingerprints,
    }
    baseline_path(base).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def load_baseline(root: Path | None = None) -> dict[str, str | None] | None:
    """读取基线指纹映射；基线缺失或损坏返回 None（自检静默跳过）。"""
    try:
        data = json.loads(baseline_path(root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    fps = data.get("fingerprints")
    return fps if isinstance(fps, dict) else None


def check_integrity(root: Path | None = None) -> dict[str, Any]:
    """比对当前底座与基线。

    返回 ``status`` 取值：
    - ``"no_baseline"``：基线缺失，自检跳过（首次安装或尚未建立基线）。
    - ``"ok"``：底座与基线完全一致。
    - ``"drift"``：检测到改动，``drift`` 列出 modified/missing/added 文件。
    """
    base = root or scripts_root()
    baseline = load_baseline(base)
    if baseline is None:
        return {"status": "no_baseline", "drift": {}}

    current = compute_fingerprints(base)
    modified, missing, added = [], [], []
    for rel in PROTECTED_FILES:
        old, new = baseline.get(rel), current.get(rel)
        if old == new:
            continue
        if old is not None and new is None:
            missing.append(rel)
        elif old is None and new is not None:
            added.append(rel)
        else:
            modified.append(rel)

    drift = {
        k: v for k, v in
        (("modified", modified), ("missing", missing), ("added", added))
        if v
    }
    return {"status": "drift" if drift else "ok", "drift": drift}


def format_warning(result: dict[str, Any]) -> str:
    """把 drift 结果格式化为一段醒目的 stderr 警告。无 drift 返回空串。"""
    if result.get("status") != "drift":
        return ""
    drift = result.get("drift", {})
    lines = [
        "",
        "  ⚠️  paper-figure-python 共享底座被改动",
        "  ─────────────────────────────────────────────",
        "  scripts/runtime/ 与 orchestrator/core.py 是跨 job 共享底座，",
        "  本不应为单张图改动。检测到以下偏离基线：",
    ]
    labels = {"modified": "已修改", "missing": "已删除", "added": "新增"}
    for kind, files in drift.items():
        for rel in files:
            lines.append(f"    · [{labels.get(kind, kind)}] {rel}")
    lines += [
        "  ─────────────────────────────────────────────",
        "  · 若误改了引擎来迁就单张图：请改回，把逻辑落到 job 的 plot.py。",
        "  · 若是故意升级底座：python memory.py baseline --refresh 刷新基线消除本警告。",
        "",
    ]
    return "\n".join(lines)
