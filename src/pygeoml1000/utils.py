"""Helpers shared by more than one module of this package."""

from __future__ import annotations

import copy


def deep_merge(base: dict, override: dict) -> dict:
    """Merge ``override`` into a copy of ``base``, recursively.

    Two mappings merge key by key. Any other value in ``override`` replaces the
    value in ``base``. Neither input changes.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged
