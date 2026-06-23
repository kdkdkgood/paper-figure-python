# 经验成长系统 · 操作细则（memory-protocol）

> 本文件**不进默认读取链**，仅在做记忆操作（写入/审计/强化/排障）时读取。
> 日常召回只需 `memory.py recall` 的输出，不必读本文件。
> 设计依据见 `经验设计/paper-figure-python-memory-v3-final.md`。

## 0. 旁路契约（最高优先级）

- `memory.py` 任何命令都不会把异常抛进绘图主链；失败即静默降级、返回空结果、退出码 0。
- 绘图主链（`create_figure.py` / `patch_figure.py` / `plot.py` / `runtime/*`）**绝不依赖 memory**。
- 写回只允许落在 `memory/` 与项目层 `<WORKSPACE>/.paper-figure-memory/`，**绝不碰任务 `output/`**。

## 1. 记忆根与分层

| 层 | 位置 | 用途 |
|---|---|---|
| 全局层 | `env PAPER_FIGURE_MEMORY_ROOT` → `<SKILL_ROOT>/memory` → `~/.paper-figure-memory`（只读回退） | 跨项目稳定偏好、通用修法、通用配方 |
| 项目层 | `<WORKSPACE>/.paper-figure-memory/` | 某论文/课题/期刊/数据批次的局部规律 |

`<SKILL_ROOT>` 由 `memory.py` 自动探测（`__file__` 反推，跨 OS/安装位零配置）；可用 `env PAPER_FIGURE_SKILL_ROOT` 覆盖。两个 env 互不影响：`PAPER_FIGURE_SKILL_ROOT` 定位 skill，`PAPER_FIGURE_MEMORY_ROOT` 单独指定记忆根（例如把经验集中存到团队共享目录）。

召回优先级：**项目层 > 全局层 > Skill 默认规则**。项目层经验**不得自动升级**为全局层（需 ≥2 项目复现或用户明确"以后都这样"）。

## 2. 命令速查（root + 七动词）

`python3` 与 `$SKILL_ROOT` 均为占位符：用调用方环境内可用的 Python；`$SKILL_ROOT` 是 skill 实际安装目录（**不写死**，随机器/OS 变化）。先自举一次拿真实路径：

```bash
# memory.py 用 __file__ 自定位，任何 OS/安装位都成立；root 动词自报路径
python3 "<本文件所在 skill 的 scripts 目录>/memory.py" root
#   → {"skill_root": "...", "memory_root": "...", ...}
# 拿到 skill_root 后，下文 $SKILL_ROOT 即替换为它（或直接 export SKILL_ROOT=<该值>）
```

```bash
M="$SKILL_ROOT/scripts/memory.py"

# 开新图：一次拿 BOOT 锚点 + 命中 hook（正文 0 展开）
python3 "$M" recall --workspace <WS> --context "<任务摘要>"

# 写入/更新正式经验（path 已存在则 append 不覆盖）
python3 "$M" remember --scope global --path "fix://layout/xxx" \
  --trigger "..." --hook "..." --weight 0.8 --body-file <临时正文文件>

# 强化回路：回报召回经验被采纳/推翻（任务结束时）
# 多个 path 用空格分隔跟同一 flag，不要重复 --adopted / --rejected（重复会覆盖只留最后一个）
python3 "$M" reinforce --workspace <WS> \
  --adopted "fix://..." "pattern://..." --rejected "pref://..."

# 证据驱动候选：从 job report 历史挖候选（不进正式经验）
python3 "$M" suggest --job-dir <JOB_DIR> --workspace <WS>

# 审计：报重复/冲突/陈旧/超长；--rebuild-index 仅重建 INDEX
python3 "$M" audit --workspace <WS>
python3 "$M" audit --rebuild-index

# 候选出列（出列后用补齐的五段式正文走 remember 正式写入）
python3 "$M" promote --candidate-id "<job名或 path_hint>" --scope global
```

## 3. 写入闸门（write_score）

任务稳定后计算（详见 v3 §4.1）：

```text
write_score =
  3×(用户明确认可/否决/"以后都这样")
+ 2×(终版与首版有实质差异：含 config 差异 或 AI_EDIT_ZONE 代码差异)
+ 2×(解决了 recall 未命中的新坑)
+ 1×(同类调整在 ≥2 个 job 复现)
- 3×(纯数据/列名/路径/语法修正)
- 2×(已有经验已覆盖，仅需 +hits/+evidence)
```

- `≥3` → 主动一句话提示后 `remember`/`promote`。
- `1..3` → 仅 `suggest` 进 inbox，留待 audit 择优。
- `<1` → 不记。

> AI_EDIT_ZONE 代码差异由 `suggest` 经 run report 的 `ai_edit_zone_hash` 自动判定（候选标记 `zone_evolved=true`，`path_hint` 指向 `pattern://`）。Edit→Run 迭代与 patch 同等计入收敛轮数，自定义图型技巧不再因"修改发生在代码层"而漏沉淀。

写入前自检（缺一不写）：会改变下次行为？非重复？五段齐全且 Rule 是祈使句？证据真实？不含项目隐私（除非项目层）？

## 4. 经验类型与 URI

| 类型 | URI 例 | 记什么 |
|---|---|---|
| `pref` | `pref://boss/style/roomy-journal-polish` | 长期审美偏好 |
| `fix` | `fix://layout/colorbar-clipped-right` | 复发问题的稳定修法 |
| `pattern` | `pattern://bar/grouped-with-raw-points` | 被接受图的配方 |
| `palette` | `palette://clinical/blue-orange-print-safe` | 验证过的领域配色 |
| `workflow` | `workflow://shared-axis/set-lim-linkage` | 流程/工具选择经验 |
| `anti` | `anti://layout/shrink-main-area-for-colorbar` | **负经验/禁忌**，召回时前置 |

URI → 文件：`fix://layout/colorbar-clipped-right` ⇒ `entries/fix/layout-colorbar-clipped-right.md`（`/` 转 `-`）。

## 5. 经验正文：五段式

`Baseline → Deviation → Result → Reusable Rule → Evidence`。frontmatter 字段：
`path scope type status weight hits misses trigger hook created updated last_hit evidence_count superseded_by`。
- `weight`：召回基础权重（0–1）。`hits/misses`：reinforce 维护，勿手改。
- `status`：`active | superseded | deprecated`。废弃只置 status，不硬删（移入 `archive/`）。
- 用 `[[fix://...]]` 交叉链接相关经验。

## 6. 召回与强化

- **召回**：`recall` 返回 BOOT + 按 `eff_weight = weight × decay(age,hits)` 排序的 hook 清单。
  - 默认**只用 hook 决策**；仅 `heavy_read=true`（`eff_weight≥0.8`）、高风险（多面板/colorbar/shared_axis/复杂图例）、或 hook 与当前情况冲突时，才读对应 entry 正文。
  - 项目层同分排全局层前；`anti://` 命中时小幅前置。
  - **关联度信号**：每条 match 带 `relevance`（`high`≥3.0 / `medium`≥1.5 / `low`，按 match_score 判档）；顶层 `quality` 取 top-1 关联度，`quality_note`/`hint` 随之切换。`quality=low` 表示当前上下文与已有经验关联弱——直接走 SKILL.md 默认规则，别被 `low` 条目带偏（`eff_weight` 高但 `relevance=low` 只说明该经验本身重，不代表与当前任务相关）。
- **强化**（任务结束时必做）：把本次召回里真正落地的经验填 `--adopted`，被当场推翻的填 `--rejected`。
  - adopted → `hits+1, weight+0.03`（封顶 0.98）；rejected → `misses+1, weight-0.05`（下限 0.10）。
  - 这让经验"越用越准"，长期不命中且零复用者经衰减自然下沉进 audit 待办。

## 7. suggest 的逻辑

读 `<JOB_DIR>/orchestrator_reports/*.json`（无则退回 `orchestrator_report.json`）：
1. 取首个 create 与最后一个 `render_validation.passed` 的 config，做 flatten diff = `config_delta`。
2. 统计所有 `patch.override_patch_keys` 频次 = 用户反复纠结的维度（`hot_override_keys`）。
3. `patch 轮数 ≥3 且 render 通过` → 标记收敛型。
4. 候选写入 `inbox/candidates.jsonl`，**不进正式经验**；AI 据此判断是否 `remember`。

## 8. 审计：压缩与提炼

触发：正式经验 >30 / inbox >20 / 新增未审计 >10 / 冲突 / 衰减待办 ≥5 / 用户要求。频率：两次至少隔 5 任务，最多 30 任务强制一次。

动作：`merge`（合并保 evidence）、`distill`（**多条低层修法升维成高层策略**，绘图审计核心）、`deprecate`、`archive`、`retrigger`、`promote_to_boot`。

流程：先扫 INDEX 标记（重复/陈旧/低密度）→ 读标记项答三问（改变什么行为？还能触发？和谁重叠？）→ **破坏性操作先报告原因、老板确认后执行** → 更新 `audit-log.md` 与 INDEX（`audit --rebuild-index`）。

**反序列重写断路器**：同一条经验在同一会话不二改。第二次想改时停手，在 entry 末尾留 `<!-- TODO:next-session: <想法> -->`，下次会话再处理。

## 9. BOOT.md 纪律

≤10 行、每行 1 句纯祈使、只写稳定到能改默认行为的原则、不写项目细节。只能由 audit `promote_to_boot`（高 hits+weight+跨项目复现）晋升，不随手塞。

## 10. INDEX 是派生缓存

`INDEX.md` 由 entry frontmatter 派生，`remember/reinforce/audit` 会自动重建。手工改了 entry 后跑 `audit --rebuild-index` 同步。**不要手改 INDEX 表格**。
