from __future__ import annotations

from importlib import resources

from legendmeta import LegendMetadata, TextDB
from pyg4ometry import geant4

from . import cryo, materials

lmeta = LegendMetadata()
configs = TextDB(resources.files("l1000geom") / "configs")

DEFINED_ASSEMBLIES = ["strings", "fibers"]


def construct(
    assemblies: list[str] = DEFINED_ASSEMBLIES,
    #    use_detailed_fiber_model: bool = False,
) -> geant4.Registry:
    """Construct the LEGEND-1000 geometry and return the pyg4ometry Registry containing the world volume."""
    if set(assemblies) - set(DEFINED_ASSEMBLIES) != set():
        msg = "invalid geometrical assembly specified"
        raise ValueError(msg)

    reg = geant4.Registry()
    mats = materials.OpticalMaterialRegistry(reg)

    # Create the world volume
    world_material = geant4.MaterialPredefined("G4_Galactic")
    world = geant4.solid.Box("world", 20, 20, 20, reg, "m")
    world_lv = geant4.LogicalVolume(world, world_material, "world", reg)
    reg.setWorld(world_lv)

    # TODO: Shift the global coordinate system that z=0 is a reasonable value for defining hit positions.
    coordinate_z_displacement = 0

    # Implement Cavern here
    # Implement water tank here

    # Create basic structure with argon and cryostat.
    cryostat_lv = cryo.construct_cryostat(mats.metal_steel, reg)
    cryo.place_cryostat(cryostat_lv, world_lv, coordinate_z_displacement, reg)

    lar_lv = cryo.construct_argon(mats.liquidargon, reg)
    lar_pv = cryo.place_argon(lar_lv, cryostat_lv, coordinate_z_displacement, reg)

    return reg


"""

    channelmap = lmeta.channelmap("20230311T235840Z")

    # Place the germanium detector array inside the liquid argon
    hpge_string_config = configs.on("20230311T235840Z")

    if "strings" in assemblies:
        hpge_strings.place_hpge_strings(channelmap, hpge_string_config, 1950, lar_lv, reg)

    # build fiber modules
    if "fibers" in assemblies:
        fiber_modules = lmeta.hardware.detectors.lar.fibers
        fibers.place_fiber_modules(
            fiber_modules, channelmap, lar_lv, lar_pv, mats, reg, use_detailed_fiber_model
        )

"""
