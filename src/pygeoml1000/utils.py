"""Helpers shared by more than one module of this package."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np


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


def convert_to_plain_types(obj: Any) -> Any:
    """Convert numpy types and dict subclasses to plain Python types, recursively.

    The compilation works with numpy arrays, and a config read from a metadata
    tree carries dict subclasses. Neither survives a round trip through YAML, so
    everything a config carries goes through here.
    """
    if isinstance(obj, dict):
        return {str(key): convert_to_plain_types(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_to_plain_types(item) for item in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.str_):
        return str(obj)
    return obj


def normalize_records(inp: Any) -> list[dict]:
    """Normalize a catalog of records into a non-empty list of mappings.

    A pre-compiled catalog, such as ``crystal.yaml`` or ``hpge.yaml``, is a list
    of records. A config that holds a single record may give it as a mapping.
    """
    if isinstance(inp, dict):
        inp = [inp]
    if not isinstance(inp, list):
        msg = "a record catalog must be a list of records or a mapping containing one record"
        raise TypeError(msg)
    if inp == []:
        msg = "a record catalog must contain at least one record"
        raise ValueError(msg)
    if not all(isinstance(record, dict) for record in inp):
        msg = "each record must be a mapping"
        raise TypeError(msg)
    return inp
