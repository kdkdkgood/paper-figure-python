---
path: anti://layout/shrink-main-area-for-colorbar
scope: global
type: anti
status: active
weight: 0.80
hits: 0
misses: 0
trigger: 需要给 colorbar/图例/右侧标签让出空间
hook: ❌ 不要压缩主图给 colorbar/图例让位；先扩画布
created: 2026-06-22
updated: 2026-06-22
last_hit: 2026-06-22
evidence_count: 1
superseded_by: 
---

# 禁忌：压缩主图给 colorbar/图例让位

## Baseline（默认做法）
空间不够时，本能反应是缩小主 axes 或 `subplots_adjust` 压主图来塞下 colorbar/图例。

## Deviation（关键发现）
这会牺牲数据可读性，与"保护主图数据区"的核心原则冲突。守卫体系本就提供扩画布的正路。

## Result（可验证结果）
压缩主图换来的"塞下"通常被老板否决；扩画布或挪图例才是被接受的版本。

## Reusable Rule（祈使句，可直接落地）
不要为容纳 colorbar/图例而压缩主图。改用 `layout_guard_spec.intent="preserve_data"` / `roomy`、扩 `width_mm`、或把图例外置。正向修法见 [[fix://layout/colorbar-clipped-right]]。

## Evidence（证据来源）
- 2026-06-22 · 种子经验 · 来自 SKILL.md 参数语义「优先保护主图区，不要直接关闭守卫」。
