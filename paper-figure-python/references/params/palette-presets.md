<!-- 条件读取：需要选择领域配色或查预设细节时读取此文件 -->

# 领域配色预设（palette_preset）

真值源：`scripts/palette_registry.py`。**配色只有单一管线：`color_spec.palette_preset` 是唯一的"换配色"
入口**，选定后一次性切换分类色板 + 顺序色图 + 发散色图 + 热图取色倾向。

- 换配色 → 只设 `palette_preset`（`default` / `ml_pastel` / `imaging_dark` / `clinical_temporal` / `genomics_wave`），永远生效。
- 极致自定义 → `color_spec.categorical_palette` 传**自定义 hex 颜色列表**（唯一逃生口，优先于 preset）。
- `categorical_palette` 字符串只接受 `"auto"`（=交给 preset）；不再接受 `tableau10` 这类命名色板字符串，避免与 preset 双键打架。

## 预设总览

| preset | 领域 | categorical_palette | sequential_cmap | diverging_cmap | 背景 |
|---|---|---|---|---|---|
| `default` | 通用 / 工程 | tableau10 | viridis | RdBu_r | 白 |
| `ml_pastel` | 机器学习 / 多方法对比 | ml_pastel（低饱和） | cividis | RdBu_r | 白 |
| `imaging_dark` | 显微 / 荧光成像 | imaging_dark（cyan/magenta） | magma | RdBu_r | 黑 |
| `clinical_temporal` | 临床 / 时间序列 | clinical_temporal（冷→暖） | cividis | RdBu_r | 白 |
| `genomics_wave` | 生物信息 / 基因组 | genomics_wave（高区分） | viridis | PuOr | 白 |

## 命名分类色板（hex）

> 以下命名色板是 **preset 的内部数据**，通过对应 `palette_preset` 选用，不再作为 `categorical_palette` 的字符串取值。

| 名称 | 颜色 |
|---|---|
| `okabe_ito` | 色盲友好 8 色（橙/天蓝/绿/蓝/朱/紫红/黄/黑） |
| `tableau10` | 通用高对比 10 色 |
| `grayscale` | 灰阶 6 档 |
| `ml_pastel` | `#A1C9F4 #FFB482 #8DE5A1 #FF9F9B #D0BBFF #DEBB9B #FAB0E4 #CFCFCF` |
| `imaging_dark` | `#00E5FF #FF4FD8 #FFE54F #7CFC00 #FF8A3D #FFFFFF` |
| `clinical_temporal` | `#08519C #3182BD #6BAED6 #FDAE6B #E6550D #A63603` |
| `genomics_wave` | `#1B9E77 #D95F02 #7570B3 #E7298A #66A61E #E6AB02 #A6761D #666666` |

要某个固定配色但没有对应 preset 时，用 `categorical_palette` 直接传**自定义 hex 列表**（逃生口）。

## 用法

create 时通过 overrides：

```bash
--overrides '{"color_spec": {"palette_preset": "imaging_dark"}}'
```

或后调整 patch：

```json
{"overrides": {"color_spec": {"palette_preset": "ml_pastel"}}}
```

hook 中读取：

```python
def post_draw(ctx):
    ax = ctx.ax(0)
    colors = ctx.palette(4)               # 当前预设的分类色
    seq = ctx.color["sequential_cmap"]    # 当前预设的顺序色图
    div = ctx.color["diverging_cmap"]     # 当前预设的发散色图
```

## 选型建议

- 多条曲线 / 多方法 benchmark → `ml_pastel`，避免高饱和刺眼。
- imshow 荧光 / 注意力图、黑底 → `imaging_dark` + `helpers.style_dark_image_ax`。
- 生存曲线、随访、时间分箱 → `clinical_temporal`。
- 基因组 track、通路富集、组学热图 → `genomics_wave`（发散 PuOr 对正负更中性）。
- 不确定 / 工程通用 → `default`。
