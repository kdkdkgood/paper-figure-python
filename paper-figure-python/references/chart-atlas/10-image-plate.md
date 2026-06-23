# 10 — 图像拼贴（image plate）

**意图判据**：成像数据（显微/荧光/注意力图/特征图）或多个矩阵的网格展示，靠"重复中找差异"。

**推荐 layout**：`quad-2x2` / `quad-1x4` / `hex-2x3` 均匀网格；暗背景配 `palette_preset="imaging_dark"`。
见 `figure-archetypes.md` B（Dark Image Plate）。

**关键 API**：

- 逐面板：`for i, ax in enumerate(ctx.axes_grid.ravel()): ax.imshow(imgs[i], cmap=ctx.color["sequential_cmap"])`。
- 暗背景：`from runtime.helpers import style_dark_image_ax`，并在 CONFIG 传
  `axis_spec={"show_top_spine": False, "show_right_spine": False}`。
- 标尺：`ax.plot([x0,x0+L],[y0,y0], color="w", lw=2)` + `ax.text(...)`。
- 面板内文字按底色取色：`from runtime.helpers import luminance_aware_text_color`。
- 统一色标范围：所有面板共用 `vmin/vmax`，并加一个共享 colorbar。

**常见陷阱**：

- 各面板独立归一导致不可比——共享 `vmin/vmax`。
- runtime 默认白底，黑图露白边——务必逐面板 `set_facecolor` 或用 `style_dark_image_ax`。
- 拼贴过密无间隔——用 `layout_guard_spec` 控制间距，不手动 subplots_adjust。

**post_draw 骨架**：

```python
def post_draw(ctx):
    import numpy as np
    from runtime.helpers import style_dark_image_ax
    imgs = ctx.df_override                       # list[2D array]，长度 = 面板数
    cmap = ctx.color["sequential_cmap"]
    vmax = float(max(np.nanmax(im) for im in imgs)); vmin = float(min(np.nanmin(im) for im in imgs))
    last = None
    for i, ax in enumerate(ctx.axes_grid.ravel()):
        if i >= len(imgs):
            ax.set_axis_off(); continue
        last = ax.imshow(imgs[i], cmap=cmap, vmin=vmin, vmax=vmax)
        style_dark_image_ax(ax)
        ax.set_title(f"t{i}", color="w", fontsize=ctx.style["annotation_size"])
    if last is not None:
        ctx.fig.colorbar(last, ax=list(ctx.axes_grid.ravel()), fraction=0.025, pad=0.02)
```

> 配合 `imaging_dark` 预设时，记得 create/patch 传入
> `axis_spec={"show_top_spine": False, "show_right_spine": False}`。
