<!-- 条件读取：决定"画哪种图"时按需读取对应分片，不必全读。 -->

# Chart-Type Atlas：图型速查地图

按图型家族分片的快速参考。每片含：**意图判据 / 推荐 layout / 关键 API / 常见陷阱 /
post_draw 骨架**。这里是 priors，不是限制——AI 可自由组合或另写图型。

| 编号 | 图型家族 | 一句话意图 |
|---|---|---|
| [01](01-bar-grouped.md) | 分组柱 + 显著性 | 组间均值比较，要看差异和显著性 |
| [02](02-line-trend.md) | 趋势线 + 置信带 | 连续/时间变量的走势与不确定性 |
| [03](03-scatter-correlation.md) | 散点 + 回归 | 两连续变量的关系与拟合 |
| [04](04-heatmap.md) | 热图 / 相关矩阵 | 矩阵型数据、相关性、聚类 |
| [05](05-ridge-distribution.md) | 山脊 / 分布 | 多组分布形状的纵向比较 |
| [06](06-raincloud.md) | 雨云图 | 分布 + 原始点 + 摘要三合一 |
| [07](07-forest-interval.md) | 森林图 / 区间 | 效应量、置信区间、多模型对比 |
| [08](08-polar-radar.md) | 极坐标 / 雷达 | 多指标轮廓、周期性数据 |
| [09](09-paired-before-after.md) | 配对前后 | 配对样本的个体变化 |
| [10](10-image-plate.md) | 图像拼贴 | 成像/矩阵图的网格展示 |

通用约定：

- 取色用 `ctx.palette(n)` / `ctx.color`；字号线宽用 `ctx.style`。
- 可选工具：`from runtime.helpers import add_significance_bracket, make_ablation_colors, ...`。
- 不手动调用 `tight_layout/subplots_adjust`；布局交给守卫。
