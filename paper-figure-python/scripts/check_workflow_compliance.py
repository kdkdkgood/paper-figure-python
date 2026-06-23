#!/usr/bin/env python3
"""检查输出是否符合新架构约束。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_PY_FILES = {"plot.py"}
REQUIRED_REPORT_KEYS = {"mode"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check workflow compliance.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--job-dir", default="", help="单个任务目录")
    target.add_argument("--out-root", default="", help="批量扫描 output 根目录")

    parser.add_argument("--output-mode", choices=["json", "text"], default="json")
    parser.add_argument("--fail-exit-code", type=int, default=2)
    parser.add_argument("--allow-extra-python", action="store_true", help="允许额外 .py 文件（默认不允许）")
    return parser.parse_args()


def _latest_report_path(job_dir: Path) -> Path | None:
    history_dir = job_dir / "orchestrator_reports"
    if history_dir.exists():
        files = sorted(history_dir.glob("*.json"))
        if files:
            return files[-1]
    canonical = job_dir / "orchestrator_report.json"
    if canonical.exists():
        return canonical
    return None


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return loaded if isinstance(loaded, dict) else None


def _check_figure_output(job_dir: Path, issues: list[str]) -> None:
    figure_path = job_dir / "figure.png"
    if not figure_path.exists():
        issues.append("缺少 figure.png（作业尚未运行或运行失败）")


def _check_python_syntax(path: Path, issues: list[str]) -> None:
    try:
        source = path.read_text(encoding="utf-8")
    except Exception:
        issues.append(f"{path.name} 无法读取")
        return
    try:
        compile(source, str(path), "exec")
    except SyntaxError as exc:
        issues.append(f"{path.name} 语法错误 (行 {exc.lineno}): {exc.msg}")


def _extract_template_mode(plot_text: str) -> str:
    for line in plot_text.splitlines():
        if line.startswith("# TEMPLATE_MODE:"):
            mode = line.split(":", 1)[1].strip().lower()
            return mode or "bundled"
    return "bundled"


def _check_template_mode_semantics(
    *,
    job_dir: Path,
    plot_text: str,
    report: dict[str, Any] | None,
    issues: list[str],
) -> None:
    template_mode = _extract_template_mode(plot_text)
    if template_mode not in {"bundled", "thin"}:
        issues.append(f"未知 TEMPLATE_MODE: {template_mode}")
        return

    if template_mode == "thin":
        if "from runtime import FigureContext, run_figure" not in plot_text:
            issues.append("thin plot 缺少 runtime 入口导入")
        for helper_name in ("_pf_layout_guard.py", "_pf_cropper.py"):
            if (job_dir / helper_name).exists():
                issues.append(f"thin plot 不应生成 helper 文件: {helper_name}")

    if not isinstance(report, dict):
        return
    report_job = report.get("job")
    if not isinstance(report_job, dict):
        return
    report_mode = str(report_job.get("template_mode", "bundled")).strip().lower() or "bundled"
    if report_mode != template_mode:
        issues.append(f"report job.template_mode={report_mode} 与 plot TEMPLATE_MODE={template_mode} 不一致")


def _check_job(job_dir: Path, *, allow_extra_python: bool) -> dict[str, Any]:
    issues: list[str] = []
    job_dir = job_dir.resolve()
    plot_path = job_dir / "plot.py"
    if not plot_path.exists():
        issues.append("缺少 plot.py")
        return {"job_dir": str(job_dir), "passed": False, "issues": issues}

    plot_text = plot_path.read_text(encoding="utf-8")
    if "# SOURCE_TEMPLATE:" not in plot_text:
        issues.append("plot.py 缺少 SOURCE_TEMPLATE 标记")
    if "AI_EDIT_ZONE:imports START" not in plot_text:
        issues.append("plot.py 缺少 AI_EDIT_ZONE 标记")

    _check_python_syntax(plot_path, issues)
    for helper_name in ("_pf_layout_guard.py", "_pf_cropper.py"):
        helper_path = job_dir / helper_name
        if helper_path.exists():
            _check_python_syntax(helper_path, issues)

    py_files = sorted(p.name for p in job_dir.glob("*.py"))
    if not allow_extra_python:
        extras = [name for name in py_files if name not in ALLOWED_PY_FILES]
        if extras:
            issues.append(f"存在旁路脚本: {extras}")

    _check_figure_output(job_dir, issues)

    report_path = _latest_report_path(job_dir)
    report: dict[str, Any] | None = None
    if report_path is None:
        issues.append("缺少 orchestrator report")
    else:
        report = _load_json(report_path)
        if report is None:
            issues.append("orchestrator report 不是有效 JSON")
        else:
            missing = sorted(REQUIRED_REPORT_KEYS - set(report.keys()))
            if missing:
                issues.append(f"orchestrator report 缺字段: {missing}")

    _check_template_mode_semantics(job_dir=job_dir, plot_text=plot_text, report=report, issues=issues)

    return {
        "job_dir": str(job_dir),
        "passed": len(issues) == 0,
        "issues": issues,
    }


def _discover_job_dirs(out_root: Path) -> list[Path]:
    if not out_root.exists():
        return []
    return sorted({path.parent.resolve() for path in out_root.rglob("plot.py")})


def _find_root_stray_python(out_root: Path, job_dirs: list[Path], allow_extra_python: bool) -> list[str]:
    if allow_extra_python:
        return []
    job_dir_set = {p.resolve() for p in job_dirs}
    stray: list[str] = []
    for path in out_root.rglob("*.py"):
        parent = path.parent.resolve()
        if parent in job_dir_set and path.name in ALLOWED_PY_FILES:
            continue
        stray.append(str(path.resolve()))
    return sorted(stray)


def main() -> None:
    args = parse_args()
    allow_extra_python = bool(args.allow_extra_python)

    if str(args.job_dir).strip():
        job_dirs = [Path(str(args.job_dir).strip())]
        stray_files: list[str] = []
    else:
        out_root = Path(str(args.out_root).strip())
        job_dirs = _discover_job_dirs(out_root)
        stray_files = _find_root_stray_python(out_root, job_dirs, allow_extra_python=allow_extra_python)

    details = [
        _check_job(job_dir, allow_extra_python=allow_extra_python)
        for job_dir in job_dirs
    ]
    failed = [item for item in details if not bool(item.get("passed"))]

    if stray_files:
        failed.append(
            {
                "job_dir": "__out_root__",
                "passed": False,
                "issues": [f"检测到旁路 .py 文件: {stray_files}"],
            }
        )

    payload = {
        "status": "ok" if len(failed) == 0 else "fail",
        "total_jobs": len(details),
        "passed_jobs": len(details) - len([d for d in details if not d.get("passed")]),
        "failed_jobs": failed,
        "details": details,
    }

    if args.output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"[CHECK] status={payload['status']} total_jobs={payload['total_jobs']}")
        for item in failed:
            print(f"[CHECK][FAIL] {item.get('job_dir')}")
            for issue in item.get("issues", []):
                print(f"  - {issue}")

    if payload["status"] == "ok":
        raise SystemExit(0)
    raise SystemExit(int(args.fail_exit_code))


if __name__ == "__main__":
    main()
