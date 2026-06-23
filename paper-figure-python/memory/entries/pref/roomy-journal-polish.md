---
path: pref://boss/style/roomy-journal-polish
scope: global
type: pref
status: active
weight: 0.75
hits: 0
misses: 0
trigger: 老板说"高级/舒服/论文感/再宽松点/更大气"
hook: create 时即用 roomy + 较大字号 + 保护主图区，而非单点微调
created: 2026-06-22
updated: 2026-06-22
last_hit: 2026-06-22
evidence_count: 1
superseded_by: 
---

# 老板风格偏好：roomy journal polish

## Baseline（默认做法）
默认 `layout_guard_spec.intent="balanced"`，视觉紧凑，适合投稿。

## Deviation（关键发现）
老板反复要求"更高级/更舒服/更大气"，本质是要更大的字、更大的 marker、更宽敞的画布、更少的拥挤感。

## Result（可验证结果）
用 `roomy` + 较大字号后，老板一轮过，不再要求"再大一点"。

## Reusable Rule（祈使句，可直接落地）
老板第一次开口要求"更好看/更大气"时，不要逐点微调；直接开 `layout_guard_spec.intent="roomy"`、加大 `axis_label_size`、加大 `marker_size`、宽画布 `aspect_ratio`。
