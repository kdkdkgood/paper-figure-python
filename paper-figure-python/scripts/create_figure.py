#!/usr/bin/env python3
"""主链入口：创建新图表任务（stage1）。"""

from __future__ import annotations

from entrypoints import run_create_cli


def main() -> None:
    run_create_cli()


if __name__ == "__main__":
    main()
