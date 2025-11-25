# ruff: noqa: PLC0415 F401

from __future__ import annotations

import numpy as np
import pytest
from pyg4ometry import gdml


def test_import_legacy():
    with pytest.deprecated_call():
        import l1000geom


def test_import():
    import pygeoml1000


def test_construct(tmp_path):
    from pygeoml1000 import core

    core.construct()


def test_read_back(tmp_path):
    from pygeoml1000 import core

    registry = core.construct()
    # write a GDML file.
    gdml_file_detailed = tmp_path / "segmented.gdml"
    w = gdml.Writer()
    w.addDetector(registry)
    w.write(gdml_file_detailed)
    # try to read it back.
    gdml.Reader(gdml_file_detailed)


def test_material_store():
    # replacing material properties is _not_ a core functionality of this package, but
    # we have to make sure that replaced material properties from the optics package are
    # propagated correctly to the generated GDML files.

    from pygeomoptics import store
    from pygeomoptics.fibers import fiber_core_refractive_index

    from pygeoml1000 import core

    # test that replaced material properties are reflected in the GDML.
    fiber_core_refractive_index.replace_implementation(lambda: 1234)
    reg = core.construct()
    rindex = reg.defineDict["ps_fibers_RINDEX"].eval()
    assert np.all(rindex[:, 1] == [1234, 1234])

    # test that after the reset, the created GDML contains the original values again.
    store.reset_all_to_original()
    reg = core.construct()
    rindex = reg.defineDict["ps_fibers_RINDEX"].eval()
    assert np.all(rindex[:, 1] == [1.6, 1.6])
