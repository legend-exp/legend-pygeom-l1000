"""Construct the LEGEND-1000 water tank including the water volume.

Dimensions from technical drawings 'Water Tank 12m Dia - Pit Version' approved by M. Busch 16 July 2024.

Latest Changes: 24.01.2025 Eric Esch
"""

from __future__ import annotations

from math import pi

import numpy as np
import pyg4ometry.geant4 as g4

from . import core, cryo

# Everything in mm
# Basic tank
tank_pit_radius = 5000  # Radius of the outer tank wall inside icarus pit
tank_vertical_wall = 10.0
tank_horizontal_wall = 20.0  # If i read the drawing correctly the horizontal wall is thicker
tank_base_radius = 12000.0 / 2  # Radius of the base of the tank
tank_pit_height = 800.0  # Height of the icarus pit
tank_central_part_height = 8877.6  # This is the height of the central part
tank_base_height = (
    tank_central_part_height + tank_pit_height
)  # This is the difference between top part and pit start

# Tank top is a little more complicated
tank_top_height = 9409.8 + tank_pit_height  # This value is therefore equal to the entire tank height.
tank_top_bulge_width = 3330.0  # width of the bulged rectangle on top of the tank
tank_top_bulge_depth = 169.2
# Technically there is also an outer radius for the bulge, but i am not sure for what
tank_top_bulge_radius = 3025.0  # radius of the bulged sections

# Flanges on top of the tank
tank_flange_height = 9976.1 + tank_pit_height  # Height of the flange on top of the tank
tank_flange_position_radius = 10600.0 / 2

# This is just some extra height so that the reentrance tube does not overlap with the cryo
# This is just guessed for now.
Reentrance_tube_height = 250.0

# Think of the manhole as a square with curved top/bottom (geometric term is 'stadium')
# Where to place the manhole
tank_manhole_height = 920.0  # The height of the lower line of the square compared to the tank base
tank_manhole_angle = 55.0  # The angle of the manhole position compared to the tank axis
# Dimensions of manhole
tank_manhole_square_height = 600.0  # The height of the square part of the manhole
tank_manhole_square_inner_width = 800.0  # The inner part is where the actual hole will be
tank_manhole_square_outer_width = 1000.0  # The outer part is some cladding around the hole
tank_manhole_inner_radius = 400.0  # The inner radius of the curved part of the manhole
tank_manhole_outer_radius = 500.0  # The outer radius of the curved part of the manhole
tank_manhole_depth = 135.37  # How far the manhole extends outside the tank (from cad)

# Missing: Top catwalk


def construct_base(
    name: str, reg: g4.Registry, v_wall: float = 0.0, h_wall: float = 0.0, neck_safety: float = 0.0
) -> g4.solid:
    """Construct the base shape of the tank.

    name: Prefix to add to the volume name
    v_wall: The thickness of the vertical walls of the tank
    h_wall: The thickness of the horizontal walls of the tank

    The returned polycone will be the base of the tank with the vertical and horizontal walls 'shaved' off."""

    tank_top_bulge_hwidth = tank_top_bulge_width / 2
    tank_top_bulge_height = tank_top_height - tank_top_bulge_depth
    r_base = [
        0,
        tank_pit_radius - v_wall,
        tank_pit_radius - v_wall,
        tank_base_radius - v_wall,
        tank_base_radius - v_wall,
        tank_top_bulge_hwidth + v_wall,
        tank_top_bulge_hwidth + v_wall,
        cryo.NECKRADIUS_START - neck_safety,
        cryo.NECKRADIUS_START - neck_safety,
        0,
    ]
    z_base = [
        h_wall,
        h_wall,
        tank_pit_height + h_wall,
        tank_pit_height + h_wall,
        tank_base_height - h_wall,
        tank_top_height - h_wall,
        tank_top_bulge_height - h_wall,
        tank_top_bulge_height - h_wall,
        tank_top_bulge_height - h_wall + Reentrance_tube_height,
        tank_top_bulge_height - h_wall + Reentrance_tube_height,
    ]
    return g4.solid.GenericPolycone(name + "_base", 0, 2 * pi, r_base, z_base, reg, "mm")


def construct_bulge(
    name: str, base: g4.solid, reg: g4.Registry, v_wall: float = 0.0, h_wall: float = 0.0
) -> g4.solid:
    """Construct the bulge on top of the tank.

    name: Prefix to add to the volume name
    base: The base to which this bulge will be added (or rather subtracted)
    v_wall: The thickness of the vertical walls of the tank
    h_wall: The thickness of the horizontal walls of the tank

    """

    bulge_sc_angle = np.arcsin(
        (tank_top_bulge_width / 2) / tank_top_bulge_radius
    )  # Angle of the bulged section
    bulge_y = np.cos(bulge_sc_angle) * tank_top_bulge_radius * 2
    bulge_box = g4.solid.Box(
        name + "_top_bulge_box",
        bulge_y + 2 * v_wall,
        tank_top_bulge_width + 2 * v_wall,
        tank_top_bulge_depth,
        reg,
        "mm",
    )
    bulge_semicircle = g4.solid.Tubs(
        name + "_top_bulge_semic",
        tank_top_bulge_width / 2 - 10,  # -10 to ensure the surfaces are not shared
        tank_top_bulge_radius + v_wall,
        tank_top_bulge_depth,
        -bulge_sc_angle,
        2 * bulge_sc_angle,
        reg,
        "mm",
    )
    bulge_step1 = g4.solid.Subtraction(
        name + "_top_bulge_step1",
        base,
        bulge_box,
        [[0, 0, 0], [0, 0, tank_top_height - (tank_top_bulge_depth / 2 + h_wall)]],
        reg,
    )
    bulge_step2 = g4.solid.Subtraction(
        name + "_top_bulge_step2",
        bulge_step1,
        bulge_semicircle,
        [[0, 0, 0], [0, 0, tank_top_height - (tank_top_bulge_depth / 2 + h_wall)]],
        reg,
    )

    return g4.solid.Subtraction(
        name + "_top_bulge",
        bulge_step2,
        bulge_semicircle,
        [[0, 0, pi], [0, 0, tank_top_height - (tank_top_bulge_depth / 2 + h_wall)]],
        reg,
    )


def construct_flange(base: g4.solid, reg: g4.Registry, n: int = 4) -> g4.solid:
    """Construct the flange solid to be placed on top of the tank.
    Constructed from 6 boolean operations and therefore probably not very run-time efficient in G4.

    base: The base of the tank to which the flanges will be added.
    n: Number of flanges to add to the tank. Default is 4."""

    if n > 32:
        msg = "Too many flanges. This will cause overlapps."
        raise ValueError(msg)

    # Parameters are directly read out of the L1000 CAD model generated 17.04.2024
    r_flange_base = [299.5, 304.5, 304.5, 390, 390, 161.5, 161.5, 222.5, 222.5, 158.5, 158.5, 299.5]
    z_flange_base = [0, 0, 923, 923, 995, 995, 1067, 1067, 1095, 1095, 923, 923]
    flange_base = g4.solid.GenericPolycone(
        "tank_flange_base", 0, 2 * pi, r_flange_base, z_flange_base, reg, "mm"
    )

    # The horizontal flange thingis
    flange_extra_height = 957
    r_flange_extras = [205.5, 282.5, 282.5, 209.5, 209.5, 282.5, 282.5, 205.5]
    z_flange_extras = [0, 0, 32, 32, 925, 925, flange_extra_height, flange_extra_height]
    flange_extras = g4.solid.GenericPolycone(
        "tank_flange_extras", 0, 2 * pi, r_flange_extras, z_flange_extras, reg, "mm"
    )

    # This is where the fun begins
    z_offset = tank_base_height + 544

    flange_last = base

    for i in range(n):
        angle = (45 + i * (360 / n)) * pi / 180
        flange_x = tank_flange_position_radius * np.sin(angle)
        flange_y = tank_flange_position_radius * np.cos(angle)
        flange_new = g4.solid.Union(
            "tank_flange_step" + str(i) + "1",
            flange_last,
            flange_base,
            [[0, 0, angle], [flange_x, flange_y, tank_base_height]],
            reg,
        )
        y_offset = flange_extra_height / 2 * np.cos(angle)
        x_offset = flange_extra_height / 2 * np.sin(angle)
        flange_last = g4.solid.Union(
            "tank_flange_step" + str(i) + "2",
            flange_new,
            flange_extras,
            [[pi / 2, 0, angle], [flange_x - x_offset, flange_y + y_offset, z_offset]],
            reg,
        )

        flange_new = g4.solid.Union(
            "tank_flange_step1" + str(i) + "3",
            flange_last,
            flange_extras,
            [[0, pi / 2, angle], [flange_x - y_offset, flange_y - x_offset, z_offset]],
            reg,
        )
        flange_last = flange_new

    return flange_last


def construct_manhole(base: g4.solid, reg: g4.Registry):
    """Construct the manhole solid.

    base: The base of the tank to which the manhole will be added.
    """
    curvature_safety = (
        200  # Add some extra space to account for the curvature. Due to the union this will not matter
    )

    mh_depth = tank_manhole_depth + curvature_safety
    mh_box = g4.solid.Box(
        "tank_manhole_box", tank_manhole_square_inner_width, tank_manhole_square_height, mh_depth, reg, "mm"
    )

    mh_semicircle = g4.solid.Tubs(
        "tank_manhole_semic", 0, tank_manhole_inner_radius, mh_depth, 0, 2 * pi, reg, "mm"
    )

    mh_z_position = tank_manhole_square_height + tank_pit_height + tank_manhole_square_height / 2
    mh_rad = tank_manhole_angle * pi / 180
    mh_x_position = -(tank_base_radius + mh_depth / 2 - curvature_safety) * np.sin(mh_rad)
    mh_y_position = (tank_base_radius + mh_depth / 2 - curvature_safety) * np.cos(mh_rad)

    tank_high_step2 = g4.solid.Union(
        "tank_manhole_step1",
        base,
        mh_box,
        [[pi / 2, 0, mh_rad], [mh_x_position, mh_y_position, mh_z_position]],
        reg,
    )
    tank_high_step3 = g4.solid.Union(
        "tank_manhole_step2",
        tank_high_step2,
        mh_semicircle,
        [[pi / 2, 0, mh_rad], [mh_x_position, mh_y_position, mh_z_position + tank_manhole_square_height / 2]],
        reg,
    )

    return g4.solid.Union(
        "tank_manhole_step3",
        tank_high_step3,
        mh_semicircle,
        [[pi / 2, 0, mh_rad], [mh_x_position, mh_y_position, mh_z_position - tank_manhole_square_height / 2]],
        reg,
    )


def construct_tank(tank_material: g4.Material, reg: g4.Registry, detail: str = "simple") -> g4.LogicalVolume:
    """Construct the tank volume.

    detail: Level of tank detail. Can be 'simple' or 'detailed'.
    simple: Only the base polycone of the tank is constructed.
    detailed: Base, Bulge, Manhole and Flanges are constructed.
    """

    base = construct_base("tank", reg)
    if detail == "simple":
        return g4.LogicalVolume(base, tank_material, "tank", reg)

    tank_medium = construct_bulge("tank", base, reg)

    if detail != "detailed":
        msg = "invalid tank detail level specified"
        raise ValueError(msg)

    tank_high_flange = construct_flange(tank_medium, reg)
    tank_high_final = construct_manhole(tank_high_flange, reg)

    return g4.LogicalVolume(tank_high_final, tank_material, "tank", reg)


def construct_and_place_tank(instr: core.InstrumentationData) -> core.InstrumentationData:
    if "watertank" not in instr.detail:
        msg = "No 'watertank' detail specified in the special metadata."
        raise ValueError(msg)

    if instr.detail["watertank"] == "omit":
        return instr
    tank_lv = construct_tank(instr.materials.metal_steel, instr.registry, instr.detail["watertank"])
    tank_lv.pygeom_color_rgba = False
    g4.SkinSurface("tank_steel_surface", tank_lv, instr.materials.surfaces.to_tyvek, instr.registry)
    # Polycones are placed with the bottom positioned at the given coordinates.
    # But we want it such that the polycone is centered around (0,0,0)
    # Displace it so the center of the middle straight part is at (0,0,0)
    tank_z_displacement = -(tank_pit_height + tank_central_part_height / 2.0)

    g4.PhysicalVolume(
        [0, 0, 0],
        [instr.mother_x_displacement, 0, tank_z_displacement + instr.mother_z_displacement],
        tank_lv,
        "tank",
        instr.mother_lv,
        instr.registry,
    )

    water_lv = construct_water(instr.materials.water, instr.registry, instr.detail["watertank"])
    water_lv.pygeom_color_rgba = [0, 0, 1, 0.2]
    water_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], water_lv, "water", tank_lv, instr.registry)

    # NamedTuples are immutable, so we need to create a copy
    return instr._replace(mother_lv=water_lv, mother_pv=water_pv, mother_z_displacement=tank_z_displacement)


def construct_water(
    water_material: g4.Material, reg: g4.Registry, detail: str = "simple"
) -> g4.LogicalVolume:
    """Construct the water volume.

    detail: Level of tank detail. Can be 'simple' or 'detailed'.
    simple: Only the base polycone of the water is constructed.
    detailed: The base polycone and the bulge on top of the tank are constructed.
    """
    base = construct_base(
        "water", reg, v_wall=tank_vertical_wall, h_wall=tank_horizontal_wall, neck_safety=1e-9
    )
    if detail == "simple":
        return g4.LogicalVolume(base, water_material, "tank_water", reg)

    water = construct_bulge("water", base, reg, v_wall=tank_vertical_wall, h_wall=tank_horizontal_wall)
    return g4.LogicalVolume(water, water_material, "tank_water", reg)
