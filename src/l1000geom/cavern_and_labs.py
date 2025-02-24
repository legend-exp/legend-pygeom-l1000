from __future__ import annotations

from math import pi

import numpy as np
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
            cavern_extent[0][2]  # lower edge of the cavern volume
            + watertank_offset  # base to center of the watertank (w/o icarus pit)
            + 1000  # width of rock below
            + 0.01  # safety margin
        )
        g4.PhysicalVolume(
            [0, 0, 0], [0, 0, -cavern_z_displacement], cavern_lv, "cavern", instr.mother_lv, instr.registry
        )

    if instr.detail["labs"] != "omit":
        text = "Labs are not implemented yet."
        raise NotImplementedError(text)


def construct_cavern(
    material: g4.Material, registry: g4.Registry, world_lv: g4.LogicalVolume
) -> g4.LogicalVolume:
    """
    Construct the cavern geometry.

    Positive x-axis is pointing towards north.
    """

    world_extent = world_lv.extent(includeBoundingSolid=True)
    world_lengths = np.array([world_extent[1][i] - world_extent[0][i] for i in range(3)])

    cavern_max_height = 19450  # mm
    cavern_width = 18500  # mm
    cavern_onset_of_curvature = 10600  # mm

    distance_center_to_end_of_tunnle = 17600  # mm (this is rought guess)
    if distance_center_to_end_of_tunnle > world_lengths[0] / 2.0:
        # this is a safety check, if the distance is larger than the cavern itself
        distance_center_to_end_of_tunnle = world_lengths[0] / 2.0

    rock_depth_above = 5000  # mm
    rock_depth_below = 1000  # mm
    rock_volume_height = cavern_max_height + rock_depth_above + rock_depth_below

    tank_pit_radius = 9950.0 / 2 + 0.01  # Radius of the outer tank wall inside icarus pit
    tank_pit_height = 800.0 + 0.01  # Height of the icarus pit

    rock = g4.solid.Box(
        "rock",
        (world_lengths[0]) - 0.01,
        (world_lengths[1]) - 0.01,
        rock_volume_height,
        registry,
        "mm",
    )

    box_cutout_x = world_lengths[0] / 2 + distance_center_to_end_of_tunnle
    box_cutput_y = cavern_width
    box_cutout_z = cavern_onset_of_curvature

    cavern_box_cutout = g4.solid.Box(
        "cavern_box_cutout",
        box_cutout_x,
        box_cutput_y,
        box_cutout_z,
        registry,
        "mm",
    )

    tube_cutout_h = box_cutout_x / 2.0
    tube_cutout_r_1 = cavern_max_height - cavern_onset_of_curvature
    tube_cutout_r_2 = cavern_width / 2.0

    cavern_cutout_tube = g4.solid.EllipticalTube(
        "cavern_cutout_tube", tube_cutout_r_1, tube_cutout_r_2, tube_cutout_h, registry, "mm"
    )

    cavern_cutout_icarus = g4.solid.Tubs(
        "cavern_cutout_icarus", 0, tank_pit_radius, tank_pit_height, 0, 2 * pi, registry, "mm"
    )

    offset_z_box = cavern_onset_of_curvature / 2.0 + rock_depth_below - rock_volume_height / 2.0
    box_x_offset = (box_cutout_x - world_lengths[0]) / 2.0
    rock_wo_box = g4.solid.Subtraction(
        "rock_wo_box",
        rock,
        cavern_box_cutout,
        [[0, 0, 0], [box_x_offset, 0, offset_z_box]],
        registry,
    )

    offset_z_tube = offset_z_box - box_cutout_z / 2.0 + cavern_max_height - tube_cutout_r_1
    rock_wo_box_and_tube = g4.solid.Subtraction(
        "rock_wo_box_and_tube",
        rock_wo_box,
        cavern_cutout_tube,
        [[0, pi / 2.0, 0], [box_x_offset, 0, offset_z_tube]],
        registry,
    )

    offset_z_icarus = offset_z_box - box_cutout_z / 2.0 - tank_pit_height / 2.0
    rock_wo_box_and_tube_and_icarus = g4.solid.Subtraction(
        "rock_wo_box_and_tube_and_icarus",
        rock_wo_box_and_tube,
        cavern_cutout_icarus,
        [[0, 0, 0], [0, 0, offset_z_icarus]],
        registry,
    )

    return g4.LogicalVolume(rock_wo_box_and_tube_and_icarus, material, "cavern", registry)
