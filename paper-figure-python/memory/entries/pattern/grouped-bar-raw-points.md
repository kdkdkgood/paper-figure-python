---
path: pattern://bar/grouped-with-raw-points
scope: global
type: pattern
status: active
weight: 0.70
hits: 0
misses: 0
trigger: 分组/条形图展示均值或汇总，样本量不大
hook: 条形上叠加抖动原始点（jitter），暴露分布而非只给均值条
created: 2026-06-22
updated: 2026-06-22
last_hit: 2026-06-22
evidence_count: 1
superseded_by: 
---

# 分组条形图叠加原始数据点

## Baseline（默认做法）
分组柱状/条形图只画均值 ± 误差棒，隐藏了样本分布信息。

## Deviation（关键发现）
当样本量不大（n ≤ 30），均值条 + 误差棒会掩盖离群值和分布形状。叠加上 jitter 原始点能一目了然。

## Result（可验证结果）
叠加后读者能同时看到集中趋势与分布，审稿人/老板都更认可"信息量充分"的呈现。

## Reusable Rule（祈使句，可直接落地）
n ≤ 30 的分组条形图上，务必用半透明 jitter 点叠加原始数据；用 `ctx.palette()` 给每组配色一致的点。

## Evidence（证据来源）
- 2026-06-22 · 种子经验 · 统计可视化经典原则。
