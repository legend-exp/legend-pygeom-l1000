from __future__ import annotations


def test_import():
    import l1000geom  # noqa: F401


def test_construct():
    import l1000geom.core

    l1000geom.core.construct(use_detailed_fiber_model=False)
    l1000geom.core.construct(use_detailed_fiber_model=True)
