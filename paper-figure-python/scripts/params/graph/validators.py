#!/usr/bin/env python3
"""参数层依赖与归属校验器。"""

from __future__ import annotations

from params.contracts.layer_keys import LAYER_KEYS
from params.graph.dependency_graph import LAYER_DEPENDENCIES
from params.graph.dependency_graph import LAYER_ORDER


def validate_unique_layer_keys() -> list[str]:
    errors: list[str] = []
    key_owner: dict[str, str] = {}
    for layer, keys in LAYER_KEYS.items():
        for key in keys:
            owner = key_owner.get(key)
            if owner is not None and owner != layer:
                errors.append(f"参数 {key} 同时归属于 {owner} 与 {layer}")
            key_owner[key] = layer
    return errors


def validate_dependency_graph() -> list[str]:
    errors: list[str] = []
    nodes = set(LAYER_ORDER)

    for node, deps in LAYER_DEPENDENCIES.items():
        if node not in nodes:
            errors.append(f"依赖图包含未知层: {node}")
        for dep in deps:
            if dep not in nodes:
                errors.append(f"依赖图包含未知依赖: {node} -> {dep}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str, path: list[str]) -> None:
        if node in visiting:
            cycle = " -> ".join(path + [node])
            errors.append(f"依赖图存在环: {cycle}")
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in LAYER_DEPENDENCIES.get(node, set()):
            dfs(dep, path + [node])
        visiting.remove(node)
        visited.add(node)

    for node in nodes:
        dfs(node, [])

    return errors


def assert_graph_contract() -> None:
    errors = [*validate_unique_layer_keys(), *validate_dependency_graph()]
    if errors:
        raise ValueError("参数层契约校验失败: " + "；".join(errors))


__all__ = ["assert_graph_contract", "validate_dependency_graph", "validate_unique_layer_keys"]
