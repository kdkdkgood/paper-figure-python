#!/usr/bin/env python3
"""精简后的统一编排服务（create + fast_patch）。"""

from __future__ import annotations

import ast
import json
import re
import sys
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from contracts.output_contract import build_route_key
from contracts.output_contract import resolve_axis_mode_state
from contracts.style_contracts import map_validate_profile
from jobgen_config import build_config
from jobgen_config import build_runtime_config
from jobgen_config import deep_update
from jobgen_config import load_overrides
from jobgen_config import slugify_task
from jobgen_config import validate_overrides
from jobgen_schema import CONFIG_BLOCK_RE
from jobgen_schema import TOP_LEVEL_OVERRIDE_KEYS
from jobgen_template import render_thin_plot_script
from orchestrator.core import build_runtime_env
from orchestrator.core import run_command
from orchestrator.core import write_orchestrator_report
from policy.change_level_policy import ROUTE_PATCH_KEYS
from policy.change_level_policy import contract_violation_reason
from policy.change_level_policy import infer_change_level

AI_EDIT_ZONE_RE = re.compile(
    r"(?s)(?P<indent>[ \t]*)# --- AI_EDIT_ZONE:(?P<name>[A-Za-z0-9_\-]+) START ---\n"
    r"(?P<body>.*?)(?P=indent)# --- AI_EDIT_ZONE:(?P=name) END ---"
)


@dataclass(frozen=True)
class ServicePaths:
    scripts_dir: Path
    validator_path: Path


def _paths() -> ServicePaths:
    scripts_dir = Path(__file__).resolve().parents[1]
    return ServicePaths(
        scripts_dir=scripts_dir,
        validator_path=scripts_dir / "validate_figure.py",
    )


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _reserve_job_dir(out_root: Path, job_name: str) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    target = out_root / job_name
    if not target.exists():
        target.mkdir(parents=True, exist_ok=False)
        return target
    idx = 2
    while True:
        candidate = out_root / f"{job_name}_{idx:02d}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        idx += 1


def _build_job_name(task: str, layout: str, chart_type: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{slugify_task(task)}_{layout}_{chart_type}"


def _to_int(raw: Any, default: int) -> int:
    try:
        return int(raw)
    except Exception:
        return int(default)


def _to_route_args(route: dict[str, Any]) -> Any:
    style_stack_raw = route.get("style_stack", "")
    if isinstance(style_stack_raw, list):
        style_stack = ",".join(str(x).strip() for x in style_stack_raw if str(x).strip())
    else:
        style_stack = str(style_stack_raw or "")

    multi_order_raw = route.get("multi_order", "line")
    if isinstance(multi_order_raw, list):
        multi_order = ",".join(str(x).strip() for x in multi_order_raw if str(x).strip())
    else:
        multi_order = str(multi_order_raw or "line")

    return SimpleNamespace(
        task=str(route.get("task", "科研绘图任务")),
        chart_type=str(route.get("chart_type", "multi")),
        layout=str(route.get("layout", "")),
        axis_mode=str(route.get("axis_mode", "auto")),
        library=str(route.get("library", "matplotlib")),
        style_profile=str(route.get("style_profile", "elsevier")),
        style_stack=style_stack,
        seed=_to_int(route.get("seed", 42), 42),
        art_type=str(route.get("art_type", "combo")),
        dpi=_to_int(route.get("dpi", 0), 0),
        multi_order=multi_order,
    )


def _build_compiled_runtime(
    *,
    route: dict[str, Any],
    overrides: dict[str, Any],
    use_layout_prior: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    args = _to_route_args(route)
    override_warnings = validate_overrides(overrides=overrides, strict=True)
    if override_warnings:
        # strict=True 下理论上不会进到这里，保留防御。
        raise ValueError("overrides 校验失败：" + "；".join(override_warnings))
    compiled = build_config(args=args, overrides=overrides, use_layout_prior=use_layout_prior)
    runtime = build_runtime_config(compiled)
    return compiled, runtime


def _extract_ai_edit_zones(plot_text: str) -> dict[str, str]:
    zones: dict[str, str] = {}
    for match in AI_EDIT_ZONE_RE.finditer(plot_text):
        name = str(match.group("name")).strip()
        if not name:
            continue
        zones[name] = str(match.group("body"))
    return zones


def _apply_ai_edit_zones(*, new_plot_text: str, preserved_zones: dict[str, str]) -> str:
    if not preserved_zones:
        return new_plot_text

    def _replace(match: re.Match) -> str:
        name = str(match.group("name")).strip()
        if name not in preserved_zones:
            return match.group(0)
        indent = str(match.group("indent"))
        start = f"{indent}# --- AI_EDIT_ZONE:{name} START ---\n"
        end = f"{indent}# --- AI_EDIT_ZONE:{name} END ---"
        return f"{start}{preserved_zones[name]}{end}"

    return AI_EDIT_ZONE_RE.sub(_replace, new_plot_text)


def _resolve_string_expr(expr: ast.AST, literals: dict[str, str]) -> str:
    if isinstance(expr, ast.Name):
        key = str(expr.id)
        if key in literals:
            return str(literals[key])
        raise ValueError(f"CONFIG 依赖未定义字符串变量: {key}")
    value = ast.literal_eval(expr)
    if not isinstance(value, str):
        raise ValueError("CONFIG literal 不是字符串")
    return value


def _parse_config_block(block: str) -> dict[str, Any]:
    tree = ast.parse(block)
    literals: dict[str, str] = {}
    config_payload: str | None = None
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        name = str(target.id)
        if name != "CONFIG":
            try:
                raw = ast.literal_eval(node.value)
            except Exception:
                continue
            if isinstance(raw, str):
                literals[name] = raw
            continue

        call = node.value
        if not isinstance(call, ast.Call):
            continue
        if not isinstance(call.func, ast.Attribute):
            continue
        if not isinstance(call.func.value, ast.Name):
            continue
        if str(call.func.value.id) != "json" or str(call.func.attr) != "loads":
            continue
        if not call.args:
            continue
        config_payload = _resolve_string_expr(call.args[0], literals)
        break

    if config_payload is None:
        raise ValueError("未找到 CONFIG = json.loads(...) 配置块")
    loaded = json.loads(config_payload)
    if not isinstance(loaded, dict):
        raise ValueError("CONFIG 必须是 JSON 对象")
    return loaded


def _extract_config_from_plot(plot_text: str) -> dict[str, Any]:
    match = CONFIG_BLOCK_RE.search(plot_text)
    if match is None:
        raise ValueError("plot.py 缺少 CONFIG 块")
    return _parse_config_block(match.group(0))


def _load_json_object(raw: str) -> dict[str, Any]:
    text = str(raw).strip()
    if not text:
        return {}
    if text.startswith(("{", "[")):
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("输入必须是 JSON 对象")
        return payload
    candidate = Path(text)
    if candidate.exists():
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    else:
        payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("输入必须是 JSON 对象")
    return payload


def _extract_route_patch(patch: dict[str, Any]) -> dict[str, Any]:
    route_patch: dict[str, Any] = {}
    inline_route = patch.get("route")
    if inline_route is not None:
        if not isinstance(inline_route, dict):
            raise ValueError("patch.route 必须是对象")
        route_patch.update(inline_route)
    for key in ROUTE_PATCH_KEYS:
        if key in patch:
            route_patch[key] = deepcopy(patch[key])
    unknown = sorted(set(route_patch.keys()) - ROUTE_PATCH_KEYS)
    if unknown:
        raise ValueError(f"route patch 含未知键: {unknown}")
    return route_patch


def _extract_override_patch(patch: dict[str, Any]) -> dict[str, Any]:
    def _merge_legacy_panel_mappings(*, source: dict[str, Any], source_name: str, target: dict[str, Any]) -> None:
        if "panel_mappings" not in source:
            return
        panel_mappings = source.get("panel_mappings")
        if not isinstance(panel_mappings, dict):
            raise ValueError(f"{source_name}.panel_mappings 必须是对象")

        existing_data_spec = target.get("data_spec")
        if existing_data_spec is None:
            target["data_spec"] = {"panel_mappings": deepcopy(panel_mappings)}
            return
        if not isinstance(existing_data_spec, dict):
            raise ValueError(f"{source_name}.data_spec 必须是对象（因存在 panel_mappings）")

        existing_mappings = existing_data_spec.get("panel_mappings")
        if existing_mappings is None:
            existing_data_spec["panel_mappings"] = deepcopy(panel_mappings)
            return
        if not isinstance(existing_mappings, dict):
            raise ValueError(f"{source_name}.data_spec.panel_mappings 必须是对象")
        deep_update(existing_mappings, deepcopy(panel_mappings))

    merged: dict[str, Any] = {}
    inline = patch.get("overrides")
    if inline is not None:
        if not isinstance(inline, dict):
            raise ValueError("patch.overrides 必须是对象")
        _merge_legacy_panel_mappings(source=inline, source_name="patch.overrides", target=merged)
        deep_update(merged, deepcopy(inline))
        merged.pop("panel_mappings", None)
    for key in TOP_LEVEL_OVERRIDE_KEYS:
        if key in patch:
            merged[key] = deepcopy(patch[key])
    _merge_legacy_panel_mappings(source=patch, source_name="patch", target=merged)
    return merged


def _base_route_from_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": str(config.get("task", "科研绘图任务")),
        "chart_type": str(config.get("chart_type", "multi")),
        "layout": str(config.get("layout", "")),
        "axis_mode": str(config.get("requested_axis_mode", config.get("axis_mode", "auto"))),
        "library": str(config.get("library", "matplotlib")),
        "style_profile": str(config.get("style_profile", "elsevier")),
        "style_stack": deepcopy(config.get("style_stack", [])),
        "seed": int(config.get("seed", 42)),
        "art_type": str(config.get("art_type", "combo")),
        "dpi": int(config.get("dpi", 0)),
        "multi_order": deepcopy(config.get("multi_order", ["line"])),
    }


def _base_overrides_from_config(config: dict[str, Any]) -> dict[str, Any]:
    base: dict[str, Any] = {}
    for key in TOP_LEVEL_OVERRIDE_KEYS:
        if key in {"extra_config", "multi_order", "dpi"}:
            continue
        if key in config:
            if key == "data_spec" and isinstance(config.get(key), dict) and not bool(config[key].get("enabled", False)):
                continue
            base[key] = deepcopy(config[key])
    return base


def _resolve_backup_path(plot_path: Path, backup_dir: str) -> Path:
    backup_dir_text = str(backup_dir).strip()
    if backup_dir_text:
        root = Path(backup_dir_text).expanduser()
        if not root.is_absolute():
            root = plot_path.parent / root
        root.mkdir(parents=True, exist_ok=True)
        backup_path = root / f"{plot_path.name}.bak"
    else:
        backup_path = plot_path.with_suffix(".py.bak")

    if backup_path.exists():
        idx = 2
        while True:
            if backup_dir_text:
                candidate = backup_path.with_name(f"{plot_path.name}.bak.{idx}")
            else:
                candidate = plot_path.with_suffix(f".py.bak.{idx}")
            if not candidate.exists():
                return candidate
            idx += 1
    return backup_path


def _is_patch_request_empty(*, route_patch: dict[str, Any], override_patch: dict[str, Any]) -> bool:
    return (not bool(route_patch)) and (not bool(override_patch))


def _run_plot_if_needed(
    *,
    run: bool,
    plot_path: Path,
    job_dir: Path,
    output_mode: str,
) -> tuple[bool, str, str, Path | None]:
    if not bool(run):
        return False, "", "", None

    runtime_env = build_runtime_env(job_dir)
    figure_path = job_dir / "figure.png"
    rc, out, err = run_command(
        cmd=[sys.executable, str(plot_path)],
        cwd=job_dir,
        capture=(str(output_mode) == "json"),
        env_extra=runtime_env,
    )
    if rc != 0:
        raise RuntimeError(f"plot.py 执行失败，返回码 {rc}")
    if not figure_path.exists():
        raise FileNotFoundError("plot.py 执行成功但未生成 figure.png")
    return True, out, err, figure_path


def _run_validate_if_needed(
    *,
    validate: bool,
    plot_run_done: bool,
    figure_path: Path | None,
    runtime_config: dict[str, Any],
    job_dir: Path,
    output_mode: str,
    validate_profile: str,
    validate_art_type: str,
) -> tuple[bool, bool | None, str, str]:
    if not bool(validate):
        return False, None, "", ""
    if (not plot_run_done) or figure_path is None or (not figure_path.exists()):
        return True, None, "", ""

    paths = _paths()
    if not paths.validator_path.exists():
        raise FileNotFoundError(f"未找到校验脚本: {paths.validator_path}")

    runtime_env = build_runtime_env(job_dir)
    rc, out, err = run_command(
        cmd=[
            sys.executable,
            str(paths.validator_path),
            str(figure_path),
            "--profile",
            str(validate_profile),
            "--art-type",
            str(validate_art_type),
            "--layout",
            str(runtime_config.get("layout", "single")),
            "--crop-enabled",
            "1" if bool(runtime_config.get("crop_spec", {}).get("enabled", True)) else "0",
        ],
        cwd=job_dir,
        capture=(str(output_mode) == "json"),
        env_extra=runtime_env,
    )
    return True, (rc == 0), out, err


def _build_result_base(mode: str) -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": str(mode),
        "generated_at": _now_iso(),
        "warnings": [],
    }


def run_create(
    *,
    task: str,
    chart_type: str,
    layout: str,
    style_profile: str,
    seed: int,
    overrides: str,
    out_root: str,
    job_name: str,
    axis_mode: str = "auto",
    library: str = "matplotlib",
    style_stack: str = "",
    art_type: str = "combo",
    dpi: int = 0,
    multi_order: str = "line",
    layout_priors: bool = True,
    run: bool = False,
    validate: bool = False,
    validate_profile: str = "",
    validate_art_type: str = "auto",
    output_mode: str = "json",
    template_mode: str = "bundled",
) -> dict[str, Any]:
    t0 = time.perf_counter()
    result = _build_result_base("create")

    route = {
        "task": str(task),
        "chart_type": str(chart_type),
        "layout": str(layout),
        "axis_mode": str(axis_mode),
        "library": str(library),
        "style_profile": str(style_profile),
        "style_stack": str(style_stack),
        "seed": int(seed),
        "art_type": str(art_type),
        "dpi": int(dpi),
        "multi_order": str(multi_order),
    }
    override_patch = load_overrides(str(overrides))

    _compiled_config, runtime_config = _build_compiled_runtime(
        route=route,
        overrides=override_patch,
        use_layout_prior=bool(layout_priors),
    )

    route_key = build_route_key(runtime_config)
    axis_mode_state = resolve_axis_mode_state(runtime_config)

    out_root_path = Path(str(out_root)).expanduser()
    if not out_root_path.is_absolute():
        out_root_path = (Path.cwd() / out_root_path).resolve()
    effective_job_name = str(job_name).strip() or _build_job_name(
        task=str(runtime_config.get("task", task)),
        layout=str(runtime_config.get("layout", layout)),
        chart_type=str(runtime_config.get("chart_type", chart_type)),
    )
    job_dir = _reserve_job_dir(out_root_path, effective_job_name)
    plot_path = job_dir / "plot.py"

    normalized_template_mode = "thin"
    plot_path.write_text(render_thin_plot_script(config=runtime_config, source_template="generated-thin"), encoding="utf-8")
    source_template = "generated-thin"

    did_run, plot_stdout, plot_stderr, figure_path = _run_plot_if_needed(
        run=bool(run),
        plot_path=plot_path,
        job_dir=job_dir,
        output_mode=output_mode,
    )

    effective_validate_profile = str(validate_profile).strip() or map_validate_profile(
        str(runtime_config.get("style_profile", "elsevier"))
    )
    effective_validate_art_type = (
        str(runtime_config.get("art_type", "combo"))
        if str(validate_art_type).strip().lower() == "auto"
        else str(validate_art_type).strip()
    )

    did_validate, validate_passed, validate_stdout, validate_stderr = _run_validate_if_needed(
        validate=bool(validate),
        plot_run_done=did_run,
        figure_path=figure_path,
        runtime_config=runtime_config,
        job_dir=job_dir,
        output_mode=output_mode,
        validate_profile=effective_validate_profile,
        validate_art_type=effective_validate_art_type,
    )

    payload = {
        "schema_version": "2.1",
        "generated_at": _now_iso(),
        "mode": "create",
        "route_key": route_key,
        "job": {
            "dir": str(job_dir),
            "script": str(plot_path),
            "figure": str(figure_path) if figure_path else None,
            "source_template": source_template,
            "template_mode": normalized_template_mode,
        },
        "config": {
            "chart_type": runtime_config.get("chart_type"),
            "layout": runtime_config.get("layout"),
            "axis_mode": axis_mode_state,
            "library": runtime_config.get("library"),
            "style_profile": runtime_config.get("style_profile"),
            "seed": runtime_config.get("seed"),
            "dpi": runtime_config.get("dpi"),
            "runtime_derived": runtime_config.get("runtime_derived", {}),
            "template_mode": normalized_template_mode,
        },
        "render_validation": {
            "enabled": bool(validate),
            "passed": validate_passed,
            "profile": effective_validate_profile,
            "art_type": effective_validate_art_type,
        },
        "metrics": {
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "render_count": int(bool(did_run)),
            "validate_attempted": bool(did_validate),
        },
    }
    report_path = write_orchestrator_report(job_dir=job_dir, payload=payload)

    result.update(
        {
            "job_dir": str(job_dir),
            "plot": str(plot_path),
            "figure": str(figure_path) if figure_path else None,
            "figure_generated": bool(figure_path and figure_path.exists()),
            "template_mode": normalized_template_mode,
            "route_key": route_key,
            "config": payload["config"],
            "report": str(report_path),
            "plot_stdout": plot_stdout,
            "plot_stderr": plot_stderr,
            "validate_stdout": validate_stdout,
            "validate_stderr": validate_stderr,
            "render_validation": payload["render_validation"],
            "metrics": payload["metrics"],
        }
    )
    return result


def run_fast_patch(
    *,
    plot: str,
    patch: str,
    dry_run: bool = False,
    force_patch_l3: bool = False,
    backup: bool = True,
    backup_dir: str = "",
    layout_priors: bool = True,
    run: bool = False,
    validate: bool = False,
    validate_profile: str = "",
    validate_art_type: str = "auto",
    output_mode: str = "json",
) -> dict[str, Any]:
    t0 = time.perf_counter()
    result = _build_result_base("fast_patch")

    plot_path = Path(str(plot)).expanduser().resolve()
    if not plot_path.exists():
        raise FileNotFoundError(f"未找到 plot.py: {plot_path}")

    original_text = plot_path.read_text(encoding="utf-8")
    old_config = _extract_config_from_plot(original_text)
    preserved_ai_zones = _extract_ai_edit_zones(original_text)

    patch_payload = _load_json_object(str(patch))
    route_patch = _extract_route_patch(patch_payload)
    override_patch = _extract_override_patch(patch_payload)
    patch_request_empty = _is_patch_request_empty(route_patch=route_patch, override_patch=override_patch)

    requested_level = str(patch_payload.get("change_level", "auto"))
    change_level = infer_change_level(
        route_patch=route_patch,
        override_patch=override_patch,
        requested_level=requested_level,
        intent_entry=None,
    )
    contract_reason = contract_violation_reason(
        level=change_level,
        route_patch=route_patch,
        override_patch=override_patch,
        route_allow=set(),
        override_allow=set(),
    )
    if contract_reason and change_level != "L3":
        raise ValueError(contract_reason)

    if change_level == "L3" and (not bool(force_patch_l3)):
        result.update(
            {
                "status": "suggest_regenerate",
                "change_level": change_level,
                "reason": "检测到 L3 变更（chart_type/library），建议重新生成。",
            }
        )
        return result

    base_route = _base_route_from_config(old_config)
    new_route = deepcopy(base_route)
    new_route.update(route_patch)
    new_overrides = _base_overrides_from_config(old_config)
    deep_update(new_overrides, deepcopy(override_patch))

    # ---- AI_EDIT_ZONE 注入：从 extra_config 提取 AI_EDIT_ZONE:* 键，注入到 preserved zones ----
    # 这使 patch JSON 中的 extra_config.AI_EDIT_ZONE:pre_draw 能直接覆盖 plot.py 对应区域。
    _extra_cfg = new_overrides.get("extra_config")
    if isinstance(_extra_cfg, dict):
        _zone_prefix = "AI_EDIT_ZONE:"
        _zone_keys = [k for k in list(_extra_cfg.keys()) if str(k).startswith(_zone_prefix)]
        for _k in _zone_keys:
            _zone_name = str(_k)[len(_zone_prefix):]
            _raw = str(_extra_cfg.pop(_k))
            # 规范化缩进：保留相对缩进，统一使用 4 空格前缀（hook 函数体标准缩进）
            _raw_lines = _raw.split("\n")
            _non_empty = [ln for ln in _raw_lines if ln.strip()]
            _min_indent = min((len(ln) - len(ln.lstrip()) for ln in _non_empty), default=0)
            _norm = []
            for _ln in _raw_lines:
                if _zone_name == "imports":
                    _norm.append(_ln[_min_indent:] if _ln.strip() else "")
                else:
                    _norm.append(("    " + _ln[_min_indent:]) if _ln.strip() else "")
            preserved_ai_zones[_zone_name] = "\n".join(_norm) + "\n"
        if not _extra_cfg:
            new_overrides.pop("extra_config", None)

    _compiled_config, runtime_config = _build_compiled_runtime(
        route=new_route,
        overrides=new_overrides,
        use_layout_prior=bool(layout_priors),
    )

    route_key = build_route_key(runtime_config)
    axis_mode_state = resolve_axis_mode_state(runtime_config)

    new_plot_text = render_thin_plot_script(config=runtime_config, source_template="fast_patch-thin")
    new_plot_text = _apply_ai_edit_zones(new_plot_text=new_plot_text, preserved_zones=preserved_ai_zones)

    if bool(dry_run):
        result.update(
            {
                "status": "dry_run",
                "plot": str(plot_path),
                "change_level": change_level,
                "patch_request_empty": patch_request_empty,
                "route_key": route_key,
            }
        )
        return result

    backup_path: Path | None = None
    if bool(backup):
        backup_path = _resolve_backup_path(plot_path=plot_path, backup_dir=str(backup_dir))
        backup_path.write_text(original_text, encoding="utf-8")
    plot_path.write_text(new_plot_text, encoding="utf-8")

    job_dir = plot_path.parent

    did_run, plot_stdout, plot_stderr, figure_path = _run_plot_if_needed(
        run=bool(run),
        plot_path=plot_path,
        job_dir=job_dir,
        output_mode=output_mode,
    )

    effective_validate_profile = str(validate_profile).strip() or map_validate_profile(
        str(runtime_config.get("style_profile", "elsevier"))
    )
    effective_validate_art_type = (
        str(runtime_config.get("art_type", "combo"))
        if str(validate_art_type).strip().lower() == "auto"
        else str(validate_art_type).strip()
    )

    did_validate, validate_passed, validate_stdout, validate_stderr = _run_validate_if_needed(
        validate=bool(validate),
        plot_run_done=did_run,
        figure_path=figure_path,
        runtime_config=runtime_config,
        job_dir=job_dir,
        output_mode=output_mode,
        validate_profile=effective_validate_profile,
        validate_art_type=effective_validate_art_type,
    )

    payload = {
        "schema_version": "2.1",
        "generated_at": _now_iso(),
        "mode": "fast_patch",
        "patch_request_empty": patch_request_empty,
        "route_key": route_key,
        "patch": {
            "change_level": change_level,
            "route_patch": route_patch,
            "override_patch_keys": sorted(override_patch.keys()),
        },
        "job": {
            "dir": str(job_dir),
            "script": str(plot_path),
            "backup": str(backup_path) if backup_path is not None else None,
            "figure": str(figure_path) if figure_path else None,
            "source_template": "fast_patch-thin",
            "template_mode": "thin",
        },
        "config": {
            "chart_type": runtime_config.get("chart_type"),
            "layout": runtime_config.get("layout"),
            "axis_mode": axis_mode_state,
            "library": runtime_config.get("library"),
            "style_profile": runtime_config.get("style_profile"),
            "seed": runtime_config.get("seed"),
            "dpi": runtime_config.get("dpi"),
            "runtime_derived": runtime_config.get("runtime_derived", {}),
        },
        "render_validation": {
            "enabled": bool(validate),
            "passed": validate_passed,
            "profile": effective_validate_profile,
            "art_type": effective_validate_art_type,
        },
        "metrics": {
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "render_count": int(bool(did_run)),
            "validate_attempted": bool(did_validate),
        },
    }
    report_path = write_orchestrator_report(job_dir=job_dir, payload=payload)

    result.update(
        {
            "plot": str(plot_path),
            "backup": str(backup_path) if backup_path is not None else None,
            "figure": str(figure_path) if figure_path else None,
            "figure_generated": bool(figure_path and figure_path.exists()),
            "change_level": change_level,
            "route_key": route_key,
            "patch_request_empty": patch_request_empty,
            "config": payload["config"],
            "report": str(report_path),
            "plot_stdout": plot_stdout,
            "plot_stderr": plot_stderr,
            "validate_stdout": validate_stdout,
            "validate_stderr": validate_stderr,
            "render_validation": payload["render_validation"],
            "metrics": payload["metrics"],
        }
    )
    return result


def run(mode: str, **kwargs: Any) -> dict[str, Any]:
    key = str(mode).strip().lower()
    if key == "create":
        return run_create(**kwargs)
    if key == "fast_patch":
        return run_fast_patch(**kwargs)
    raise ValueError(f"unsupported mode: {mode}")


__all__ = [
    "run",
    "run_create",
    "run_fast_patch",
]
