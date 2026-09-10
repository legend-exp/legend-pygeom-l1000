"""Construct the instrumentation inside of the water tank.

Dimensions from latest CAD from 2025-01-24.
"""

from __future__ import annotations

import warnings
import weakref
from math import pi

import numpy as np
import pyg4ometry.config as pyg4_config
import pyg4ometry.geant4 as g4
from pygeomtools import RemageDetectorInfo
from scipy.spatial.transform import Rotation as R

from . import core, materials, watertank
from .utils import COLORS

# This is some rough calculation of the effective height of the tyvek foil inside of the tank.
# This is to avoid overlaps with the curved top part of the water tank, while keeping the gap as
# small as possible.
tyvek_outer_radius = 4000  # rough estimation, the real radius should be smaller than this value
offset = watertank.tank_horizontal_wall
out = watertank.tank_base_radius - watertank.tank_vertical_wall - tyvek_outer_radius
h_diff = watertank.tank_top_height - watertank.tank_base_height
inner = watertank.tank_base_radius - offset - watertank.tank_top_bulge_width / 2
tyvek_effective_height = (
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
pmt_tyvek_gap = 1.0  # mm

# The PMT ellipsoids deliberately do not follow the global mesh slice/stack setting. That setting
# exists to keep the few large vessels (tank, cryostat) smooth, but there are several hundred PMTs,
# and pyg4ometry keeps one mesh per *logical volume* rather than per solid, both when meshing and in
# the viewer. At 300 slices that is ~180k polygons per PMT and over 100M triangles in the scene. A
# PMT is a quarter of a metre wide in a scene of tens of metres, so it never covers more than a few
# pixels and this tessellation is indistinguishable from a finer one.
pmt_mesh_slices = 32
pmt_mesh_stacks = 16


def construct_PMT_front(
    vac_mat: g4.Material,
    surfaces: materials.surfaces.OpticalSurfaceRegistry,
    reg: g4.Registry,
) -> g4.LogicalVolume:
    """Construct the solids for the front part of the PMT.
    Consists of glass window, vacuum and cathode.
    These solids should be placed as mother-to-daughter: window <- vacuum <- cathode
    """
    # Borosilcate glass window of the PMT
    pmt_window = g4.solid.Ellipsoid(
        "waterinstr_pmt_window_borosilicate",
        pmt_eff_radius,
        pmt_eff_radius,
        pmt_eff_radius,
        cutoff,
        200,
        reg,
        "mm",
        nslice=pmt_mesh_slices,
        nstack=pmt_mesh_stacks,
    )

    vacuum_radius = 128  # Results in a glass window thickness of ~2-3mm
    vacuum_height = pmt_eff_radius - 2
    # The vacuum inside of the PMT window
    pmt_vacuum = g4.solid.Ellipsoid(
        "waterinstr_pmt_interior_vacuum",
        vacuum_radius,
        vacuum_radius,
        vacuum_height,
        cutoff,
        200,
        reg,
        "mm",
        nslice=pmt_mesh_slices,
        nstack=pmt_mesh_stacks,
    )
    # The actual sensitive part of the PMT. Optical hits will be registered once they hit this volume
    pmt_cathode = g4.solid.Ellipsoid(
        "waterinstr_pmt_cathode",
        vacuum_radius,
        vacuum_radius,
        vacuum_height,
        cathode_cutoff,
        200,
        reg,
        "mm",
        nslice=pmt_mesh_slices,
        nstack=pmt_mesh_stacks,
    )

    pmt_cathode_lv = g4.LogicalVolume(pmt_cathode, vac_mat, "waterinstr_pmt_cathode", reg)
    pmt_cathode_lv.pygeom_color_rgba = COLORS["pmt_cathode"]
    g4.SkinSurface("pmt_cathode_surface", pmt_cathode_lv, surfaces.to_photocathode, reg)

    # Already place all of the daughters in the Mother.
    # This has to be taken into considerations when specifying them as detectors,
    # As only one physical volume instance of the sensitive detector is created.

    return [pmt_window, pmt_vacuum, pmt_cathode_lv]


def construct_PMT_back(base_mat: g4.Material, reg: g4.Registry) -> g4.LogicalVolume:
    base_r = 42.25  # values roughly measured from the CAD.
    r = [0, base_r, base_r, 52.25, 102.75, 125, 0]
    z = [0, 0, 72, 82, 110, pmt_base_height, pmt_base_height]
    pmt_base = g4.solid.GenericPolycone("waterinstr_pmt_base_epoxy", 0, 2 * pi, r, z, reg, "mm")

    return g4.LogicalVolume(pmt_base, base_mat, "waterinstr_pmt_base_epoxy", reg)


def construct_tyvek_foil(mat: g4.Material, instr: core.InstrumentationData) -> g4.LogicalVolume:
    tyvek_metadata = instr.special_metadata["watertank_instrumentation"]["tyvek"]

    tyvek_solid = g4.solid.Polyhedra(
        "waterinstr_reflector_tyvek",
        0,
        2 * pi,
        tyvek_metadata["faces"],
        1,
        [0, tyvek_effective_height],
        [tyvek_metadata["r"], tyvek_metadata["r"]],
        [tyvek_metadata["r"] + 3, tyvek_metadata["r"] + 3],  # 3mm thickness?
        instr.registry,
        "mm",
    )
    return g4.LogicalVolume(tyvek_solid, mat, "waterinstr_reflector_tyvek", instr.registry)


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
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        euler_angles = rotation.as_euler("xyz")
    return [euler_angles[0], euler_angles[1], euler_angles[2]]


# ``g4.LogicalVolume`` tessellates its solid inside the constructor, and it does not cache the
# result per solid. Every PMT needs its own chain of logical volumes (see :func:`place_PMT_front`),
# so the same two ellipsoids would otherwise be meshed once per PMT. At the fine mesh settings used
# for the documentation images a single ellipsoid takes seconds, which turns the few hundred PMTs
# into a run of tens of minutes. The copies are geometrically identical, so mesh each solid once and
# hand that mesh to all of them.
_shared_meshes: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _logical_volume_sharing_mesh(
    solid: g4.solid.SolidBase, material: g4.Material, name: str, reg: g4.Registry
) -> g4.LogicalVolume:
    """Construct a :class:`g4.LogicalVolume`, meshing each distinct solid only once.

    Overlap checking clones the daughter meshes before transforming them, so sharing is safe
    there. The one shared piece of state it writes is the list of overlap meshes that
    ``checkOverlaps`` hangs off the mother's mesh for visualisation, which the copies then show
    for each other. That affects only what the viewer draws in red, not what is detected.
    """
    mesh = _shared_meshes.get(solid)
    if mesh is None:
        lv = g4.LogicalVolume(solid, material, name, reg)
        # on a meshing error pyg4ometry leaves ``mesh`` at None; storing that is harmless, it just
        # means the next copy is built the ordinary way.
        _shared_meshes[solid] = lv.mesh
        return lv

    do_meshing = pyg4_config.doMeshing
    pyg4_config.doMeshing = False
    try:
        lv = g4.LogicalVolume(solid, material, name, reg)
    finally:
        pyg4_config.doMeshing = do_meshing
    lv.mesh = mesh
    return lv


def place_PMT_front(
    rotation: list,
    translation: list,
    pmt_volumes: list,
    name: str,
    mother_lv: g4.LogicalVolume,
    reg: g4.Registry,
    instr: core.InstrumentationData,
    rawid: int,
) -> g4.PhysicalVolume:
    """
    Since the PMT is a compound volume, we need to place the PMT window, vacuum and cathode separately.
    Due to the Geant4 handles copies of Logical Volumes, we need to create new Logical Volumes for each sensitive PMT.
    """
    # In order to have unique PMT physical volumes, we need to re-create the mother logical volumes.
    window_name = f"waterinstr_pmt_window_borosilicate_{name}"
    vacuum_name = f"waterinstr_pmt_interior_vacuum_{name}"
    pmt_window_lv = _logical_volume_sharing_mesh(
        pmt_volumes[0], instr.materials.borosilicate, window_name, reg
    )
    pmt_window_lv.pygeom_color_rgba = COLORS["pmt_window"]
    pmt_vacuum_lv = _logical_volume_sharing_mesh(pmt_volumes[1], instr.materials.vacuum, vacuum_name, reg)
    # the vacuum would fill the PMT no matter how transparent the glass around it is.
    pmt_vacuum_lv.pygeom_color_rgba = False

    # We have to place the new logical volumes for every single PMT
    g4.PhysicalVolume([0, 0, 0], [0, 0, 0], pmt_vacuum_lv, vacuum_name, pmt_window_lv, reg)
    pmt_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], pmt_volumes[2], name, pmt_vacuum_lv, reg)
    pmt_pv.set_pygeom_active_detector(RemageDetectorInfo("optical", rawid))

    return g4.PhysicalVolume(rotation, translation, pmt_window_lv, window_name, mother_lv, reg)


def place_floor_pmts(pmt_volumes: list, pmt_base_lv: g4.LogicalVolume, instr: core.InstrumentationData):
    for key, value in instr.channelmap.items():
        if "pmt" in key.lower() and value["location"]["name"] == "floor":
            loc = value["location"]
            target_direction = np.array(
                [loc["direction"]["nx"], loc["direction"]["ny"], loc["direction"]["nz"]]
            )
            rawid = value["daq"]["rawid"]
            place_PMT_front(
                get_euler_angles(target_direction),
                [
                    loc["x"],
                    loc["y"],
                    loc["z"] + offset + pmt_base_height - cutoff,
                ],  # Move the window up above the base
                pmt_volumes,
                value["name"],
                instr.mother_lv,
                instr.registry,
                instr,
                rawid,
            )

            g4.PhysicalVolume(
                get_euler_angles(target_direction),
                [loc["x"], loc["y"], loc["z"] + offset],
                pmt_base_lv,
                f"waterinstr_pmt_base_epoxy_{value['name']}",
                instr.mother_lv,
                instr.registry,
            )


def place_wall_pmts(pmt_volumes: list, instr: core.InstrumentationData):
    for key, value in instr.channelmap.items():
        if "pmt" in key.lower() and value["location"]["name"] == "wall":
            loc = value["location"]
            # Due to the cutoff of the ellipsoid
            # we need to move it in the looking direction after rotation
            # The PMTs look inwards, so the offset is applied along the outward face normal.
            wall_offset = cutoff - pmt_tyvek_gap
            x = loc["x"] + wall_offset * loc["direction"]["nx"]
            y = loc["y"] + wall_offset * loc["direction"]["ny"]
            z = loc["z"] + wall_offset * loc["direction"]["nz"]
            target_direction = np.array(
                [loc["direction"]["nx"], loc["direction"]["ny"], loc["direction"]["nz"]]
            )
            rawid = value["daq"]["rawid"]
            place_PMT_front(
                get_euler_angles(target_direction),
                [x, y, z],
                pmt_volumes,
                value["name"],
                instr.mother_lv,
                instr.registry,
                instr,
                rawid,
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

    tyvek_lv = construct_tyvek_foil(instr.materials.tyvek, instr)
    tyvek_lv.pygeom_color_rgba = COLORS["tyvek"]
    g4.SkinSurface("tyvek_surface", tyvek_lv, instr.materials.surfaces.to_tyvek, instr.registry)
    g4.PhysicalVolume(
        [0, 0, 0], [0, 0, 2 * offset], tyvek_lv, "waterinstr_reflector_tyvek", instr.mother_lv, instr.registry
    )
    pmt_volumes = construct_PMT_front(instr.materials.vacuum, instr.materials.surfaces, instr.registry)
    pmt_base_lv = construct_PMT_back(instr.materials.epoxy, instr.registry)
    pmt_base_lv.pygeom_color_rgba = [0, 0, 0, 1]
    g4.SkinSurface("pmt_back_surface", pmt_base_lv, instr.materials.surfaces.to_steel, instr.registry)

    place_floor_pmts(pmt_volumes, pmt_base_lv, instr)
    place_wall_pmts(pmt_volumes, instr)

    return instr
