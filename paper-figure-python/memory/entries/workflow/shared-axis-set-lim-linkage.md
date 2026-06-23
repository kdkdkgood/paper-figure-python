---
path: workflow://shared-axis/set-lim-linkage
scope: global
type: workflow
status: active
weight: 0.85
hits: 1
misses: 0
trigger: shared_axis 模式下调单个面板的 xlim/ylim，或抱怨其他面板范围跟着变
hook: sharex 下 set_xlim 联动整列、sharey 下 set_ylim 联动整行，这是预期行为；要独立范围先切 independent
created: 2026-06-22
updated: 2026-06-22
last_hit: 2026-06-22
evidence_count: 1
superseded_by: 
---

# shared_axis 下 set_xlim/set_ylim 联动是预期行为

## Baseline（默认做法）
用户（或 AI）在 shared_axis 模式下对单个面板调 `set_xlim`/`set_ylim`，预期仅影响当前面板。

## Deviation（关键发现）
matplotlib 的 `sharex`/`sharey` 原生联动是**预期行为**而非 bug。`set_xlim()` 在 `sharex` 下联动整列；`set_ylim()` 在 `sharey` 下联动整行。

## Result（可验证结果）
确认这是 matplotlib 的默认语义，不是本 skill 或 runtime 的 bug。

## Reusable Rule（祈使句，可直接落地）
如是预期行为直接告诉用户"这是正确的"；若用户确实需要独立范围，把 `axis_mode` 改为 `independent`（或走 patch `route.axis_mode=independent`）。

## Evidence（证据来源）
- 2026-06-22 · 种子经验 · 来自 SKILL.md「共享轴模式」段落。
