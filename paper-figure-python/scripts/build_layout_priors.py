#!/usr/bin/env python3
"""批量构建 layout priors（覆盖全部 A×B 形状）。"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from params.defaults.l0_route_defaults import DEFAULT_MULTI_ORDER
from params.defaults.l0_route_defaults import LAYOUT_GRID
from params.defaults.l0_route_defaults import LAYOUT_TO_ADJUST_KEY
from params.defaults.l3_layout_defaults import ADJUST_SPEC_DEFAULTS

ADJUST_KEYS = ("left", "right", "top", "bottom", "wspace", "hspace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建并写入 layout priors（A×B 全覆盖）")
    parser.add_argument("--out-root", default="output", help="create_figure.py 输出根目录")
    parser.add_argument("--report-dir", default="", help="运行报告目录；为空时自动写到 output/regression_reports/")
    parser.add_argument(
        "--records-dir",
        default="paper-figure-python/references/layout_priors",
        help="per-shape records 输出目录",
    )
    parser.add_argument(
        "--index-file",
        default="paper-figure-python/references/layout_priors_index.json",
        help="index 输出路径",
    )
    parser.add_argument("--style-profile", default="elsevier")
    parser.add_argument("--library", default="matplotlib", choices=["matplotlib", "seaborn"])
    parser.add_argument("--art-type", default="combo", choices=["line", "photo", "combo"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-fallback-passes", type=int, default=10)
    parser.add_argument("--stop-threshold-px", type=float, default=0.8)
    parser.add_argument("--case-timeout-s", type=int, default=120, help="单个 case 超时秒数")
    parser.add_argument("--max-cases", type=int, default=0, help="仅执行前 N 个 case（0=全部）")
    parser.add_argument("--run", dest="run", action="store_true", help="显式执行 plot.py（默认开启）")
    parser.add_argument("--no-run", dest="run", action="store_false", help="仅生成代码，不执行绘图")
    parser.add_argument("--dry-run", action="store_true", help="只跑测试与报告，不落盘 priors 文件")
    parser.set_defaults(run=True)
    return parser.parse_args()


def _shape_key(nrows: int, ncols: int) -> tuple[int, int]:
    return int(nrows), int(ncols)


def _shape_axis_key(nrows: int, ncols: int, axis_mode: str) -> str:
    return f"{int(nrows)}x{int(ncols)}|{str(axis_mode)}"


def _panel_signature(panel_types: list[str]) -> str:
    return "+".join(str(item) for item in panel_types)


def _repeat_signature(panel_type: str, n_panels: int) -> str:
    return "+".join([panel_type] * max(1, int(n_panels)))


def _build_multi_order(n_panels: int) -> list[str]:
    base = list(DEFAULT_MULTI_ORDER)
    if n_panels <= len(base):
        return base[:n_panels]
    seq: list[str] = []
    while len(seq) < n_panels:
        seq.extend(base)
    return seq[:n_panels]


def _canonical_layouts_by_shape() -> tuple[dict[tuple[int, int], str], dict[tuple[int, int], list[str]]]:
    canonical: dict[tuple[int, int], str] = {}
    all_layouts: dict[tuple[int, int], list[str]] = {}
    for layout, grid in LAYOUT_GRID.items():
        key = _shape_key(grid["nrows"], grid["ncols"])
        all_layouts.setdefault(key, []).append(str(layout))
        if key not in canonical:
            canonical[key] = str(layout)
    for key in all_layouts:
        all_layouts[key] = sorted(set(all_layouts[key]))
    return canonical, all_layouts


def _base_adjust_for_layout(layout: str) -> dict[str, float]:
    adjust_key = LAYOUT_TO_ADJUST_KEY.get(str(layout), "multi")
    base = deepcopy(ADJUST_SPEC_DEFAULTS.get(adjust_key, ADJUST_SPEC_DEFAULTS["multi"]))
    normalized: dict[str, float] = {}
    for key in ADJUST_KEYS:
        if key in base:
            normalized[key] = float(base[key])
        elif key in {"left", "bottom"}:
            normalized[key] = 0.0
        elif key in {"right", "top"}:
            normalized[key] = 1.0
        else:
            normalized[key] = 0.0
    return normalized


def _build_overrides(layout: str, max_fallback_passes: int, stop_threshold_px: float) -> dict[str, Any]:
    return {
        "adjust_spec": _base_adjust_for_layout(layout),
        "layout_guard_spec": {
            "max_fallback_passes": int(max_fallback_passes),
            "edge_tolerance_px": float(stop_threshold_px),
            "subplot_overlap_tolerance_px": float(stop_threshold_px),
        },
    }


def _build_cases(max_cases: int) -> list[dict[str, Any]]:
    canonical, _ = _canonical_layouts_by_shape()
    cases: list[dict[str, Any]] = []
    # 先按 panel 数，再按行列排序，方便报告阅读。
    ordered_shapes = sorted(canonical.keys(), key=lambda x: (x[0] * x[1], x[0], x[1]))
    for nrows, ncols in ordered_shapes:
        layout = canonical[(nrows, ncols)]
        n_panels = int(nrows * ncols)
        cases.append({"layout": layout, "nrows": nrows, "ncols": ncols, "axis_mode": "independent", "chart_type": "line"})
        cases.append({"layout": layout, "nrows": nrows, "ncols": ncols, "axis_mode": "shared_axis", "chart_type": "line"})
        cases.append({"layout": layout, "nrows": nrows, "ncols": ncols, "axis_mode": "independent", "chart_type": "heatmap"})
        if n_panels > 1:
            cases.append(
                {
                    "layout": layout,
                    "nrows": nrows,
                    "ncols": ncols,
                    "axis_mode": "independent",
                    "chart_type": "multi",
                    "multi_order": _build_multi_order(n_panels),
                }
            )
    if max_cases > 0:
        cases = cases[: max_cases]
    return cases


def _relative_job_dir(job_dir: str) -> str:
    try:
        return str(Path(job_dir).resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return str(job_dir)


def _compute_quality(layout_guard: dict[str, Any]) -> dict[str, Any]:
    passes = layout_guard.get("passes", [])
    if not isinstance(passes, list):
        passes = []
    pass_count = len(passes)
    used_scale_canvas = False
    final_max_residual_px = 0.0
    if passes:
        for item in passes:
            actions = item.get("actions", [])
            if isinstance(actions, list) and any(str(action) == "scale_canvas" for action in actions):
                used_scale_canvas = True
        last = passes[-1] if isinstance(passes[-1], dict) else {}
        overflow = last.get("overflow_px", {})
        deficit = last.get("gap_deficit_px", {})
        candidates: list[float] = []
        if isinstance(overflow, dict):
            for key in ("left", "right", "top", "bottom"):
                try:
                    candidates.append(float(overflow.get(key, 0.0)))
                except Exception:
                    pass
        if isinstance(deficit, dict):
            for key in ("horizontal", "vertical"):
                try:
                    candidates.append(float(deficit.get(key, 0.0)))
                except Exception:
                    pass
        if candidates:
            final_max_residual_px = max(0.0, max(candidates))
    return {
        "pass_count": int(pass_count),
        "used_scale_canvas": bool(used_scale_canvas),
        "final_max_residual_px": float(round(final_max_residual_px, 4)),
    }


def _better_quality(new_q: dict[str, Any], old_q: dict[str, Any]) -> bool:
    new_res = float(new_q.get("final_max_residual_px", 1e9))
    old_res = float(old_q.get("final_max_residual_px", 1e9))
    if new_res < old_res - 1e-9:
        return True
    if abs(new_res - old_res) > 1e-9:
        return False
    return int(new_q.get("pass_count", 1e9)) < int(old_q.get("pass_count", 1e9))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_final_adjust(metadata_payload: dict[str, Any]) -> dict[str, float] | None:
    crop_report = metadata_payload.get("crop_report", {})
    if isinstance(crop_report, dict):
        layout_guard = crop_report.get("layout_guard", {})
        if isinstance(layout_guard, dict):
            final_adjust = layout_guard.get("final_adjust", {})
            if isinstance(final_adjust, dict):
                normalized: dict[str, float] = {}
                for key in ADJUST_KEYS:
                    if key in final_adjust:
                        try:
                            normalized[key] = float(final_adjust[key])
                        except Exception:
                            pass
                if normalized:
                    return normalized

    cfg = metadata_payload.get("config", {})
    if isinstance(cfg, dict):
        adjust_spec = cfg.get("adjust_spec", {})
        if isinstance(adjust_spec, dict):
            normalized = {}
            for key in ADJUST_KEYS:
                if key in adjust_spec:
                    try:
                        normalized[key] = float(adjust_spec[key])
                    except Exception:
                        pass
            if normalized:
                return normalized
    return None


def _run_case(
    *,
    create_script: Path,
    case: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    layout = str(case["layout"])
    chart_type = str(case["chart_type"])
    axis_mode = str(case["axis_mode"])
    nrows = int(case["nrows"])
    ncols = int(case["ncols"])
    n_panels = max(1, nrows * ncols)

    task = f"prior_ab_{nrows}x{ncols}_{layout}_{axis_mode}_{chart_type}"
    overrides = _build_overrides(layout, args.max_fallback_passes, args.stop_threshold_px)
    cmd = [
        sys.executable,
        str(create_script),
        "--task",
        task,
        "--chart-type",
        chart_type,
        "--layout",
        layout,
        "--axis-mode",
        axis_mode,
        "--library",
        str(args.library),
        "--style-profile",
        str(args.style_profile),
        "--art-type",
        str(args.art_type),
        "--seed",
        str(args.seed),
        "--out-root",
        str(args.out_root),
        "--no-validate",
        "--output-mode",
        "json",
        "--overrides",
        json.dumps(overrides, ensure_ascii=False),
    ]
    cmd.append("--run" if bool(args.run) else "--no-run")
    if chart_type == "multi":
        multi_order = case.get("multi_order", _build_multi_order(n_panels))
        cmd.extend(["--multi-order", ",".join(str(x) for x in multi_order)])

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(1, int(args.case_timeout_s)),
        )
    except subprocess.TimeoutExpired as exc:
        elapsed_s = round(time.perf_counter() - t0, 3)
        return {
            "ok": False,
            "case": case,
            "elapsed_s": elapsed_s,
            "error": f"timeout>{int(args.case_timeout_s)}s",
            "stdout": str(getattr(exc, "stdout", "")),
            "stderr": str(getattr(exc, "stderr", "")),
            "returncode": 124,
        }
    elapsed_s = round(time.perf_counter() - t0, 3)

    try:
        payload = json.loads(proc.stdout.strip())
    except Exception:
        return {
            "ok": False,
            "case": case,
            "elapsed_s": elapsed_s,
            "error": "create_figure.py did not return json",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": int(proc.returncode),
        }

    if proc.returncode != 0 or payload.get("status") != "ok":
        return {
            "ok": False,
            "case": case,
            "elapsed_s": elapsed_s,
            "error": str(payload.get("error", "run_failed")),
            "payload": payload,
            "returncode": int(proc.returncode),
        }

    metadata_report = payload.get("report")
    if not isinstance(metadata_report, str):
        metadata_report = payload.get("metadata_report")
    if not isinstance(metadata_report, str):
        return {
            "ok": False,
            "case": case,
            "elapsed_s": elapsed_s,
            "error": "metadata_report missing",
            "payload": payload,
            "returncode": int(proc.returncode),
        }
    metadata_path = Path(metadata_report)
    if not metadata_path.exists():
        return {
            "ok": False,
            "case": case,
            "elapsed_s": elapsed_s,
            "error": f"metadata_report not found: {metadata_path}",
            "payload": payload,
            "returncode": int(proc.returncode),
        }
    metadata_payload = _read_json(metadata_path)
    final_adjust = _extract_final_adjust(metadata_payload)
    if not isinstance(final_adjust, dict) or not final_adjust:
        return {
            "ok": False,
            "case": case,
            "elapsed_s": elapsed_s,
            "error": "final_adjust missing",
            "payload": payload,
            "returncode": int(proc.returncode),
        }

    cfg = payload.get("config", {})
    runtime_derived = cfg.get("runtime_derived", {}) if isinstance(cfg, dict) else {}
    if not isinstance(runtime_derived, dict):
        runtime_derived = {}
    panel_types = runtime_derived.get("panel_types", [])
    if not isinstance(panel_types, list) or not panel_types:
        # 兜底：若 runtime 未给，则按 chart_type 推断。
        panel_types = [chart_type] * n_panels
    effective_axis_mode = str(cfg.get("effective_axis_mode", axis_mode)) if isinstance(cfg, dict) else axis_mode
    shape_axis = _shape_axis_key(nrows, ncols, effective_axis_mode)
    signature = _panel_signature([str(x) for x in panel_types])

    crop_report = metadata_payload.get("crop_report", {})
    layout_guard = crop_report.get("layout_guard", {}) if isinstance(crop_report, dict) else {}
    if not isinstance(layout_guard, dict):
        layout_guard = {}
    quality = _compute_quality(layout_guard)

    return {
        "ok": True,
        "case": case,
        "elapsed_s": elapsed_s,
        "shape_axis_key": shape_axis,
        "panel_types_signature": signature,
        "effective_axis_mode": effective_axis_mode,
        "adjust_spec": {k: float(final_adjust[k]) for k in ADJUST_KEYS if k in final_adjust},
        "quality": quality,
        "source_job_dir": _relative_job_dir(str(payload.get("job_dir", ""))),
        "payload": payload,
    }


def _select_default_variant(axis_mode: str, n_panels: int, variant_keys: list[str]) -> str:
    if not variant_keys:
        return ""
    variant_set = set(variant_keys)
    line_sig = _repeat_signature("line", n_panels)
    heatmap_sig = _repeat_signature("heatmap", n_panels)
    if str(axis_mode) == "shared_axis":
        if line_sig in variant_set:
            return line_sig
        return sorted(variant_keys)[0]
    if n_panels > 1 and heatmap_sig in variant_set:
        return heatmap_sig
    if line_sig in variant_set:
        return line_sig
    return sorted(variant_keys)[0]


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    script_dir = Path(__file__).resolve().parent
    create_script = script_dir / "create_figure.py"
    if not create_script.exists():
        raise SystemExit(f"未找到 create_figure.py: {create_script}")

    cases = _build_cases(max_cases=int(args.max_cases))
    if not cases:
        raise SystemExit("没有可执行 case。")

    if args.report_dir.strip():
        report_dir = Path(args.report_dir).resolve()
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = (root / "output" / "regression_reports" / f"layout_priors_{stamp}").resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    canonical, all_layouts = _canonical_layouts_by_shape()
    del canonical

    print(f"[INFO] cases={len(cases)}")
    run_results: list[dict[str, Any]] = []
    for idx, case in enumerate(cases, start=1):
        print(
            f"[{idx}/{len(cases)}] layout={case['layout']} "
            f"shape={case['nrows']}x{case['ncols']} axis={case['axis_mode']} chart={case['chart_type']}"
        )
        run_results.append(_run_case(create_script=create_script, case=case, args=args))

    ok_runs = [item for item in run_results if item.get("ok")]
    failed_runs = [item for item in run_results if not item.get("ok")]

    routes: dict[str, Any] = {}
    for item in ok_runs:
        shape_axis_key = str(item["shape_axis_key"])
        nrows, ncols = map(int, shape_axis_key.split("|")[0].split("x"))
        axis_mode = str(shape_axis_key.split("|", 1)[1])
        shape = _shape_key(nrows, ncols)
        bucket = routes.setdefault(
            shape_axis_key,
            {
                "allowed_layouts": list(all_layouts.get(shape, [])),
                "default_variant": "",
                "variants": {},
            },
        )
        variant_key = str(item["panel_types_signature"])
        new_record = {
            "adjust_spec": {k: float(item["adjust_spec"][k]) for k in ADJUST_KEYS if k in item["adjust_spec"]},
            "quality": dict(item["quality"]),
            "source_job_dir": str(item["source_job_dir"]),
        }
        existing = bucket["variants"].get(variant_key)
        if not isinstance(existing, dict):
            bucket["variants"][variant_key] = new_record
        else:
            old_quality = existing.get("quality", {})
            if _better_quality(new_q=new_record["quality"], old_q=old_quality if isinstance(old_quality, dict) else {}):
                bucket["variants"][variant_key] = new_record

        variant_keys = list(bucket["variants"].keys())
        bucket["default_variant"] = _select_default_variant(
            axis_mode=axis_mode,
            n_panels=nrows * ncols,
            variant_keys=variant_keys,
        )
        bucket["allowed_layouts"] = sorted(set(str(x) for x in bucket.get("allowed_layouts", [])))

    version = f"{datetime.now().strftime('%Y-%m-%d')}-layout-prior-v2-ab-full"
    records_payload = {
        "version": version,
        "selector": "shape_axis_then_panel_signature",
        "notes": [
            "first filter: nrows*ncols + effective_axis_mode",
            "second filter: panel_types_signature exact -> similar(in-bucket) -> default_variant",
            "all adjust_spec values come from layout_guard final_adjust with max_fallback_passes=10 and threshold_px=0.8",
        ],
        "routes": dict(sorted(routes.items(), key=lambda item: item[0])),
    }

    navigation: dict[str, Any] = {}
    for key, bucket in records_payload["routes"].items():
        variants = list(bucket.get("variants", {}).keys())
        navigation[key] = {
            "allowed_layouts": list(bucket.get("allowed_layouts", [])),
            "default_variant": str(bucket.get("default_variant", "")),
            "variants": sorted(variants),
        }
    index_payload = {
        "version": version,
        "dir": "references/layout_priors",
        "routes": {
            key: key.replace("|", "_") + ".json"
            for key in sorted(navigation.keys())
        },
    }

    records_dir = Path(args.records_dir).resolve()
    index_file = Path(args.index_file).resolve()
    summary_json = report_dir / "layout_priors_build_summary.json"
    summary_md = report_dir / "layout_priors_build_summary.md"

    summary_payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cases_total": len(cases),
        "cases_ok": len(ok_runs),
        "cases_failed": len(failed_runs),
        "records_dir": str(records_dir),
        "index_file": str(index_file),
        "routes_count": len(records_payload["routes"]),
        "dry_run": bool(args.dry_run),
        "failed": failed_runs,
    }
    summary_json.write_text(
        json.dumps(
            {
                "summary": summary_payload,
                "records_preview": records_payload,
                "index_preview": index_payload,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    md_lines = [
        "# Layout Priors Build Summary",
        "",
        f"- generated_at: `{summary_payload['generated_at']}`",
        f"- total: `{summary_payload['cases_total']}`",
        f"- ok: `{summary_payload['cases_ok']}`",
        f"- failed: `{summary_payload['cases_failed']}`",
        f"- routes_count: `{summary_payload['routes_count']}`",
        f"- dry_run: `{summary_payload['dry_run']}`",
        "",
        "## Failed Cases",
    ]
    if not failed_runs:
        md_lines.append("- none")
    else:
        for item in failed_runs:
            case = item.get("case", {})
            md_lines.append(
                f"- layout={case.get('layout')} shape={case.get('nrows')}x{case.get('ncols')} "
                f"axis={case.get('axis_mode')} chart={case.get('chart_type')} error={item.get('error')}"
            )
    summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    if not args.dry_run:
        records_dir.mkdir(parents=True, exist_ok=True)
        for shape_axis_key, bucket_data in records_payload["routes"].items():
            shape_file = {
                "shape_axis_key": shape_axis_key,
                "allowed_layouts": bucket_data["allowed_layouts"],
                "default_variant": bucket_data["default_variant"],
                "variants": {
                    vk: {"adjust_spec": vv["adjust_spec"]}
                    for vk, vv in bucket_data["variants"].items()
                },
            }
            filename = shape_axis_key.replace("|", "_") + ".json"
            (records_dir / filename).write_text(
                json.dumps(shape_file, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] records_dir={records_dir} ({len(records_payload['routes'])} files)")
        print(f"[OK] index={index_file}")
    else:
        print("[INFO] dry-run enabled: priors 文件未写入")

    print(f"[OK] summary_json={summary_json}")
    print(f"[OK] summary_md={summary_md}")
    print(f"[OK] routes={len(records_payload['routes'])} ok={len(ok_runs)} failed={len(failed_runs)}")
    if failed_runs:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
