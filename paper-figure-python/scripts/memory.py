#!/usr/bin/env python3
"""paper-figure-python 经验成长系统 · 轻量文件级记忆层。

按 v3 方案实现的旁路 CLI：boot/recall/remember/reinforce/suggest/audit/promote。

设计契约（务必保持）：
- 旁路降级：所有命令对外永不抛异常到绘图主链。失败时打印告警 + 返回空/降级结果。
- 零依赖：仅用标准库；不引入数据库、网络、第三方包。
- 不污染：写回严格限定 memory/ 与项目层 .paper-figure-memory/，绝不碰任务 output/。
- INDEX.md 是 entry frontmatter 的派生缓存，可随时由 audit --rebuild-index 重建。

记忆根探测顺序：
  env PAPER_FIGURE_MEMORY_ROOT  →  <SKILL_ROOT>/memory  →  ~/.paper-figure-memory（只读回退）
项目层固定在 <WORKSPACE>/.paper-figure-memory/。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# 默认参数（与 v3 §10 对齐）
# ---------------------------------------------------------------------------
BOOT_MAX_LINES = 10
RECALL_DEFAULT_LIMIT = 5
HEAVY_READ_WEIGHT = 0.8          # eff_weight ≥ 此值建议读正文
RELEVANCE_HIGH = 3.0             # match_score ≥ 此值视为强关联
RELEVANCE_MEDIUM = 1.5           # ≥ 此值视为部分关联，低于则视为弱关联
WRITE_SCORE_THRESHOLD = 3
SUGGEST_ITER_ROUNDS = 3  # patch + run 总迭代轮数 ≥ 此值即视为收敛证据
ENTRY_SOFT_CAP = 30
INBOX_SOFT_CAP = 20
WEIGHT_UP_STEP = 0.03
WEIGHT_UP_CAP = 0.98
WEIGHT_DOWN_STEP = 0.05
WEIGHT_DOWN_FLOOR = 0.10
DECAY_WINDOW_DAYS = 180

ENTRY_TYPES = ("pref", "fix", "pattern", "palette", "workflow", "anti")
TODAY = date.today().isoformat()

# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------


def _warn(msg: str) -> None:
    print(f"[memory] 告警: {msg}", file=sys.stderr)


def _skill_root() -> Path:
    """定位 SKILL_ROOT，跨机器/跨 OS 可移植，零配置。

    优先级：env PAPER_FIGURE_SKILL_ROOT（与 plot.py 同一约定）→ 由 __file__ 反推
    （memory.py 位于 <SKILL_ROOT>/scripts/memory.py）。后者对任何安装位都成立，
    无论 Windows 还是 macOS、无论装在 ~/.claude/skills 还是 ~/.kiro/skills。
    """
    env = os.environ.get("PAPER_FIGURE_SKILL_ROOT")
    if env:
        base = Path(env).expanduser()
        # 允许 env 指向 skill 根或其 scripts 目录
        if (base / "scripts" / "memory.py").is_file():
            return base
        if base.name == "scripts" and (base / "memory.py").is_file():
            return base.parent
    return Path(__file__).resolve().parent.parent


def _global_root() -> Path:
    env = os.environ.get("PAPER_FIGURE_MEMORY_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    candidate = _skill_root() / "memory"
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return candidate
    except OSError:
        # SKILL_ROOT 只读 → 回退用户目录
        fallback = Path.home() / ".paper-figure-memory"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _project_root(workspace: str | None) -> Path | None:
    if not workspace:
        return None
    ws = Path(workspace).expanduser().resolve()
    return ws / ".paper-figure-memory"


def _ensure_layout(root: Path) -> None:
    for t in ENTRY_TYPES:
        (root / "entries" / t).mkdir(parents=True, exist_ok=True)
    (root / "inbox").mkdir(parents=True, exist_ok=True)
    (root / "archive").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# frontmatter 解析（极简 YAML 子集：key: value，不引入 pyyaml）
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def _parse_entry(path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FM_RE.match(text)
    if not m:
        return None
    meta: dict[str, Any] = {}
    for line in m.group(1).splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip()
    meta["_body"] = m.group(2)
    meta["_file"] = path
    return meta


def _coerce_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _coerce_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _iter_entries(root: Path) -> Iterable[dict[str, Any]]:
    edir = root / "entries"
    if not edir.exists():
        return
    for p in sorted(edir.rglob("*.md")):
        meta = _parse_entry(p)
        if meta and meta.get("path"):
            yield meta


# ---------------------------------------------------------------------------
# 衰减与召回评分（v3 §5.2 / §5.4）
# ---------------------------------------------------------------------------


def _age_days(meta: dict[str, Any]) -> int:
    stamp = meta.get("last_hit") or meta.get("updated") or meta.get("created")
    if not stamp:
        return 0
    try:
        d = datetime.strptime(str(stamp), "%Y-%m-%d").date()
    except ValueError:
        return 0
    return max(0, (date.today() - d).days)


def _decay(meta: dict[str, Any]) -> float:
    age = _age_days(meta)
    hits = _coerce_int(meta.get("hits"))
    val = (1.0 - age / DECAY_WINDOW_DAYS) + 0.05 * hits
    return max(0.3, min(1.0, val))


def _eff_weight(meta: dict[str, Any]) -> float:
    return round(_coerce_float(meta.get("weight"), 0.5) * _decay(meta), 4)


_TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_./-]+|[一-鿿]+")


def _tokens(text: str) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    for tok in _TOKEN_RE.findall(text.lower()):
        out.append(tok)
        # 中文按 2-gram 切，提升关键词召回
        if re.fullmatch(r"[一-鿿]+", tok) and len(tok) >= 2:
            out.extend(tok[i : i + 2] for i in range(len(tok) - 1))
    return out


def _match_score(meta: dict[str, Any], ctx_tokens: set[str], scope: str) -> float:
    trig = set(_tokens(meta.get("trigger", "")))
    pathk = set(_tokens(meta.get("path", "")))
    hookk = set(_tokens(meta.get("hook", "")))
    score = (
        len(trig & ctx_tokens) * 2
        + len(pathk & ctx_tokens)
        + len(hookk & ctx_tokens)
        + _eff_weight(meta)
    )
    if scope == "project":
        score += 1.0  # 项目层加成
    if meta.get("type") == "anti" and (trig & ctx_tokens):
        score += 0.5  # 负经验命中时前置
    return round(score, 4)


def _relevance_label(score: float) -> str:
    """把 match_score 映射为关联度档位，供 AI 快速判断是否采纳。"""
    if score >= RELEVANCE_HIGH:
        return "high"
    if score >= RELEVANCE_MEDIUM:
        return "medium"
    return "low"


# 各档位对应的 recall 提示语，随 top-1 关联度动态切换
_QUALITY_HINT = {
    "high": "当前场景有强匹配经验，优先按 hook 决策；高风险/冲突时再读 entry 正文。",
    "medium": "有部分关联经验，结合实际情况判断是否采纳，谨慎对待低 relevance 条目。",
    "low": "无高置信度匹配，当前上下文与已有经验关联弱，按 SKILL.md 默认规则出图即可。",
}


# ---------------------------------------------------------------------------
# 命令：boot / recall
# ---------------------------------------------------------------------------


def _read_boot(root: Path) -> list[str]:
    f = root / "BOOT.md"
    if not f.exists():
        return []
    lines = [
        ln[2:].strip()
        for ln in f.read_text(encoding="utf-8").splitlines()
        if ln.startswith("- ")
    ]
    return lines


def cmd_root(args: argparse.Namespace) -> dict[str, Any]:
    """打印自身定位的路径，供文档/调用方零配置自举（跨机器自描述）。"""
    g = _global_root()
    out = {
        "skill_root": str(_skill_root()),
        "memory_root": str(g),
        "memory_py": str(Path(__file__).resolve()),
    }
    proj = _project_root(args.workspace)
    if proj is not None:
        out["project_memory_root"] = str(proj)
    return out


def cmd_boot(args: argparse.Namespace) -> dict[str, Any]:
    g = _global_root()
    boot = _read_boot(g)
    proj_root = _project_root(args.workspace)
    if proj_root and proj_root.exists():
        boot += _read_boot(proj_root)
    if len(boot) > BOOT_MAX_LINES:
        _warn(f"BOOT 条目 {len(boot)} 超过上限 {BOOT_MAX_LINES}，建议 audit promote_to_boot 精简")
    return {"boot": boot}


def cmd_recall(args: argparse.Namespace) -> dict[str, Any]:
    ctx_tokens = set(_tokens(args.context or ""))
    g = _global_root()
    result: dict[str, Any] = {"boot": _read_boot(g), "matches": []}

    pools: list[tuple[str, Path]] = [("global", g)]
    proj_root = _project_root(args.workspace)
    if proj_root and proj_root.exists():
        result["boot"] += _read_boot(proj_root)
        pools.append(("project", proj_root))

    scored: list[tuple[float, dict[str, Any]]] = []
    for scope, root in pools:
        for meta in _iter_entries(root):
            if meta.get("status", "active") != "active":
                continue
            s = _match_score(meta, ctx_tokens, scope)
            eff = _eff_weight(meta)
            entry_rel = str(meta["_file"].relative_to(root))
            scored.append(
                (
                    s,
                    {
                        "path": meta.get("path"),
                        "scope": scope,
                        "kind": meta.get("type"),
                        "trigger": meta.get("trigger", ""),
                        "hook": meta.get("hook", ""),
                        "eff_weight": eff,
                        "relevance": _relevance_label(s),
                        "heavy_read": eff >= HEAVY_READ_WEIGHT,
                        "entry": entry_rel,
                    },
                )
            )

    # 项目层同分排前：稳定排序键（score desc, project-first, eff desc）
    scored.sort(key=lambda x: (x[0], x[1]["scope"] == "project", x[1]["eff_weight"]), reverse=True)
    result["matches"] = [m for _, m in scored[: args.limit]]

    # 关联度汇总：以 top-1 score 判档，引导 AI 在弱关联时直接走默认规则
    quality = _relevance_label(scored[0][0]) if scored else "low"
    result["quality"] = quality
    result["quality_note"] = _QUALITY_HINT[quality]
    result["hint"] = _QUALITY_HINT[quality]
    return result


# ---------------------------------------------------------------------------
# 命令：remember（新建/更新 + 同步 INDEX）
# ---------------------------------------------------------------------------


def _path_to_relfile(uri: str) -> Path:
    # 形如 fix://layout/colorbar-clipped-right →  entries/fix/layout-colorbar-clipped-right.md
    m = re.match(r"^([a-z]+)://(.+)$", uri)
    if not m:
        raise ValueError(f"非法 path URI: {uri}")
    kind, rest = m.group(1), m.group(2)
    if kind not in ENTRY_TYPES:
        raise ValueError(f"未知记忆类型: {kind}")
    slug = rest.replace("/", "-")
    return Path("entries") / kind / f"{slug}.md"


def _find_entry_by_path(root: Path, uri: str) -> Path | None:
    for meta in _iter_entries(root):
        if meta.get("path") == uri:
            return meta["_file"]
    return None


def _render_entry(meta: dict[str, Any], body: str) -> str:
    order = [
        "path", "scope", "type", "status", "weight", "hits", "misses",
        "trigger", "hook", "created", "updated", "last_hit",
        "evidence_count", "superseded_by",
    ]
    lines = ["---"]
    for k in order:
        if k in meta and meta[k] is not None:
            lines.append(f"{k}: {meta[k]}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip("\n")


def cmd_remember(args: argparse.Namespace) -> dict[str, Any]:
    root = _global_root() if args.scope == "global" else _project_root(args.workspace)
    if root is None:
        raise ValueError("scope=project 需要 --workspace")
    _ensure_layout(root)

    body = ""
    if args.body_file:
        body = Path(args.body_file).expanduser().read_text(encoding="utf-8")
    elif args.body:
        body = args.body

    existing = _find_entry_by_path(root, args.path)
    kind = re.match(r"^([a-z]+)://", args.path).group(1)

    if existing:  # 更新：默认 append 不覆盖正文
        meta = _parse_entry(existing) or {}
        old_body = meta.pop("_body", "")
        meta.pop("_file", None)
        if args.trigger:
            meta["trigger"] = args.trigger
        if args.hook:
            meta["hook"] = args.hook
        if args.weight is not None:
            meta["weight"] = args.weight
        if args.status:
            meta["status"] = args.status
        if args.superseded_by:
            meta["superseded_by"] = args.superseded_by
        meta["updated"] = TODAY
        meta["evidence_count"] = _coerce_int(meta.get("evidence_count")) + (1 if body else 0)
        new_body = old_body.rstrip()
        if body:
            new_body += f"\n\n## 更新 {TODAY}\n\n{body.strip()}\n"
        existing.write_text(_render_entry(meta, new_body), encoding="utf-8")
        action = "updated"
        target = existing
    else:  # 新建
        meta = {
            "path": args.path,
            "scope": args.scope,
            "type": kind,
            "status": args.status or "active",
            "weight": args.weight if args.weight is not None else 0.7,
            "hits": 0,
            "misses": 0,
            "trigger": args.trigger or "",
            "hook": args.hook or "",
            "created": TODAY,
            "updated": TODAY,
            "last_hit": TODAY,
            "evidence_count": 1 if body else 0,
            "superseded_by": args.superseded_by or "",
        }
        target = root / _path_to_relfile(args.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render_entry(meta, body or f"# {args.path}\n"), encoding="utf-8")
        action = "created"

    _rebuild_index(root)
    return {"action": action, "entry": str(target.relative_to(root)), "scope": args.scope}


# ---------------------------------------------------------------------------
# 命令：reinforce（强化回路 · v3 灵魂）
# ---------------------------------------------------------------------------


def _adjust_entry(root: Path, uri: str, adopted: bool) -> dict[str, Any] | None:
    f = _find_entry_by_path(root, uri)
    if f is None:
        return None
    meta = _parse_entry(f)
    if meta is None:
        return None
    body = meta.pop("_body", "")
    meta.pop("_file", None)
    w = _coerce_float(meta.get("weight"), 0.7)
    if adopted:
        meta["hits"] = _coerce_int(meta.get("hits")) + 1
        meta["last_hit"] = TODAY
        meta["weight"] = round(min(WEIGHT_UP_CAP, w + WEIGHT_UP_STEP), 4)
    else:
        meta["misses"] = _coerce_int(meta.get("misses")) + 1
        meta["weight"] = round(max(WEIGHT_DOWN_FLOOR, w - WEIGHT_DOWN_STEP), 4)
    meta["updated"] = TODAY
    f.write_text(_render_entry(meta, body), encoding="utf-8")
    return {"path": uri, "weight": meta["weight"], "hits": meta.get("hits"), "misses": meta.get("misses")}


def cmd_reinforce(args: argparse.Namespace) -> dict[str, Any]:
    roots = [_global_root()]
    proj = _project_root(args.workspace)
    if proj and proj.exists():
        roots.append(proj)

    changed: list[dict[str, Any]] = []
    for uri in (args.adopted or []):
        for r in roots:
            res = _adjust_entry(r, uri, adopted=True)
            if res:
                changed.append({**res, "effect": "adopted"})
                break
    for uri in (args.rejected or []):
        for r in roots:
            res = _adjust_entry(r, uri, adopted=False)
            if res:
                changed.append({**res, "effect": "rejected"})
                break
    for r in roots:
        _rebuild_index(r)
    return {"changed": changed}


# ---------------------------------------------------------------------------
# 命令：suggest（证据驱动候选 · 对比首版↔终版 config · v3 §4.2）
# ---------------------------------------------------------------------------

_REPORT_HISTORY_DIR = "orchestrator_reports"


def _load_reports(job_dir: Path) -> list[dict[str, Any]]:
    hist = job_dir / _REPORT_HISTORY_DIR
    files: list[Path] = []
    if hist.exists():
        files = sorted(hist.glob("*.json"))
    canonical = job_dir / "orchestrator_report.json"
    if not files and canonical.exists():
        files = [canonical]
    reports: list[dict[str, Any]] = []
    for f in files:
        try:
            reports.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return reports


def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in (d or {}).items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, f"{key}."))
        else:
            out[key] = v
    return out


def cmd_suggest(args: argparse.Namespace) -> dict[str, Any]:
    job_dir = Path(args.job_dir).expanduser().resolve()
    reports = _load_reports(job_dir)
    if not reports:
        return {"candidates": [], "note": "无 orchestrator_reports，跳过"}

    creates = [r for r in reports if r.get("mode") == "create"]
    patches = [r for r in reports if r.get("mode") == "fast_patch"]
    runs = [r for r in reports if r.get("mode") == "run"]
    rendered_ok = [r for r in reports if r.get("render_validation", {}).get("passed")]
    final = rendered_ok[-1] if rendered_ok else reports[-1]
    first = creates[0] if creates else reports[0]

    # 首版渲染↔终版渲染 config diff。
    # 注意：create report 的 config 由 service 构建（axis_mode 是嵌套 state dict），
    # run report 的 config 由 engine 构建（axis_mode 是解析后的字符串）——二者 schema
    # 不同构，直接相比会产生大量假 delta。故 diff 只在“同构的渲染报告”之间做：
    # 优先取首个 run/patch 作为“首版渲染”基线，create 仅在无任何渲染时兜底。
    iter_reports = [r for r in reports if r.get("mode") in ("run", "fast_patch")]
    delta_first = iter_reports[0] if iter_reports else first
    first_cfg = _flatten(delta_first.get("config", {}))
    final_cfg = _flatten(final.get("config", {}))
    config_delta = {
        k: [first_cfg.get(k), final_cfg.get(k)]
        for k in set(first_cfg) | set(final_cfg)
        if first_cfg.get(k) != final_cfg.get(k)
    }

    # AI_EDIT_ZONE 代码演变：对比首条↔末条带哈希的 run report
    # （仅当两端都有哈希且不同才判定——缺哈希一律视作"未知，不主张演变"）
    hashed = [r for r in reports if r.get("ai_edit_zone_hash")]
    zone_evolved = (
        len(hashed) >= 2
        and hashed[0].get("ai_edit_zone_hash") != hashed[-1].get("ai_edit_zone_hash")
    )

    # override_patch_keys 频次 = 用户反复纠结的维度
    key_freq: dict[str, int] = {}
    for r in patches:
        for k in r.get("patch", {}).get("override_patch_keys", []):
            key_freq[k] = key_freq.get(k, 0) + 1
    hot_keys = sorted(key_freq.items(), key=lambda kv: kv[1], reverse=True)

    n_patch = len(patches)
    n_run = len(runs)
    total_iter = n_patch + n_run  # Edit→Run 与 patch 同等计入迭代轮数
    converged = total_iter >= SUGGEST_ITER_ROUNDS and bool(rendered_ok)

    candidates: list[dict[str, Any]] = []
    if config_delta or hot_keys or zone_evolved:
        signal_bits = []
        if hot_keys:
            signal_bits.append(
                "反复调整 " + ", ".join(f"{k}×{v}" for k, v in hot_keys[:3])
            )
        if zone_evolved:
            signal_bits.append(
                f"AI_EDIT_ZONE 代码经 {total_iter} 轮迭代有实质演变（自定义图型技巧）"
            )
        if converged:
            signal_bits.append(f"{total_iter} 轮迭代后收敛且 render 通过")
        # 代码演变型候选指向 pattern 命名空间，CONFIG 型指向 pref
        path_hint = "pattern://custom/<待命名>" if zone_evolved and not config_delta else "pref://boss/style/<待命名>"
        draft_hook = (
            "把本次 AI_EDIT_ZONE 的自定义绘图技巧提炼为可复用 pattern（含适用图型与关键代码骨架）"
            if zone_evolved and not config_delta
            else "把上述 config_delta 提炼为'首版即到位'的祈使句规则"
        )
        candidates.append(
            {
                "kind": "candidate",
                "job": str(job_dir.name),
                "path_hint": path_hint,
                "scope_hint": "global",
                "signal": "；".join(signal_bits) or "首版与终版 config 存在实质差异",
                "config_delta": config_delta,
                "hot_override_keys": dict(hot_keys),
                "zone_evolved": zone_evolved,
                "draft_hook": draft_hook,
                "confidence": round(min(0.9, 0.4 + 0.1 * total_iter), 2),
                "created": TODAY,
            }
        )

    # 写入 inbox（不进正式经验）
    if candidates and not args.dry_run:
        root = _global_root() if args.scope == "global" else (_project_root(args.workspace) or _global_root())
        _ensure_layout(root)
        inbox = root / "inbox" / "candidates.jsonl"
        with inbox.open("a", encoding="utf-8") as fh:
            for c in candidates:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")

    return {
        "candidates": candidates,
        "stats": {
            "creates": len(creates),
            "patches": n_patch,
            "runs": n_run,
            "zone_evolved": zone_evolved,
            "converged": converged,
        },
    }


# ---------------------------------------------------------------------------
# 命令：audit（重复/冲突/陈旧/孤儿/超长 BOOT · 只建议）
# ---------------------------------------------------------------------------


def _rebuild_index(root: Path) -> None:
    rows = []
    for meta in _iter_entries(root):
        rows.append(
            (
                meta.get("path", ""),
                meta.get("scope", "global"),
                meta.get("trigger", "").replace("|", "/"),
                meta.get("hook", "").replace("|", "/"),
                f"{_coerce_float(meta.get('weight'), 0.5):.2f}",
                meta.get("status", "active"),
                str(meta["_file"].relative_to(root)),
            )
        )
    rows.sort(key=lambda r: r[0])
    out = [
        "<!-- AUTO-GENERATED by memory.py · 请勿手改本表，改 entry frontmatter 后跑 `memory.py audit --rebuild-index` -->",
        f"<!-- meta: total={len(rows)} last_audit={TODAY} -->",
        "",
        "# Paper Figure Memory Index",
        "",
        "| path | scope | trigger | hook | weight | status | entry |",
        "|---|---|---|---|---:|---|---|",
    ]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    (root / "INDEX.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def cmd_audit(args: argparse.Namespace) -> dict[str, Any]:
    root = _global_root()
    if args.rebuild_index:
        _rebuild_index(root)
        proj = _project_root(args.workspace)
        if proj and proj.exists():
            _rebuild_index(proj)
        return {"rebuilt": True}

    metas = list(_iter_entries(root))
    findings: dict[str, list[Any]] = {
        "duplicate_trigger": [],
        "stale": [],
        "orphan_deprecated_in_index": [],
        "boot_overlong": [],
        "over_cap": [],
        "inbox_overflow": [],
    }

    # 重复 trigger/hook（高 token 重叠）
    for i in range(len(metas)):
        for j in range(i + 1, len(metas)):
            a, b = metas[i], metas[j]
            ta = set(_tokens(a.get("trigger", "")))
            tb = set(_tokens(b.get("trigger", "")))
            if ta and tb and len(ta & tb) / max(1, min(len(ta), len(tb))) >= 0.6:
                findings["duplicate_trigger"].append([a.get("path"), b.get("path")])

    # 陈旧（eff_weight < 0.4）
    for m in metas:
        if m.get("status", "active") == "active" and _eff_weight(m) < 0.4:
            findings["stale"].append({"path": m.get("path"), "eff_weight": _eff_weight(m)})
        if m.get("status") == "deprecated":
            findings["orphan_deprecated_in_index"].append(m.get("path"))

    boot = _read_boot(root)
    if len(boot) > BOOT_MAX_LINES:
        findings["boot_overlong"] = [len(boot), BOOT_MAX_LINES]

    active = [m for m in metas if m.get("status", "active") == "active"]
    if len(active) > ENTRY_SOFT_CAP:
        findings["over_cap"] = [len(active), ENTRY_SOFT_CAP]

    inbox = root / "inbox" / "candidates.jsonl"
    if inbox.exists():
        n = sum(1 for _ in inbox.open(encoding="utf-8"))
        if n > INBOX_SOFT_CAP:
            findings["inbox_overflow"] = [n, INBOX_SOFT_CAP]

    findings = {k: v for k, v in findings.items() if v}
    _rebuild_index(root)
    return {
        "findings": findings,
        "note": "audit 只建议；merge/distill/deprecate/archive 等破坏性操作须先报告原因、老板确认后由 AI 执行。",
    }


# ---------------------------------------------------------------------------
# 命令：promote（inbox 候选 → 正式 entry）
# ---------------------------------------------------------------------------


def cmd_promote(args: argparse.Namespace) -> dict[str, Any]:
    # promote 要求 AI 已把候选补齐为五段式正文，再走 remember；这里仅做候选出列。
    root = _global_root() if args.scope == "global" else (_project_root(args.workspace) or _global_root())
    inbox = root / "inbox" / "candidates.jsonl"
    if not inbox.exists():
        return {"promoted": None, "note": "inbox 为空"}
    lines = [ln for ln in inbox.read_text(encoding="utf-8").splitlines() if ln.strip()]
    kept, picked = [], None
    for ln in lines:
        try:
            c = json.loads(ln)
        except json.JSONDecodeError:
            kept.append(ln)
            continue
        if picked is None and (args.candidate_id in (c.get("job"), c.get("path_hint"))):
            picked = c
        else:
            kept.append(ln)
    if picked is None:
        return {"promoted": None, "note": f"未找到候选 {args.candidate_id}"}
    inbox.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return {
        "promoted": picked,
        "next": "请用补齐的五段式正文调用 remember 写入正式 entry；项目层→全局层须在正文写明升级理由。",
    }


def cmd_baseline(args: argparse.Namespace) -> dict[str, Any]:
    """共享底座完整性基线：--refresh 重建基线，否则仅校验当前底座是否漂移。

    用于 skill-integrity 护栏：scripts/runtime/ 与 orchestrator/core.py 是跨 job
    共享底座，故意升级后用 --refresh 刷新基线；平时 baseline（无参）即校验。
    """
    from runtime import integrity

    if args.refresh:
        payload = integrity.write_baseline()
        return {
            "action": "refreshed",
            "baseline": str(integrity.baseline_path()),
            "protected_files": payload["protected_files"],
            "note": "基线已锁定当前底座；后续出图若检测到偏离将打印警告。",
        }
    result = integrity.check_integrity()
    warning = integrity.format_warning(result)
    if warning:
        sys.stderr.write(warning + "\n")
    return {
        "action": "checked",
        "status": result["status"],
        "drift": result["drift"],
        "note": {
            "no_baseline": "尚无基线，运行 baseline --refresh 建立。",
            "ok": "底座与基线一致。",
            "drift": "底座已偏离基线：误改请改回 plot.py，故意升级请 --refresh。",
        }.get(result["status"], ""),
    }


# ---------------------------------------------------------------------------
# 入口（旁路降级：任何异常都不抛到绘图主链）
# ---------------------------------------------------------------------------

_SAFE_EMPTY = {
    "root": {},
    "boot": {"boot": []},
    "recall": {"boot": [], "matches": []},
    "remember": {"action": "skipped"},
    "reinforce": {"changed": []},
    "suggest": {"candidates": []},
    "audit": {"findings": {}},
    "promote": {"promoted": None},
    "baseline": {"action": "skipped"},
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="memory.py", description="paper-figure-python 经验成长系统")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_ws(p):
        p.add_argument("--workspace", default=None, help="workspace 根目录（启用项目层）")

    p = sub.add_parser("root"); add_ws(p)

    p = sub.add_parser("boot"); add_ws(p)

    p = sub.add_parser("recall"); add_ws(p)
    p.add_argument("--context", default="", help="任务摘要文本")
    p.add_argument("--limit", type=int, default=RECALL_DEFAULT_LIMIT)

    p = sub.add_parser("remember"); add_ws(p)
    p.add_argument("--scope", choices=("global", "project"), default="global")
    p.add_argument("--path", required=True)
    p.add_argument("--trigger", default="")
    p.add_argument("--hook", default="")
    p.add_argument("--weight", type=float, default=None)
    p.add_argument("--status", default="")
    p.add_argument("--superseded-by", dest="superseded_by", default="")
    p.add_argument("--body", default="")
    p.add_argument("--body-file", dest="body_file", default="")

    p = sub.add_parser("reinforce"); add_ws(p)
    p.add_argument("--adopted", nargs="*", default=[], help="被采纳的经验 path（可多个）")
    p.add_argument("--rejected", nargs="*", default=[], help="被推翻的经验 path（可多个）")

    p = sub.add_parser("suggest"); add_ws(p)
    p.add_argument("--job-dir", dest="job_dir", required=True)
    p.add_argument("--scope", choices=("global", "project"), default="global")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("audit"); add_ws(p)
    p.add_argument("--rebuild-index", action="store_true", help="仅由 entry frontmatter 重建 INDEX.md")

    p = sub.add_parser("promote"); add_ws(p)
    p.add_argument("--candidate-id", dest="candidate_id", required=True, help="候选的 job 名或 path_hint")
    p.add_argument("--scope", choices=("global", "project"), default="global")

    p = sub.add_parser("baseline"); add_ws(p)
    p.add_argument("--refresh", action="store_true", help="重建底座完整性基线（故意升级 runtime 后调用）")

    args = parser.parse_args(argv)
    handler = {
        "root": cmd_root, "boot": cmd_boot, "recall": cmd_recall, "remember": cmd_remember,
        "reinforce": cmd_reinforce, "suggest": cmd_suggest, "audit": cmd_audit,
        "promote": cmd_promote, "baseline": cmd_baseline,
    }[args.cmd]

    try:
        result = handler(args)
    except Exception as exc:  # 旁路契约：永不让记忆故障影响出图主链
        _warn(f"{args.cmd} 失败，已降级：{exc}")
        result = _SAFE_EMPTY.get(args.cmd, {})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
