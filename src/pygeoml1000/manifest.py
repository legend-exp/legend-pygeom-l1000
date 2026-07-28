"""Generate a parts manifest: the mass of every part actually present in the geometry.

The manifest lists one entry per logical volume, with its material, its number of placements and
the resulting total mass. This can be used as a cross-checked against the experiment estimated material count.
"""

from __future__ import annotations

import collections
import logging
from pathlib import Path
from typing import Any

import pint
import yaml
from pyg4ometry import config as meshconfig
from pyg4ometry import geant4

from . import _version

log = logging.getLogger(__name__)

u = pint.get_application_registry()

#: units of the numerical quantities in the manifest.
UNITS = {"volume": "cm**3", "mass": "g", "density": "g/cm**3"}

#: unit of the volumes returned by :meth:`pyg4ometry.pycsg.core.CSG.volume`
MESH_VOLUME_UNIT = "mm**3"

#: unit of :attr:`pyg4ometry.geant4.Material.density`
DENSITY_UNIT = "g/cm**3"


def _count_placements(world_lv: geant4.LogicalVolume) -> collections.Counter:
    """Count how often each logical volume is placed in the tree below ``world_lv``.

    The multiplicity has to be propagated down the tree: a logical volume placed once inside a
    mother that is itself placed 12096 times is present 12096 times. Counting only the physical
    volumes that directly reference a logical volume is off by that factor.
    """
    memo: dict[str, collections.Counter] = {}

    def walk(lv: geant4.LogicalVolume) -> collections.Counter:
        if lv.name in memo:
            return memo[lv.name]

        total = collections.Counter({lv.name: 1})
        for pv in lv.daughterVolumes:
            total += walk(pv.logicalVolume)

        memo[lv.name] = total
        return total

    return walk(world_lv)


def _own_volume(lv: geant4.LogicalVolume, mesh_volumes: dict[str, float]) -> float:
    """Get the volume in :data:`MESH_VOLUME_UNIT` occupied by the material of ``lv`` itself, i.e.
    the volume of its solid minus the volumes of its daughters.

    This is :func:`pygeomtools.geometry.get_approximate_volume`, but caching the mesh volumes in
    ``mesh_volumes``.
    """

    def mesh_volume(lv: geant4.LogicalVolume) -> float:
        if lv.name not in mesh_volumes:
            mesh_volumes[lv.name] = lv.solid.mesh().volume()
        return mesh_volumes[lv.name]

    volume = mesh_volume(lv)
    for pv in lv.daughterVolumes:
        volume -= mesh_volume(pv.logicalVolume)

    return volume


def generate_manifest(
    registry: geant4.Registry,
    detail_level: str | None = None,
    assemblies: list[str] | None = None,
) -> dict[str, Any]:
    """Build the parts manifest for an already-constructed geometry.

    The returned document has three sections: ``metadata`` describing how the geometry was built,
    ``totals`` with the total mass per material, and ``parts`` with one entry per logical volume,
    sorted by descending mass.

    Parameters
    ----------
    registry
        the registry returned by :func:`pygeoml1000.core.construct`.
    detail_level
        the detail level the geometry was constructed with, recorded in the manifest metadata.
    assemblies
        the assemblies the geometry was constructed with, recorded in the manifest metadata.

    """
    world_lv = registry.worldVolume
    placements = _count_placements(world_lv)

    mesh_volumes: dict[str, float] = {}
    parts = []
    mass_by_material: collections.Counter = collections.Counter()

    for name, n_placements in placements.items():
        if name == world_lv.name:
            continue  # the world is not a part.

        lv = registry.logicalVolumeDict[name]
        unit_volume = (_own_volume(lv, mesh_volumes) * u(MESH_VOLUME_UNIT)).to(UNITS["volume"])
        total_volume = unit_volume * n_placements
        density = float(getattr(lv.material, "density", 0.0) or 0.0) * u(DENSITY_UNIT)
        total_mass = (total_volume * density).to(UNITS["mass"])

        mass_by_material[lv.material.name] += total_mass.m
        parts.append(
            {
                "name": name,
                "material": lv.material.name,
                "density": density.m,
                "solid": type(lv.solid).__name__,
                "placements": n_placements,
                "unit_volume": unit_volume.m,
                "total_volume": total_volume.m,
                "total_mass": total_mass.m,
            }
        )

    parts.sort(key=lambda part: (-part["total_mass"], part["name"]))

    return {
        "metadata": {
            "package_version": _version.__version__,
            "detail_level": detail_level,
            "assemblies": assemblies,
            "mesh_slices": meshconfig.SolidDefaults.Tubs.nslice,
            "n_logical_volumes": len(registry.logicalVolumeDict),
            "n_physical_volumes": len(registry.physicalVolumeDict),
            "units": dict(UNITS),
        },
        "totals": {
            "mass": sum(mass_by_material.values()),
            "by_material": dict(mass_by_material.most_common()),
        },
        "parts": parts,
    }


def write_manifest(
    registry: geant4.Registry,
    filename: str | Path,
    detail_level: str | None = None,
    assemblies: list[str] | None = None,
) -> None:
    """Write the parts manifest of ``registry`` to ``filename`` as YAML."""
    manifest = generate_manifest(registry, detail_level=detail_level, assemblies=assemblies)

    with Path(filename).open("w") as f:
        yaml.safe_dump(manifest, f, sort_keys=False, default_flow_style=False)

    log.info(
        "wrote parts manifest of %d parts (%.1f kg total) to %s",
        len(manifest["parts"]),
        manifest["totals"]["mass"] / 1000,
        filename,
    )
