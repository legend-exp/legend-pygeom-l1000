from __future__ import annotations

import importlib.metadata

import legend_pygeom_l1000 as m


def test_version():
    assert importlib.metadata.version("legend_pygeom_l1000") == m.__version__
