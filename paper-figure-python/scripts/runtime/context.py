"""Runtime context passed to thin plot hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from palette_registry import resolve_palette


Hook = Callable[["FigureContext"], None]


@dataclass
class FigureContext:
    """Mutable state shared between runtime and user hook functions."""

    cfg: dict[str, Any]
    job_dir: Path
    pre_draw: Hook | None = None
    post_draw: Hook | None = None
    fig: Any = None
    axes_grid: Any = None
    nrows: int = 1
    ncols: int = 1
    df_override: Any = None
    panel_dfs: dict[int, Any] = field(default_factory=dict)
    panel_labels: Any = None
    report: dict[str, Any] = field(default_factory=dict)

    @property
    def style(self) -> dict[str, Any]:
        """Recommended visual style parameters for custom drawing code."""

        value = self.cfg.get("style_spec", {})
        return value if isinstance(value, dict) else {}

    @property
    def layout(self) -> dict[str, Any]:
        """Recommended layout parameters for the current figure."""

        value = self.cfg.get("layout_spec", {})
        return value if isinstance(value, dict) else {}

    @property
    def color(self) -> dict[str, Any]:
        """Recommended color parameters for the current figure."""

        value = self.cfg.get("color_spec", {})
        return value if isinstance(value, dict) else {}

    @property
    def colors(self) -> list[str]:
        return self.palette()

    @property
    def share_axes(self) -> bool:
        """当前任务是否启用 matplotlib 原生共享轴（shared_axis 模式）。

        单一事实源 ``runtime_derived.share_axes``，与 runtime engine 判定一致。
        """

        runtime_derived = self.cfg.get("runtime_derived", {})
        if not isinstance(runtime_derived, dict):
            return False
        return bool(runtime_derived.get("share_axes", False))

    @property
    def sharex(self) -> bool:
        """是否列内共享 X 轴（多行布局且 share_axes 生效）。"""

        return self.share_axes and self.nrows > 1

    @property
    def sharey(self) -> bool:
        """是否行内共享 Y 轴（多列布局且 share_axes 生效）。"""

        return self.share_axes and self.ncols > 1

    def palette(self, n: int | None = None) -> list[str]:
        """Return a practical categorical palette for custom plot layers.

        解析逻辑集中在 ``palette_registry.resolve_palette``，与 runtime 引擎共用，
        并支持 ``color_spec.palette_preset`` 领域预设。
        """

        return resolve_palette(self.color, n)

    def ax(self, index: int = 0):
        """Return an axis by flat panel index."""

        if self.axes_grid is None:
            raise RuntimeError("axes_grid 尚未初始化；请在 post_draw(ctx) 中调用 ctx.ax()。")
        flat = self.axes_grid.ravel()
        return flat[int(index)]

    def axis(self, row: int = 0, col: int = 0):
        """Return an axis by row/column position."""

        if self.axes_grid is None:
            raise RuntimeError("axes_grid 尚未初始化；请在 post_draw(ctx) 中调用 ctx.axis()。")
        return self.axes_grid[int(row), int(col)]
