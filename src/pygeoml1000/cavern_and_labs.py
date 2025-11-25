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
        cavern_max_height = 19450.0  # mm
        rock_depth_below = 1000.0  # mm
        rock_depth_above = 5000.0  # mm

        rock_lv = construct_rock(
            instr.materials.rock,
            instr.registry,
            instr.mother_lv,
            cavern_max_height,
            rock_depth_below,
            rock_depth_above,
        )
        rock_extent = rock_lv.extent(includeBoundingSolid=True)

        cavern_lv, cavern_x_offset = construct_cavern(
            instr.materials.rock,
            instr.registry,
            instr.mother_lv,
            cavern_max_height,
            rock_depth_below,
            rock_depth_above,
        )
        cavern_extent = cavern_lv.extent(includeBoundingSolid=True)

        rock_z_displacement = (
            rock_extent[0][2]  # lower edge of the cavern volume
            - cavern_extent[0][2]
        )
        rock_pv = g4.PhysicalVolume(
            [0, 0, 0], [0, 0, -rock_z_displacement], rock_lv, "rock", instr.mother_lv, instr.registry
        )
        instr = instr._replace(mother_lv=rock_lv, mother_pv=rock_pv, mother_z_displacement=0)

        # since we place the cavern inside the rock, we just need the relative offset from the center of the rock, i.e., the origin
        cavern_z_displacement = cavern_extent[0][2]
        cavern_pv = g4.PhysicalVolume(
            [0, 0, 0],
            [cavern_x_offset, 0, cavern_z_displacement],
            cavern_lv,
            "cavern",
            instr.mother_lv,
            instr.registry,
        )
        instr = instr._replace(
            mother_lv=cavern_lv,
            mother_pv=cavern_pv,
            mother_z_displacement=-800,
            mother_x_displacement=-cavern_x_offset,
        )

    if instr.detail["labs"] != "omit":
        text = "Labs are not implemented yet."
        raise NotImplementedError(text)

    return instr


def construct_rock(
    material: g4.Material,
    registry: g4.Registry,
    world_lv: g4.LogicalVolume,
    cavern_max_height: float,
    rock_depth_below: float,
    rock_depth_above: float,
) -> g4.LogicalVolume:
    world_extent = world_lv.extent(includeBoundingSolid=True)
    world_lengths = np.array([world_extent[1][i] - world_extent[0][i] for i in range(3)])

    # the rock is a box in which the cavern will be placed inside
    # the height of the rock volume is the cavern height plus the depth above and below
    rock_volume_height = cavern_max_height + rock_depth_above + rock_depth_below

    rock = g4.solid.Box(
        "rock",
        (world_lengths[0]) - 0.01,
        (world_lengths[1]) - 0.01,
        rock_volume_height,
        registry,
        "mm",
    )

    return g4.LogicalVolume(rock, material, "rock", registry)


def construct_cavern(
    material: g4.Material,
    registry: g4.Registry,
    world_lv: g4.LogicalVolume,
    cavern_max_height: float,
    rock_depth_below: float,
    rock_depth_above: float,
) -> g4.LogicalVolume:
    """
    Construct the cavern geometry.

    Positive x-axis is pointing towards north.
    """

    world_extent = world_lv.extent(includeBoundingSolid=True)
    world_lengths = np.array([world_extent[1][i] - world_extent[0][i] for i in range(3)])
    rock_volume_height = cavern_max_height + rock_depth_above + rock_depth_below

    cavern_width = 18500  # mm
    cavern_onset_of_curvature = 10600  # mm
    distance_center_to_end_of_tunnle = 17600  # mm (this is rought guess)
    distance_center_to_end_of_tunnle = min(distance_center_to_end_of_tunnle, world_lengths[0] / 2.0)

    # the cavern is a union of solids consisting of:
    # 1. a box for the boxy part near the floor
    # 2. an elliptical tube for the curved ceiling
    # 3. a cylindrical tube for the icarus pit

    # 1. box for the boxy part near the floor
    box_cavern_x = world_lengths[0] / 2 + distance_center_to_end_of_tunnle
    box_cavern_y = cavern_width
    box_cavern_z = cavern_onset_of_curvature

    cavern_box = g4.solid.Box(
        "cavern_box",
        box_cavern_x,
        box_cavern_y,
        box_cavern_z,
        registry,
        "mm",
    )

    # 2. elliptical tube for the curved ceiling
    tube_cavern_h = box_cavern_x / 2.0
    tube_cavern_r_1 = cavern_max_height - cavern_onset_of_curvature
    tube_cavern_r_2 = cavern_width / 2.0

    cavern_tube = g4.solid.EllipticalTube(
        "cavern_tube", tube_cavern_r_1, tube_cavern_r_2, tube_cavern_h, registry, "mm"
    )

    # 3. cylindrical tube for the icarus pit
    tank_pit_radius = 9950.0 / 2 + 0.1  # Radius of the outer tank wall inside icarus pit
    tank_pit_height = 800.0 + 0.1  # Height of the icarus pit

    cavern_icarus = g4.solid.Tubs(
        "cavern_icarus", 0, tank_pit_radius, tank_pit_height, 0, 2 * pi, registry, "mm"
    )

    # Now we create a union from those three solids with the box being the reference solid, i.e., its center is at the origin

    # these are the global offsets for the cavern box, tube and icarus pit
    offset_z_box = cavern_onset_of_curvature / 2.0 + rock_depth_below - rock_volume_height / 2.0
    box_x_offset = (box_cavern_x - world_lengths[0]) / 2.0 + 0.02
    offset_z_tube = offset_z_box - box_cavern_z / 2.0 + cavern_max_height - tube_cavern_r_1
    offset_z_icarus = offset_z_box - box_cavern_z / 2.0 - tank_pit_height / 2.0
    # in creating the unions, we need the relative offsets

    cavern_box_tube = g4.solid.Union(
        "cavern_box_tube",
        cavern_box,
        cavern_tube,
        [[0, np.pi / 2.0, 0], [0, 0, offset_z_tube - offset_z_box]],
        registry,
    )

    cavern_box_tube_icarus = g4.solid.Union(
        "cavern_box_tube_icarus",
        cavern_box_tube,
        cavern_icarus,
        [[0, 0, 0], [-box_x_offset, 0, offset_z_icarus - offset_z_box]],
        registry,
    )

    # Now we place this union inside the rock volume
    return g4.LogicalVolume(cavern_box_tube_icarus, material, "cavern", registry), box_x_offset
