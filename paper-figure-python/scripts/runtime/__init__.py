"""Runtime entrypoints for thin plot jobs."""

from .context import FigureContext
from .engine import run_figure

__all__ = ["FigureContext", "run_figure"]
