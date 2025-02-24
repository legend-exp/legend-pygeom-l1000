from __future__ import annotations

from math import pi

import pyg4ometry.geant4 as g4

from . import core


def construct_and_place_cavern_and_labs(instr: core.InstrumentationData) -> None:
    """Construct and place the cavern and labs."""

    if "cavern" not in instr.detail:
        msg = "No 'cavern' detail specified in the special metadata."
        raise ValueError(msg)

    if "labs" not in instr.detail:
        msg = "No 'labs' detail specified in the special metadata."
        raise ValueError(msg)

    if instr.detail["cavern"] != "omit":
        cavern_lv = construct_cavern(instr.materials.rock, instr.registry, instr.mother_lv)
        cavern_extent = cavern_lv.extent(includeBoundingSolid=True)
        watertank_offset = 8877.6 / 2.0
        cavern_z_displacement = (
            cavern_extent[0][2] + watertank_offset + 1000 + 0.01
        )  # world_extent[1][2] - cavern_extent[1][2]
        g4.PhysicalVolume(
            [0, 0, 0], [0, 0, -cavern_z_displacement], cavern_lv, "cavern", instr.mother_lv, instr.registry
        )

    if instr.detail["labs"] != "omit":
        text = "Labs are not implemented yet."
        raise NotImplementedError(text)


#        labs_lv = construct_labs(instr.materials.metal_steel, instr.registry, instr.detail["labs"])
#        labs_z_displacement = 0
#        g4.PhysicalVolume(
#            [0, 0, 0], [0, 0, labs_z_displacement], labs_lv, "labs", instr.mother_lv, instr.registry
#        )


def construct_cavern(
    material: g4.Material, registry: g4.Registry, world_lv: g4.LogicalVolume
) -> g4.LogicalVolume:
    """Construct the cavern geometry."""

    world_extent = world_lv.extent(includeBoundingSolid=True)
    x_length = world_extent[1][0] - world_extent[0][0]

    total_height = 19450  # mm
    total_width = 18500  # mm
    onset_of_curvature = 10600  # mm
    distance_center_to_end_of_tunnle = 17600  # mm (this is rought guess)
    if distance_center_to_end_of_tunnle > x_length / 2.0:
        distance_center_to_end_of_tunnle = x_length / 2.0

    height_rock_above = 5000  # mm
    height_rock_below = 1000  # mm

    tank_pit_radius = 9950.0 / 2 + 0.01  # Radius of the outer tank wall inside icarus pit
    tank_pit_height = 800.0 + 0.01  # Height of the icarus pit

    z_length_smaller = total_height + height_rock_above + height_rock_below

    cavern_box = g4.solid.Box(
        "cavern_box",
        (world_extent[1][0] - world_extent[0][0]) - 0.01,
        (world_extent[1][1] - world_extent[0][1]) - 0.01,
        z_length_smaller,
        registry,
        "mm",
    )

    box_cutout_x = x_length / 2 + distance_center_to_end_of_tunnle
    box_cutput_y = total_width
    box_cutout_z = onset_of_curvature

    cavern_box_cutout = g4.solid.Box(
        "cavern_box_cutout",
        box_cutout_x,
        box_cutput_y,
        box_cutout_z,
        registry,
        "mm",
    )

    tube_cutout_h = box_cutout_x / 2.0
    tube_cutout_r_1 = total_height - onset_of_curvature
    tube_cutout_r_2 = total_width / 2.0

    cavern_cutout_tube = g4.solid.EllipticalTube(
        "cavern_cutout_tube", tube_cutout_r_1, tube_cutout_r_2, tube_cutout_h, registry, "mm"
    )

    cavern_cutout_icarus = g4.solid.Tubs(
        "cavern_cutout_icarus", 0, tank_pit_radius, tank_pit_height, 0, 2 * pi, registry, "mm"
    )

    box_z_offset = (
        onset_of_curvature / 2.0 + height_rock_below - z_length_smaller / 2.0
    )  # box_cutout_z - total_height) / 2. #-5000
    box_x_offset = (box_cutout_x - x_length) / 2.0
    cavern_box_wo_box = g4.solid.Subtraction(
        "cavern_box_wo_box",
        cavern_box,
        cavern_box_cutout,
        [[0, 0, 0], [box_x_offset, 0, box_z_offset]],
        registry,
    )

    tube_z_offset = (
        box_z_offset - box_cutout_z / 2.0 + total_height - tube_cutout_r_1
    )  # box_z_offset + onset_of_curvature/2.
    cavern_box_wo_box_and_tube = g4.solid.Subtraction(
        "cavern_box_wo_box_and_tube",
        cavern_box_wo_box,
        cavern_cutout_tube,
        [[0, pi / 2.0, 0], [box_x_offset, 0, tube_z_offset]],
        registry,
    )

    icarus_offset = box_z_offset - box_cutout_z / 2.0 - tank_pit_height / 2.0
    cavern_box_wo_box_and_tube_and_icarus = g4.solid.Subtraction(
        "cavern_box_wo_box_and_tube_and_icarus",
        cavern_box_wo_box_and_tube,
        cavern_cutout_icarus,
        [[0, 0, 0], [0, 0, icarus_offset]],
        registry,
    )

    return g4.LogicalVolume(cavern_box_wo_box_and_tube_and_icarus, material, "cavern", registry)
