"""Construct the instrumentation inside of the water tank.

Dimensions from latest CAD from 2025-01-24.
"""

from __future__ import annotations

from math import pi

import numpy as np
import pyg4ometry.geant4 as g4
from scipy.spatial.transform import Rotation as R

from . import core, watertank

# The reflective Teflon foil that separates the active optical volume
teflon_outer_radius = 5000  # rough estimation, the real radius should be smaller than this value
# Some trygonometry to get the effective height of the teflon foil
offset = (
    watertank.tank_horizontal_wall
)  # The water is shifted this much up in z-direction, as the tank wall starts at z=0.
out = watertank.tank_base_radius - watertank.tank_vertical_wall - teflon_outer_radius
h_diff = watertank.tank_top_height - watertank.tank_base_height
inner = watertank.tank_base_radius - offset - watertank.tank_top_bulge_width / 2
teflon_effective_height = (
    watertank.tank_base_height - 4 * offset + out * h_diff / inner
)  # Accurate would be 2*offset, to be safe we take 4*offset


# The PMT parts
# The PMTs are the R7081-20-100 from Hammamatsu
# https://hep.hamamatsu.com/content/dam/hamamatsu-photonics/sites/documents/99_SALES_LIBRARY/etd/LARGE_AREA_PMT_TPMH1376E.pdf
pmt_eff_radius = (
    131  # Best value to fit the spherical part to 250mm diameter. The technical drawing is very unclear.
)
cutoff = 41  # Cutoff to take the top part of the ellipsoid resulting in 250mm diameter.
cathode_cutoff = 65  # cutoff such that the effective cathode radius is 220mm.
pmt_base_height = 145


def construct_PMT_front(window_mat: g4.Material, vac_mat: g4.Material, reg: g4.Registry) -> g4.LogicalVolume:
    """Construct the solids for the front part of the PMT.
    Consists of glass window, vacuum and cathode.
    These solids should be placed as mother-to-daughter: window <- vacuum <- cathode
    """
    # Borosilcate glass window of the PMT
    pmt_window = g4.solid.Ellipsoid(
        "PMT_window", pmt_eff_radius, pmt_eff_radius, pmt_eff_radius, cutoff, 200, reg, "mm"
    )

    vacuum_radius = 128  # Results in a glass window thickness of ~2-3mm
    vacuum_height = pmt_eff_radius - 2
    # The vacuum inside of the PMT window
    pmt_vacuum = g4.solid.Ellipsoid(
        "PMT_vacuum", vacuum_radius, vacuum_radius, vacuum_height, cutoff, 200, reg, "mm"
    )
    # The actual sensitive part of the PMT. Optical hits will be registered once they hit this volume
    pmt_cathode = g4.solid.Ellipsoid(
        "PMT_cathode", vacuum_radius, vacuum_radius, vacuum_height, cathode_cutoff, 200, reg, "mm"
    )

    pmt_window_lv = g4.LogicalVolume(pmt_window, window_mat, "PMT_window", reg)
    pmt_window_lv.pygeom_color_rgba = [0.9, 0.8, 0.5, 0.5]
    pmt_vacuum_lv = g4.LogicalVolume(pmt_vacuum, vac_mat, "PMT_vacuum", reg)
    pmt_cathode_lv = g4.LogicalVolume(pmt_cathode, vac_mat, "PMT_cathode", reg)
    pmt_cathode_lv.pygeom_color_rgba = [0.545, 0.271, 0.074, 1]

    # Already place all of the daughters in the Mother.
    # This has to be taken into considerations when specifying them as detectors,
    # As only one physical volume instance of the sensitive detector is created.
    g4.PhysicalVolume([0, 0, 0], [0, 0, 0], pmt_vacuum_lv, "PMT_vacuum", pmt_window_lv, reg)
    g4.PhysicalVolume([0, 0, 0], [0, 0, 0], pmt_cathode_lv, "PMT_cathode", pmt_vacuum_lv, reg)
    return pmt_window_lv


def construct_PMT_back(base_mat: g4.Material, reg: g4.Registry) -> g4.LogicalVolume:
    base_r = 42.25  # values roughly measured from the CAD.
    r = [0, base_r, base_r, 52.25, 102.75, 125, 0]
    z = [0, 0, 72, 82, 110, pmt_base_height, pmt_base_height]
    pmt_base = g4.solid.GenericPolycone("PMT_base", 0, 2 * pi, r, z, reg, "mm")

    return g4.LogicalVolume(pmt_base, base_mat, "PMT_base", reg)


def construct_teflon_foil(mat: g4.Material, instr: core.InstrumentationData) -> g4.LogicalVolume:
    teflon_metadata = instr.special_metadata["watertank_instrumentation"]["teflon"]

    teflon_solid = g4.solid.Polyhedra(
        "teflon_foil",
        0,
        2 * pi,
        teflon_metadata["faces"],
        1,
        [0, teflon_effective_height],
        [teflon_metadata["r"], teflon_metadata["r"]],
        [teflon_metadata["r"] + 3, teflon_metadata["r"] + 3],  # 3mm thickness?
        instr.registry,
        "mm",
    )
    return g4.LogicalVolume(teflon_solid, mat, "teflon_foil", instr.registry)


def get_euler_angles(target_direction: np.array):
    """
    Calculate the Euler angles to rotate the default direction to the target direction.
    The default direction is [0, 0, 1]
    """
    default_direction = np.array([0, 0, 1])

    rotation_axis = np.cross(default_direction, target_direction)

    # Calculate the angle using the dot product
    cos_angle = np.dot(default_direction, target_direction)
    angle = np.arccos(cos_angle)

    # If angle is 0 or 180, no rotation is needed or full rotation is needed
    if np.abs(angle) < 1e-6:
        return [0, 0, 0]
    if np.abs(angle - np.pi) < 1e-6:
        # Special case for 180 degree rotation, any axis is valid, pick (1, 0, 0)
        return [np.pi, 0, 0]

    rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)

    # Create a rotation object
    rotation = R.from_rotvec(rotation_axis * angle)

    # Get the rotation matrix or Euler angles
    euler_angles = rotation.as_euler("xyz")
    return [euler_angles[0], euler_angles[1], euler_angles[2]]


def place_floor_pmts(
    pmt_window_lv: g4.LogicalVolume, pmt_base_lv: g4.LogicalVolume, instr: core.InstrumentationData
):
    for key, value in instr.channelmap.items():
        if "pmt" in key.lower() and value["location"]["name"] == "floor":
            loc = value["location"]
            target_direction = np.array(
                [loc["direction"]["nx"], loc["direction"]["ny"], loc["direction"]["nz"]]
            )
            g4.PhysicalVolume(
                get_euler_angles(target_direction),
                [
                    loc["x"],
                    loc["y"],
                    loc["z"] + offset + pmt_base_height - cutoff,
                ],  # Move the window up above the base
                pmt_window_lv,
                value["name"],
                instr.mother_lv,
                instr.registry,
            )
            target_direction = np.array(
                [loc["direction"]["nx"], loc["direction"]["ny"], loc["direction"]["nz"]]
            )
            g4.PhysicalVolume(
                get_euler_angles(target_direction),
                [loc["x"], loc["y"], loc["z"] + offset],
                pmt_base_lv,
                value["name"] + "_base",
                instr.mother_lv,
                instr.registry,
            )


def place_wall_pmts(pmt_window_lv: g4.LogicalVolume, instr: core.InstrumentationData):
    for key, value in instr.channelmap.items():
        if "pmt" in key.lower() and value["location"]["name"] == "wall":
            loc = value["location"]
            # Due to the cutoff of the ellipsoid
            # we need to move it in the looking direction after rotation
            x = loc["x"] + cutoff * loc["direction"]["nx"]
            y = loc["y"] + cutoff * loc["direction"]["ny"]
            z = loc["z"] + cutoff * loc["direction"]["nz"]
            target_direction = np.array(
                [loc["direction"]["nx"], loc["direction"]["ny"], loc["direction"]["nz"]]
            )
            g4.PhysicalVolume(
                get_euler_angles(target_direction),
                [x, y, z],
                pmt_window_lv,
                value["name"],
                instr.mother_lv,
                instr.registry,
            )


def construct_and_place_instrumentation(instr: core.InstrumentationData) -> g4.PhysicalVolume:
    """Construct and place the instrumentation inside of the water tank.

    Parameters
    ----------
    instr : core.InstrumentationData
        The instrumentation data object containing the current state of the geometry.
    """
    if "watertank_instrumentation" not in instr.detail:
        msg = "No 'watertank_instrumentation' detail specified in the special metadata."
        raise ValueError(msg)

    if instr.detail["watertank_instrumentation"] == "omit":
        return instr

    # Construct the instrumentation
    # Materials are temporary here
    vac_mat = g4.MaterialPredefined("G4_Galactic")

    teflon_lv = construct_teflon_foil(instr.materials.teflon, instr)
    teflon_lv.pygeom_color_rgba = [0, 0, 0, 0.20]
    g4.PhysicalVolume(
        [0, 0, 0], [0, 0, 2 * offset], teflon_lv, "teflon_foil", instr.mother_lv, instr.registry
    )
    pmt_window_lv = construct_PMT_front(instr.materials.borosilicate, vac_mat, instr.registry)
    pmt_base_lv = construct_PMT_back(instr.materials.epoxy, instr.registry)
    pmt_base_lv.pygeom_color_rgba = [0, 0, 0, 1]

    place_floor_pmts(pmt_window_lv, pmt_base_lv, instr)
    place_wall_pmts(pmt_window_lv, instr)

    return instr
