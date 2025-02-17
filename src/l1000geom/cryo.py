"""Construct the LEGEND-1000/GERDA cryostat including the liquid argon volume.

Dimensions from [Knoepfle2022]_ and P. Krause.

.. [Knoepfle2022] T. Knöpfle and B. Schwingenheuer "Design and Performance of the GERDA
   Low-Background Cryostat for Operation in Water" In: Journal of Instrumentation 17 P02038
   (2022). https://doi.org/10.1088/1748-0221/17/02/P02038
"""

from __future__ import annotations

from math import pi

import pyg4ometry.geant4 as g4

from . import core

cryo_radius = 3976 / 2
cryo_wall = 12
cryo_tub_height = 3900
cryo_top_height = 826
cryo_bottom_height = 829

cryo_access_radius = 800 / 2
cryo_access_wall = 10
cryo_access_height = 1720
access_overlap = 200


def construct_cryostat(cryostat_material: g4.Material, reg: g4.Registry) -> g4.LogicalVolume:
    cryo_top = g4.solid.Tubs(
        "cryo_top",
        0,
        cryo_radius + cryo_wall,
        2 * cryo_top_height + 2 * cryo_wall,
        0,
        2 * pi,
        reg,
        "mm",
    )
    cryo_access_tub = g4.solid.Tubs(
        "cryo_access_tub",
        0,
        cryo_access_radius + cryo_access_wall,
        cryo_access_height + access_overlap,
        0,
        2 * pi,
        reg,
        "mm",
    )
    cryo_bottom = g4.solid.Tubs(
        "cryo_bottom",
        0,
        cryo_radius + cryo_wall,
        2 * cryo_bottom_height + 2 * cryo_wall,
        0,
        2 * pi,
        reg,
        "mm",
    )
    cryo_tub = g4.solid.Tubs("cryo_tub", 0, cryo_radius + cryo_wall, cryo_tub_height, 0, 2 * pi, reg, "mm")

    cryo1 = g4.solid.Union("cryo1", cryo_tub, cryo_top, [[0, 0, 0], [0, 0, cryo_tub_height / 2]], reg)
    cryo2 = g4.solid.Union("cryo2", cryo1, cryo_bottom, [[0, pi, 0], [0, 0, -cryo_tub_height / 2]], reg)
    cryo = g4.solid.Union(
        "cryostat",
        cryo2,
        cryo_access_tub,
        [
            [0, pi, 0],
            [0, 0, +cryo_tub_height / 2 + cryo_top_height + cryo_access_height / 2],
        ],
        reg,
    )

    return g4.LogicalVolume(cryo, cryostat_material, "cryostat", reg)


def construct_and_place_cryostat(instr: core.InstrumentationData) -> g4.PhysicalVolume:
    if "cryostat" not in instr.detail:
        msg = "No 'cryostat' detail specified in the special metadata."
        raise ValueError(msg)

    if instr.detail["cryostat"] == "omit":
        return instr
    cryostat_lv = construct_cryostat(instr.materials.metal_steel, instr.registry)
    # Move the cryostat back in a central position
    g4.PhysicalVolume(
        [0, 0, 0],
        [0, 0, -instr.mother_z_displacement],
        cryostat_lv,
        "cryostat",
        instr.mother_lv,
        instr.registry,
    )

    cryostat_lv.pygeom_color_rgba = False
    lar_lv = construct_argon(instr.materials.liquidargon, instr.registry)
    lar_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], lar_lv, "lar", cryostat_lv, instr.registry)
    lar_lv.pygeom_color_rgba = [0, 0, 0, 0.1]

    # NamedTuples are immutable, so we need to create a copy
    return instr._replace(mother_lv=lar_lv, mother_pv=lar_pv, mother_z_displacement=0)


def construct_argon(lar_material: g4.Material, reg: g4.Registry) -> g4.LogicalVolume:
    lar_access_height = cryo_access_height - 800
    lar_top = g4.solid.Ellipsoid(
        "lar_top",
        cryo_radius,
        cryo_radius,
        cryo_top_height,
        0,
        cryo_top_height,
        reg,
        "mm",
    )
    lar_access = g4.solid.Tubs(
        "lar_access",
        0,
        cryo_access_radius,
        lar_access_height + access_overlap,
        0,
        2 * pi,
        reg,
        "mm",
    )
    lar_bottom = g4.solid.Ellipsoid(
        "lar_bottom",
        cryo_radius,
        cryo_radius,
        cryo_bottom_height,
        0,
        cryo_bottom_height,
        reg,
        "mm",
    )
    lar_tub = g4.solid.Tubs("lar_tub", 0, cryo_radius, cryo_tub_height, 0, 2 * pi, reg, "mm")

    lar1 = g4.solid.Union("lar1", lar_tub, lar_top, [[0, 0, 0], [0, 0, cryo_tub_height / 2]], reg)
    lar2 = g4.solid.Union("lar2", lar1, lar_bottom, [[0, pi, 0], [0, 0, -cryo_tub_height / 2]], reg)
    lar = g4.solid.Union(
        "lar",
        lar2,
        lar_access,
        [
            [0, pi, 0],
            [0, 0, +cryo_tub_height / 2 + cryo_top_height + lar_access_height / 2],
        ],
        reg,
    )

    return g4.LogicalVolume(lar, lar_material, "lar", reg)
