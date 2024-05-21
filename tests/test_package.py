from __future__ import annotations

import importlib.metadata

import l1000geom


def test_version():
    assert importlib.metadata.version("l1000geom") == l1000geom.__version__
