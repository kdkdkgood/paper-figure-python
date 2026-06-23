#!/usr/bin/env python3
"""一键 smoke test：验证 thin job、绘图运行、后调整 patch 和合规检查。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            "命令失败："
            + " ".join(cmd)
            + "\nSTDOUT:\n"
            + result.stdout
            + "\nSTDERR:\n"
            + result.stderr
        )
    return result


def _write_heatmap_workbook(path: Path) -> None:
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(20260620)
    features = [f"Gene_{idx:02d}" for idx in range(1, 13)]
    samples = [f"Sample_{idx:02d}" for idx in range(1, 9)]
    matrix = rng.normal(0.0, 0.45, size=(len(features), len(samples)))
    matrix[:4, 2:5] += 0.9
    matrix[4:8, 5:] -= 0.8
    matrix[8:, :3] += 0.6
    df = pd.DataFrame(np.round(matrix, 3), columns=samples)
    df.insert(0, "feature_id", features)
    df.insert(1, "module", ["M1"] * 4 + ["M2"] * 4 + ["M3"] * 4)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="heatmap_matrix", index=False)


def _load_create_payload(stdout: str) -> dict:
    payload = json.loads(stdout)
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise RuntimeError(f"create 返回异常：{stdout}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run paper-figure-python smoke tests.")
    parser.add_argument("--out-root", default="output/smoke_tests")
    parser.add_argument("--keep-backups", action="store_true")
    args = parser.parse_args()

    scripts_root = Path(__file__).resolve().parent
    out_root = Path(args.out_root).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    data_path = out_root / "smoke_heatmap_data.xlsx"
    _write_heatmap_workbook(data_path)

    create_cmd = [
        sys.executable,
        str(scripts_root / "create_figure.py"),
        "--task",
        "smoke heatmap post-adjust test",
        "--job-name",
        "smoke_heatmap_post_adjust",
        "--chart-type",
        "custom",
        "--layout",
        "double",
        "--style-profile",
        "elsevier",
        "--axis-mode",
        "independent",
        "--out-root",
        str(out_root),
        "--output-mode",
        "json",
        "--template-mode",
        "thin",
        "--no-run",
        "--no-validate",
    ]
    create_result = _run(create_cmd, cwd=scripts_root)
    create_payload = _load_create_payload(create_result.stdout)
    plot_path = Path(create_payload["plot"])
    job_dir = plot_path.parent

    zone_patch = {
        "overrides": {
            "extra_config": {
                "AI_EDIT_ZONE:imports": "import numpy as np\nimport pandas as pd",
                "AI_EDIT_ZONE:pre_draw": (
                    f"df = pd.read_excel({str(data_path)!r}, sheet_name='heatmap_matrix')\n"
                    "sample_cols = [col for col in df.columns if str(col).startswith('Sample_')]\n"
                    "ctx.df_override = {'table': df, 'sample_cols': sample_cols, 'matrix': df[sample_cols].to_numpy(dtype=float)}"
                ),
                "AI_EDIT_ZONE:post_draw": (
                    "ax = ctx.ax(0)\n"
                    "ax.cla()\n"
                    "payload = ctx.df_override\n"
                    "matrix = payload['matrix']\n"
                    "df = payload['table']\n"
                    "sample_cols = payload['sample_cols']\n"
                    "style = ctx.style\n"
                    "vmax = float(np.nanmax(np.abs(matrix)))\n"
                    "im = ax.imshow(matrix, aspect='auto', cmap='RdBu_r', vmin=-vmax, vmax=vmax)\n"
                    "ax.set_xticks(np.arange(len(sample_cols)))\n"
                    "ax.set_xticklabels(sample_cols, rotation=45, ha='right', fontsize=style['tick_label_size'])\n"
                    "ax.set_yticks(np.arange(len(df)))\n"
                    "ax.set_yticklabels(df['feature_id'].astype(str).tolist(), fontsize=style['tick_label_size'])\n"
                    "ax.set_xlabel('Samples', fontsize=style['axis_label_size'])\n"
                    "ax.set_ylabel('Features', fontsize=style['axis_label_size'])\n"
                    "ax.set_title('Smoke heatmap', fontsize=style['title_size'], pad=8)\n"
                    "ctx.fig.colorbar(im, ax=ax, fraction=0.035, pad=0.025)"
                ),
            }
        }
    }
    zone_patch_path = out_root / "smoke_zone_patch.json"
    zone_patch_path.write_text(json.dumps(zone_patch, ensure_ascii=False, indent=2), encoding="utf-8")

    patch_cmd = [
        sys.executable,
        str(scripts_root / "patch_figure.py"),
        "--plot",
        str(plot_path),
        "--patch",
        str(zone_patch_path),
        "--run",
        "--output-mode",
        "json",
    ]
    if not args.keep_backups:
        patch_cmd.append("--no-backup")
    _run(patch_cmd, cwd=scripts_root)

    adjust_patch = {
        "overrides": {
            "layout_spec": {"aspect_ratio": 1.0},
            "layout_guard_spec": {"intent": "roomy", "preferred_canvas_scale": 1.12},
        }
    }
    adjust_patch_path = out_root / "smoke_adjust_patch.json"
    adjust_patch_path.write_text(json.dumps(adjust_patch, ensure_ascii=False, indent=2), encoding="utf-8")
    adjust_cmd = [
        sys.executable,
        str(scripts_root / "patch_figure.py"),
        "--plot",
        str(plot_path),
        "--patch",
        str(adjust_patch_path),
        "--run",
        "--output-mode",
        "json",
    ]
    if not args.keep_backups:
        adjust_cmd.append("--no-backup")
    _run(adjust_cmd, cwd=scripts_root)

    check_cmd = [
        sys.executable,
        str(scripts_root / "check_workflow_compliance.py"),
        "--job-dir",
        str(job_dir),
        "--output-mode",
        "text",
    ]
    check_result = _run(check_cmd, cwd=scripts_root)

    crop_report = json.loads((job_dir / "crop_report.json").read_text(encoding="utf-8"))
    guard = crop_report.get("layout_guard", {})
    print(json.dumps(
        {
            "status": "ok",
            "job_dir": str(job_dir),
            "figure": str(job_dir / "figure.png"),
            "compliance": check_result.stdout.strip(),
            "final_size_in": guard.get("final_size_in"),
            "final_overflow_resolved": guard.get("final_overflow_resolved"),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
