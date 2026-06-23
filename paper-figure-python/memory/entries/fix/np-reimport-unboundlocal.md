---
path: fix://runtime/np-reimport-unboundlocal
scope: global
type: fix
status: active
weight: 0.8
hits: 0
misses: 0
trigger: 报 UnboundLocalError np，或在 pre_draw/post_draw 内写了 import numpy as np
hook: 不要在函数内部 import numpy as np；模板已提供全局 np，直接用
created: 2026-06-22
updated: 2026-06-22
last_hit: 2026-06-22
evidence_count: 1
superseded_by:
---

# UnboundLocalError: np —— 函数内重复 import numpy

## Baseline（默认做法）
习惯在每个函数里 `import numpy as np` 求稳。

## Deviation（关键发现）
thin 模板已在模块层提供全局 `np`。函数内再 `import numpy as np` 会让 Python 把 `np` 当作该函数的局部变量，在 import 行执行前任何对 `np` 的引用都触发 `UnboundLocalError: np`。

## Result（可验证结果）
删掉函数内的 `import numpy as np` 即恢复；`np` 在 `pre_draw`/`post_draw` 中直接可用。

## Reusable Rule（祈使句，可直接落地）
绝不在 `pre_draw`/`post_draw` 内 `import numpy as np`；直接用模板提供的全局 `np`。其他库（pandas/scipy/seaborn）才在 `AI_EDIT_ZONE:imports` 里 import。

## Evidence（证据来源）
- 2026-06-22 · 种子经验 · 来自 SKILL.md「常见问题」高频踩坑，与 SKILL.md 双写（必达 + 可召回强化）。
