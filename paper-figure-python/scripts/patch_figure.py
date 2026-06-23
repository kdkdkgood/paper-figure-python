#!/usr/bin/env python3
"""主链入口：对现有 plot.py 做结构化后调整。"""

from __future__ import annotations

from entrypoints import run_patch_cli


def main() -> None:
    run_patch_cli()


if __name__ == "__main__":
    main()
