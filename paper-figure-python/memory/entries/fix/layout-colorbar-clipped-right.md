---
path: fix://layout/colorbar-clipped-right
scope: global
type: fix
status: active
weight: 0.85
hits: 0
misses: 0
trigger: 图含 colorbar，且右侧标签/色条/裁边溢出
hook: 先扩 layout_spec.width_mm 与 crop_spec.padding_px，不要压缩主图
created: 2026-06-22
updated: 2026-06-22
last_hit: 2026-06-22
evidence_count: 1
superseded_by: 
---

# Colorbar 右侧裁切的稳定修法

## Baseline（默认做法）
容易只调 `bbox_inches` / `tight_layout()` / 压缩 axes 把 colorbar 塞进去。

## Deviation（关键发现）
应优先用 `layout_spec.width_mm`、`crop_spec.padding_px`、`layout_guard_spec.intent="preserve_data"` 表达意图，让守卫预留空间而非牺牲主图。

## Result（可验证结果）
右侧标签完整保留，主图数据区不被明显压缩。终版 `render_validation.passed=true`。

## Reusable Rule（祈使句，可直接落地）
遇 colorbar/右侧标签被裁：先扩画布与裁切 padding；仅当用户明确要紧凑时，才缩短 label 或缩小 colorbar。

## Evidence（证据来源）
- 2026-06-22 · 种子经验 · 来自 SKILL.md「常见问题」与 layout_guard_spec 语义。参见 [[anti://layout/shrink-main-area-for-colorbar]]。
