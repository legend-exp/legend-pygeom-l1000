"""Construct the LEGEND-1000 water tank including the water volume.

Dimensions from technical drawings 'Water Tank 12m Dia - Pit Version' approved by M. Busch 16 July 2024. 

Latest Changes: 17.01.2025 Eric Esch
"""

from __future__ import annotations

from math import pi

import numpy as np
import pyg4ometry.geant4 as g4
import pyg4ometry


# Everything in mm
# Basic tank
tank_pit_radius = 9950. / 2 # Radius of the outer tank wall inside icarus pit
tank_vertical_wall = 10.
tank_horizontal_wall = 20. # If i read the drawing correctly the horizontal wall is thicker
tank_base_radius = 12000. / 2 # Radius of the base of the tank
tank_pit_height = 800. # Height of the icarus pit
tank_base_height = 8877.6 + tank_pit_height # height being the z position with regards to the tank bottom at z = 0

# Tank top is a little more complicated
tank_top_height = 9409.8 + tank_pit_height # This value is therefore equal to the entire tank height.
tank_top_bulge_width = 3330. # width of the bulged rectangle on top of the tank
tank_top_bulge_depth = 169.2
#Technically there is also an outer radius for the bulge, but i am not sure for what
tank_top_bulge_radius = 3025. # radius of the bulged sections

# Flanges on top of the tank
tank_flange_height = 9976.1 + tank_pit_height # Height of the flange on top of the tank
tank_flange_position_radius = 10600. / 2

# Think of the manhole as a square with curved top/bottom (geometric term is 'stadium')
# Where to place the manhole
tank_manhole_height = 920. # The height of the lower line of the square compared to the tank base
tank_manhole_angle = 55. # The angle of the manhole position compared to the tank axis
# Dimensions of manhole
tank_manhole_square_height = 600. # The height of the square part of the manhole
tank_manhole_square_inner_width = 800. # The inner part is where the actual hole will be
tank_manhole_square_outer_width = 1000. # The outer part is some cladding around the hole
tank_manhole_inner_radius = 400. # The inner radius of the curved part of the manhole
tank_manhole_outer_radius = 500. # The outer radius of the curved part of the manhole
tank_manhole_depth = 135.37 # How far the manhole extends outside the tank (from cad)

# Missing: Top catwalk

def construct_base(name: str, reg: g4.Registry, v_wall: float = 0., h_wall: float = 0.) -> g4.solid:
    """ Construct the base shape of the tank. 
    
        v_wall: The thickness of the vertical walls of the tank
        h_wall: The thickness of the horizontal walls of the tank
        
        The returned polycone will be the base of the tank with the vertical and horizontal walls 'shaved' off."""

    tank_top_bulge_hwidth = tank_top_bulge_width / 2
    tank_top_bulge_height = tank_top_height - tank_top_bulge_depth
    r_base = [0, tank_pit_radius - v_wall, tank_pit_radius - v_wall,
              tank_base_radius - v_wall, tank_base_radius - v_wall, tank_top_bulge_hwidth + v_wall,
              tank_top_bulge_hwidth + v_wall, 0]
    z_base = [h_wall, h_wall, tank_pit_height + h_wall,
              tank_pit_height + h_wall, tank_base_height - h_wall, tank_top_height - h_wall,
              tank_top_bulge_height - h_wall, tank_top_bulge_height - h_wall]
    return g4.solid.GenericPolycone(name + "_base", 0, 2 * pi, r_base, z_base, reg, "mm")

def construct_bulge(name: str, reg: g4.Registry, v_wall: float = 0.) -> g4.solid:
    """ Construct the bulge on top of the tank. 
    
        v_wall: The thickness of the vertical walls of the tank
        
        No horizontal wall thickness needed, as that is already in the base shape.
        The bulge just needs to be appropriatly placed lower on the base shape."""

    bulge_sc_angle = np.arcsin((tank_top_bulge_width / 2) / tank_top_bulge_radius) # Angle of the bulged section
    bulge_y = np.cos(bulge_sc_angle) * tank_top_bulge_radius * 2
    bulge_box = g4.solid.Box(name + "_top_bulge_box", bulge_y + v_wall, tank_top_bulge_width + v_wall, tank_top_bulge_depth, reg, "mm")
    bulge_semicircle = g4.solid.Tubs(name + "_top_bulge_semic", 0, tank_top_bulge_radius + v_wall, tank_top_bulge_depth, -bulge_sc_angle, 2*bulge_sc_angle, reg, "mm")
    bulge_part = g4.solid.Union(name + "_top_bulge_part", bulge_box, bulge_semicircle, [[0, 0, 0], [0, 0, 0]], reg)
    return g4.solid.Union(name + "_top_bulge", bulge_part, bulge_semicircle, [[0, 0, pi], [0, 0, 0]], reg)

def construct_flange(seperate_flange: bool,reg: g4.Registry) -> g4.solid:
    """ Construct the flange solid to be placed on top of the tank. 
        Constructed from 6 boolean operations and therefore probably not very run-time efficient in G4.
        
        seperate_flange: If true the flange will have a cutoff at the bottom to be able to place it
        as seperate volume on top of the tank."""
    
    # Parameters are directly read out of the L1000 CAD model generated 17.04.2024
    r_flange_base = [299.5,304.5, 304.5,390,390,161.5,161.5,222.5,222.5,158.5,158.5,299.5]
    z_flange_base = [0    ,0    ,923   ,923,995,995  ,1067 ,1067 ,1095 ,1095 ,923  ,923]
    flange_base = g4.solid.GenericPolycone("tank_flange_base", 0, 2 * pi, r_flange_base, z_flange_base, reg, "mm")
    
    # flange with huge outer radius for intersections with the horizontal thingis
    r_flange_base2 = [299.5,1000,1000,390,390,161.5,161.5,222.5,222.5,158.5,158.5,299.5]
    flange_base2 = g4.solid.GenericPolycone("tank_flange_base2", 0, 2 * pi, r_flange_base2, z_flange_base, reg, "mm")

    # The horizontal flange thingis
    flange_extra_height = 957
    r_flange_extras = [205.5,282.5,282.5,209.5,209.5,282.5,282.5,205.5]
    z_flange_extras = [0    ,0    ,32   ,32   ,925  ,925  ,flange_extra_height  ,flange_extra_height  ]
    flange_extras = g4.solid.GenericPolycone("tank_flange_extras", 0, 2 * pi, r_flange_extras, z_flange_extras, reg, "mm")

    # Deletus tube to delete walls where they shouldnt be
    flange_removal_tube = g4.solid.Tubs("tank_flange_removal_tube", 0, 205.5, flange_extra_height, 0, 2*pi, reg, "mm")

    # This is where the fun begins
    z_offset = 544
    flange_int = g4.solid.Intersection("tank_flange_step1", flange_base2, flange_extras, [[pi / 2, 0, 0], [0, flange_extra_height/2, z_offset]], reg)
    flange_int2 = g4.solid.Intersection("tank_flange_step2", flange_base2, flange_extras, [[0, pi / 2, 0], [-flange_extra_height/2, 0, z_offset]], reg)
    flange_sub1 = g4.solid.Subtraction("tank_flange_step3", flange_base, flange_removal_tube, [[pi / 2, 0, 0], [0, 0, z_offset]], reg)
    flange_sub2 = g4.solid.Subtraction("tank_flange_step4", flange_sub1, flange_removal_tube, [[0, pi / 2, 0], [0, 0, z_offset]], reg)

    flange_U1 = g4.solid.Union("tank_flange_step5", flange_sub2, flange_int, [[0, 0, 0], [0, 0, 0]], reg)
    
    # If the flange should be a seperate volume also cutoff the bottom part, that is inside the tank
    if seperate_flange:
        r_cutoff = [0,tank_base_radius - (tank_top_bulge_width / 2),0]
        z_cutoff = [0,0, tank_top_height-tank_base_height]
        cutoff_pc = g4.solid.GenericPolycone("tank_flange_cutoff", 0, 2 * pi, r_cutoff, z_cutoff, reg, "mm")
        x_offset = tank_flange_position_radius - (tank_top_bulge_width / 2)
        flange_sub3 = g4.solid.Subtraction("tank_flange_step6", flange_U1, cutoff_pc, [[0, 0, 0], [x_offset, 0, 0]], reg)
        return g4.solid.Union("tank_flange_final", flange_sub3, flange_int2, [[0, 0, 0], [0, 0, 0]], reg)
    
    return g4.solid.Union("tank_flange_final", flange_U1, flange_int2, [[0, 0, 0], [0, 0, 0]], reg)

def construct_tank(tank_material: g4.Material, reg: g4.Registry, seperate_flange: bool = False) -> g4.LogicalVolume:
    """ Construct the tank volume. 
    
        seperate_flange: If true the flange will be returned as seperate volume.
        A flange has a lot of boolean operations so this might be more efficient."""

    base = construct_base("tank", reg)
    bulge = construct_bulge("tank", reg)
    flange = construct_flange(seperate_flange, reg)

    # Construct the manhole
    curvature_safety = 100 # Add some extra space to account for the curvature. Due to the union this will not matter
    mh_depth = tank_manhole_depth + curvature_safety
    mh_box = g4.solid.Box("tank_manhole_box", tank_manhole_square_inner_width, tank_manhole_square_height, mh_depth, reg, "mm")
    mh_semicircle = g4.solid.Tubs("tank_manhole_semic", 0, tank_manhole_inner_radius, mh_depth, 0, 2*pi, reg, "mm")
    mh_part = g4.solid.Union("tank_manhole_part", mh_box, mh_semicircle, [[0, 0, 0], [0, tank_manhole_square_height / 2, 0]], reg)
    mh = g4.solid.Union("tank_manhole", mh_part, mh_semicircle, [[0, 0, 0], [0, -tank_manhole_square_height / 2, 0]], reg)

    # Attach extras to the base tank
    mh_z_position = tank_manhole_square_height + tank_pit_height + tank_manhole_square_height / 2
    mh_rad = tank_manhole_angle * pi / 180
    mh_x_position = -(tank_base_radius + mh_depth / 2 - curvature_safety) *np.sin(mh_rad)
    mh_y_position = (tank_base_radius + mh_depth / 2 - curvature_safety) *np.cos(mh_rad)

    tank_step1 = g4.solid.Union("tank_step1", base, mh, [[pi/2, 0, mh_rad], [mh_x_position, mh_y_position, mh_z_position]], reg) 
    tank_last = g4.solid.Subtraction("tank", tank_step1, bulge, [[0, 0, 0], [0, 0, tank_top_height - tank_top_bulge_depth /2]], reg)
    

    if seperate_flange:
        return g4.LogicalVolume(tank_last, tank_material, "tank", reg), g4.LogicalVolume(flange, tank_material, "flange", reg)
    
    # If flange is not seperate add flanges to the tank solid
    for i in range(4):
        angle = (45 + i * 90) * pi / 180
        flange_x = tank_flange_position_radius * np.sin(angle)
        flange_y = tank_flange_position_radius * np.cos(angle)
        tank_new = g4.solid.Union("tank_step" + str(i+2), tank_last, flange, [[0, 0, angle], [flange_x, flange_y, tank_base_height]], reg)
        tank_last = tank_new

    return g4.LogicalVolume(tank_last, tank_material, "tank", reg)
    

def place_tank(
    tank_lv: g4.LogicalVolume,
    wl: g4.LogicalVolume,
    tank_displacement_z: float,
    reg: g4.Registry,
) -> g4.PhysicalVolume:
    tank_pv = g4.PhysicalVolume(
        [0, 0, 0], [0, 0, tank_displacement_z], tank_lv, "tank", wl, reg
    )
    return tank_pv

def construct_water(water_material: g4.Material, reg: g4.Registry) -> g4.LogicalVolume:
    base = construct_base("water", reg, v_wall=tank_vertical_wall, h_wall=tank_horizontal_wall)
    bulge = construct_bulge("water", reg, v_wall=40.)
    water = g4.solid.Subtraction("tank_water", base, bulge, [[0, 0, 0], [0, 0, tank_top_height - (tank_top_bulge_depth /2 + tank_horizontal_wall)]], reg)
    return g4.LogicalVolume(water, water_material, "tank_water", reg)

def place_water(
    water_lv: g4.LogicalVolume,
    tank_lv: g4.LogicalVolume,
    reg: g4.Registry,
) -> g4.PhysicalVolume:
    water_pv = g4.PhysicalVolume(
        [0, 0, 0], [0, 0, 0], water_lv, "water", tank_lv, reg
    )
    return water_pv