from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
from pyg4ometry import gdml
from pygeomtools import detectors


def test_import():
    import l1000geom  # noqa: F401


def test_construct(tmp_path):
    from l1000geom import core

    registry = core.construct(use_detailed_fiber_model=True)
    # verify that we get the expected channel counts.
    ch_count = Counter([d.detector_type for f, d in detectors.walk_detectors(registry)])
    assert ch_count["optical"] == 2 * (9 + 20)  # 2*(IB+OB)
    assert ch_count["germanium"] == 101  # from channelmap @ 20230311T235840Z
    det_file_detailed = tmp_path / "det-detailed.mac"
    detectors.generate_detector_macro(registry, det_file_detailed)

    registry = core.construct(use_detailed_fiber_model=False)
    # verify that we get the expected channel counts.
    ch_count = Counter([d.detector_type for f, d in detectors.walk_detectors(registry)])
    assert ch_count["optical"] == 2 * (9 + 20)  # 2*(IB+OB)
    assert ch_count["germanium"] == 101  # from channelmap @ 20230311T235840Z
    det_file_segmented = tmp_path / "det-segmented.mac"
    detectors.generate_detector_macro(registry, det_file_segmented)

    with Path.open(det_file_detailed) as f_det, Path.open(det_file_segmented) as f_seg:
        assert f_det.readlines() == f_seg.readlines()


def test_read_back(tmp_path):
    from l1000geom import core

    registry = core.construct(use_detailed_fiber_model=False)
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

    from legendoptics import store
    from legendoptics.fibers import fiber_core_refractive_index

    from l1000geom import core

    # test that replaced material properties are reflected in the GDML.
    fiber_core_refractive_index.replace_implementation(lambda: 1234)
    reg = core.construct(use_detailed_fiber_model=False)
    rindex = reg.defineDict["ps_fibers_RINDEX"].eval()
    assert np.all(rindex[:, 1] == [1234, 1234])

    # test that after the reset, the created GDML contains the original values again.
    store.reset_all_to_original()
    reg = core.construct(use_detailed_fiber_model=False)
    rindex = reg.defineDict["ps_fibers_RINDEX"].eval()
    assert np.all(rindex[:, 1] == [1.6, 1.6])
