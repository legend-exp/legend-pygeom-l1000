from __future__ import annotations

from importlib import resources
from typing import NamedTuple

from legendmeta import AttrsDict, LegendMetadata, TextDB
from pyg4ometry import geant4
from pygeomtools import detectors, geometry, visualization
from pygeomtools.utils import load_dict_from_config

from . import cryo, fibers, hpge_strings, materials, watertank

lmeta = LegendMetadata()
configs = TextDB(resources.files("l1000geom") / "configs")

DEFINED_ASSEMBLIES = ["watertank", "cryostat", "HPGe_dets", "fiber_curtain"]


class InstrumentationData(NamedTuple):
    mother_lv: geant4.LogicalVolume
    """Argon LogicalVolume instance in which all components are to be placed."""
    mother_pv: geant4.PhysicalVolume
    """Argon PhysicalVolume instance in which all components are to be placed."""
    mother_z_displacement: float
    """The z-displacement of the mother volume."""
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


def construct(
    assemblies: list[str] = DEFINED_ASSEMBLIES,
    detail_level: str = "close_detector",
    config: dict | None = None,
) -> geant4.Registry:
    """Construct the LEGEND-1000 geometry and return the pyg4ometry Registry containing the world volume."""
    if set(assemblies) - set(DEFINED_ASSEMBLIES) != set():
        msg = "invalid geometrical assembly specified"
        raise ValueError(msg)

    config = config if config is not None else {}

    channelmap = load_dict_from_config(config, "channelmap", lambda: AttrsDict(configs["channelmap.json"]))
    special_metadata = load_dict_from_config(
        config, "special_metadata", lambda: AttrsDict(configs["special_metadata.yaml"])
    )

    if detail_level not in special_metadata["detail"]:
        msg = "invalid detail level specified"
        raise ValueError(msg)

    detail = special_metadata["detail"][detail_level]

    if "cryostat" not in assemblies and {"HPGe_dets", "fiber_curtain"} & set(assemblies):
        msg = "invalid geometrical assembly specified. Cryostat must be included if HPGe_dets or fiber_curtain are included"
        raise ValueError(msg)

    # If the user does not specify anything the assemblies will be the default list, so a check is not necessary
    for system in detail:
        if system not in assemblies:
            detail[system] = "omit"

    reg = geant4.Registry()
    mats = materials.OpticalMaterialRegistry(reg)

    # Create the world volume
    world_material = geant4.MaterialPredefined("G4_Galactic")
    world = geant4.solid.Box("world", 30, 30, 30, reg, "m")
    world_lv = geant4.LogicalVolume(world, world_material, "world", reg)
    reg.setWorld(world_lv)

    # This object will be used and edited by all subsystems and then passed to the next subsystem
    instr = InstrumentationData(
        world_lv, None, 0, mats, reg, channelmap, special_metadata, AttrsDict(config), detail
    )
    # Create and place the structures
    # NamedTuples are immutable, so we need to take copies of instr
    instr = watertank.construct_and_place_tank(instr)
    instr = cryo.construct_and_place_cryostat(instr)
    hpge_strings.place_hpge_strings(instr)  # Does not edit InstrumentationData
    fibers.place_fiber_modules(instr)

    _assign_common_copper_surface(instr)

    detectors.write_detector_auxvals(reg)
    visualization.write_color_auxvals(reg)
    geometry.check_registry_sanity(reg, reg)

    return reg


def _assign_common_copper_surface(b: InstrumentationData) -> None:
    if hasattr(b.materials, "_metal_copper") is None:
        return
    surf = None
    cu_mat = b.materials.metal_copper

    for _, pv in b.registry.physicalVolumeDict.items():
        if pv.motherVolume != b.mother_lv or pv.logicalVolume.material != cu_mat:
            continue
        if surf is None:
            surf = b.materials.surfaces.to_copper

        geant4.BorderSurface("bsurface_lar_cu_" + pv.name, b.mother_pv, pv, surf, b.registry)
        geant4.BorderSurface("bsurface_cu_lar_" + pv.name, pv, b.mother_pv, surf, b.registry)
