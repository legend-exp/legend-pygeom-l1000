from __future__ import annotations

import logging
from typing import NamedTuple

from dbetto import AttrsDict
from pyg4ometry import geant4

from . import (
    cavern_and_labs,
    cryo,
    fibers,
    hpge_strings,
    materials,
    watertank,
    watertank_instrumentation,
)
from .config import effective_detail, resolve_config

logger = logging.getLogger(__name__)


class InstrumentationData(NamedTuple):
    mother_lv: geant4.LogicalVolume
    """Argon LogicalVolume instance in which all components are to be placed."""
    mother_pv: geant4.PhysicalVolume
    """Argon PhysicalVolume instance in which all components are to be placed."""
    mother_z_displacement: float
    """The z-displacement of the mother volume."""
    mother_x_displacement: float
    """The x-displacement of the mother volume."""
    materials: materials.OpticalMaterialRegistry
    """Material properties for common materials"""
    registry: geant4.Registry
    """pyg4ometry registry instance."""

    channelmap: AttrsDict
    """LEGEND-1000 channel map containing germanium/spms detectors configuration in the string
    and their geometry."""
    special_metadata: AttrsDict
    """LEGEND-1000 special geometry metadata file. Used to reconstruct the spatial position of each
    string, detector and calibration tube."""
    runtime_config: AttrsDict
    """Volatile runtime config, settings that are not tied to a specific detector configuration."""

    detail: AttrsDict
    """The chosen detail level by the user. Used to navigate to the corresponding entry in the special metadata."""


def construct(config: dict | None = None) -> geant4.Registry:
    """Construct the LEGEND-1000 geometry and return the pyg4ometry Registry containing the world volume.

    Parameters
    ----------
    config
        the runtime configuration, as described in :doc:`/runtime-cfg`. It is resolved with
        :func:`pygeoml1000.config.resolve_config` first, so both a config as read from file and
        an already-resolved one are accepted. ``None`` builds the default geometry.
    """
    config = resolve_config(config)

    special_metadata = AttrsDict(config["special_metadata"])
    channelmap = AttrsDict(config["channelmap"])
    detail = AttrsDict(effective_detail(config))

    reg = geant4.Registry()
    mats = materials.OpticalMaterialRegistry(reg)

    # Create the world volume
    world_material = geant4.MaterialPredefined("G4_Galactic")
    world = geant4.solid.Box("world", 44, 44, 44, reg, "m")
    world_lv = geant4.LogicalVolume(world, world_material, "world", reg)
    reg.setWorld(world_lv)

    # This object will be used and edited by all subsystems and then passed to the next subsystem
    instr = InstrumentationData(
        world_lv, None, 0, 0, mats, reg, channelmap, special_metadata, AttrsDict(config), detail
    )
    # Create and place the structures
    # NamedTuples are immutable, so we need to take copies of instr
    instr = cavern_and_labs.construct_and_place_cavern_and_labs(instr)
    instr = watertank.construct_and_place_tank(instr)
    instr = watertank_instrumentation.construct_and_place_instrumentation(instr)
    instr = cryo.construct_and_place_cryostat(instr)
    hpge_strings.place_hpge_strings(instr)  # Does not edit InstrumentationData
    fibers.place_fiber_modules(instr)

    _assign_common_copper_surface(instr)

    return reg


def _assign_common_copper_surface(b: InstrumentationData) -> None:
    """Assign a common copper surface to all copper parts in the LAr volume."""
    if not hasattr(b.materials, "_metal_copper"):
        return

    surf = None
    cu_mat = b.materials.metal_copper

    for _, pv in b.registry.physicalVolumeDict.items():
        if (
            pv.motherVolume != b.mother_lv
            or not hasattr(pv.logicalVolume, "material")
            or pv.logicalVolume.material != cu_mat
        ):
            continue

        # only lazy-load the copper surface when we encounter a copper part.
        if surf is None:
            surf = b.materials.surfaces.to_copper

        # check that we do not have another surface already at this boundary.
        if any(
            isinstance(s, geant4.BorderSurface) and {b.mother_pv, pv} == {s.physref1, s.physref2}
            for s in b.registry.surfaceDict.values()
        ):
            continue

        geant4.BorderSurface("bsurface_lar_cu_" + pv.name, b.mother_pv, pv, surf, b.registry)
        geant4.BorderSurface("bsurface_cu_lar_" + pv.name, pv, b.mother_pv, surf, b.registry)
