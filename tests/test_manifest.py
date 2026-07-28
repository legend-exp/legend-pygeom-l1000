# ruff: noqa: PLC0415

from __future__ import annotations

import pytest
import yaml


@pytest.fixture(scope="module")
def manifest():
    from pygeoml1000 import core, manifest

    return manifest.generate_manifest(core.construct(), detail_level="radiogenic")


def _part(manifest, name):
    parts = [part for part in manifest["parts"] if part["name"] == name]
    assert len(parts) == 1, f"{name}: expected exactly one entry, got {len(parts)}"
    return parts[0]


def test_pyg4ometry_units():
    """The manifest assumes mesh volumes in mm^3 and densities in g/cm3.

    Neither is parametrised in pyg4ometry: a solid is converted to mm when it is meshed, whatever
    ``lunit`` it was declared with, and a density is stored as given and written to GDML without a
    unit attribute. If either ever changed, every mass in the manifest would silently be off by a
    constant factor, so pin them here.
    """
    from pyg4ometry import geant4

    from pygeoml1000 import manifest

    registry = geant4.Registry()
    assert geant4.solid.Box("in_mm", 10, 10, 10, registry, "mm").mesh().volume() == 1e3
    assert geant4.solid.Box("in_m", 1, 1, 1, registry, "m").mesh().volume() == 1e9
    assert manifest.MESH_VOLUME_UNIT == "mm**3"

    material = geant4.Material(name="copperish", density=8.96, number_of_components=1, registry=registry)
    assert material.density == 8.96
    assert manifest.DENSITY_UNIT == "g/cm**3"


def test_placement_multiplicity(manifest):
    """The placement count must be propagated down the volume tree."""
    core_fiber = _part(manifest, "fiber_core_l1349_bNone")
    assert core_fiber["placements"] == 12096
    assert core_fiber["total_mass"] > 10_000  # g

    # cross-check against test_volume_caching, which asserts the same numbers on the registry.
    assert _part(manifest, "cable_hv_140.10")["placements"] == 336
    assert _part(manifest, "hpge_support_copper_weldment_top")["placements"] == 1008


def test_totals_are_consistent(manifest):
    total = sum(part["total_mass"] for part in manifest["parts"])
    assert total == pytest.approx(manifest["totals"]["mass"])
    assert sum(manifest["totals"]["by_material"].values()) == pytest.approx(total)


def test_parts_are_sane(manifest):
    from pygeoml1000 import core

    registry = core.construct()
    # the world volume is not a part, everything else in the registry is.
    assert len(manifest["parts"]) == len(registry.logicalVolumeDict) - 1

    for part in manifest["parts"]:
        assert part["unit_volume"] > 0, f"{part['name']} has a non-positive volume"
        assert part["placements"] >= 1
        assert part["material"] in registry.materialDict
        assert part["total_volume"] == pytest.approx(part["unit_volume"] * part["placements"])

    masses = [part["total_mass"] for part in manifest["parts"]]
    assert masses == sorted(masses, reverse=True), "parts are not sorted by descending mass"


def test_write_manifest(tmp_path):
    from pygeoml1000 import core, manifest

    manifest_file = tmp_path / "parts.yaml"
    manifest.write_manifest(core.construct(), manifest_file, detail_level="radiogenic")

    with manifest_file.open() as f:
        read_back = yaml.safe_load(f)

    assert read_back["metadata"]["detail_level"] == "radiogenic"
    assert read_back["metadata"]["n_logical_volumes"] == len(read_back["parts"]) + 1
    assert read_back["totals"]["mass"] > 0
