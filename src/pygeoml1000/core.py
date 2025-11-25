from __future__ import annotations

import logging
from importlib import resources
from typing import NamedTuple

from dbetto import AttrsDict, TextDB
from pyg4ometry import geant4
from pygeomtools.utils import load_dict_from_config

from . import (
    cavern_and_labs,
    cryo,
    dummy_metadata_generator,
    fibers,
    hpge_strings,
    materials,
    watertank,
    watertank_instrumentation,
)

logger = logging.getLogger(__name__)
configs = TextDB(resources.files("pygeoml1000") / "configs")


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


def construct(
    assemblies: list[str] | None = None,
    detail_level: str = "radiogenic",
    config: dict | None = None,
) -> geant4.Registry:
    """Construct the LEGEND-1000 geometry and return the pyg4ometry Registry containing the world volume."""

    config = config if config is not None else {}

    # Try to load channelmap and special_metadata, with fallback to generate the data on the fly
    try:
        channelmap = load_dict_from_config(
            config, "channelmap", lambda: AttrsDict(configs["channelmap.json"])
        )
    except FileNotFoundError:
        # Fallback: generate dummy metadata objects directly
        logger.info("channelmap.json not found in configs directory, generating channelmap on the fly")
        channelmap_dict, special_metadata_dict = dummy_metadata_generator.generate_dummy_metadata()
        channelmap = AttrsDict(channelmap_dict)
    except Exception as e:
        msg = f"Error loading channelmap: {e}"
        raise RuntimeError(msg) from e

    try:
        special_metadata = load_dict_from_config(
            config, "special_metadata", lambda: AttrsDict(configs["special_metadata.yaml"])
        )
    except FileNotFoundError:
        # Fallback: use dummy metadata objects directly
        logger.info("special_metadata.yaml not found in configs directory, generating metadata on the fly")
        special_metadata = AttrsDict(special_metadata_dict)
    except Exception as e:
        msg = f"Error loading special_metadata: {e}"
        raise RuntimeError(msg) from e

    if detail_level not in special_metadata["detail"]:
        msg = "invalid detail level specified"
        raise ValueError(msg)

    detail = special_metadata["detail"][detail_level]
    if assemblies is not None:
        if set(assemblies) - set(detail) != set():
            msg = "invalid geometrical assembly specified"
            raise ValueError(msg)

        if "cryostat" not in assemblies and {"HPGe_dets", "fiber_curtain"} & set(assemblies):
            msg = "invalid geometrical assembly specified. Cryostat must be included if HPGe_dets or fiber_curtain are included"
            raise ValueError(msg)

        for system in detail:
            if system not in assemblies:
                detail[system] = "omit"

        # Enable systems that have been specified but are not in the detail level
        for system in assemblies:
            if detail[system] == "omit":
                detail[system] = "simple"

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
