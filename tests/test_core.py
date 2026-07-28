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


def test_volume_caching():
    """Geometrically identical parts must share a single logical volume.

    Each of these parts is identical across all detector units, so it must be built once and
    placed many times. This guards against a regression where a logical volume name embeds a
    per-detector or per-string identifier, which rebuilds the entire solid tree per placement.
    """
    from pygeoml1000 import core

    registry = core.construct()

    # name stem -> expected number of placements
    expected_placements = {
        "cable_hv": 336,
        "cable_signal": 336,
        "ultem_clamp_hv": 336,
        "ultem_clamp_signal": 336,
        "signal_asic": 336,
        "hpge_support_copper_weldment_top": 1008,
        "ultem_insulator_du_holder": 1008,
        "hpge_support_copper_rod": 126,
    }

    for stem, n_expected in expected_placements.items():
        lvs = [name for name in registry.logicalVolumeDict if name.startswith(stem)]
        assert len(lvs) == 1, f"{stem}: expected exactly one cached logical volume, got {lvs}"

        pvs = [name for name in registry.physicalVolumeDict if name.startswith(stem)]
        assert len(pvs) == n_expected, f"{stem}: expected {n_expected} placements, got {len(pvs)}"

    # a coarse guard against per-instance logical volumes creeping back in elsewhere.
    assert len(registry.logicalVolumeDict) < 600


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
