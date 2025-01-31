from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from importlib import resources

import numpy as np
import pyg4ometry
from legendhpges import make_hpge
from legendmeta import AttrsDict
from pyg4ometry import geant4
from pygeomtools import RemageDetectorInfo
from scipy.spatial.transform import Rotation

from . import core, materials

log = logging.getLogger(__name__)


def place_hpge_strings(b: core.InstrumentationData) -> None:
    """Construct LEGEND-1000 HPGe strings."""
    # derive the strings from the channelmap.
    ch_map = b.channelmap.map("system", unique=False).geds.values()
    strings_to_build = {}

    for hpge_meta in ch_map:
        # Temporary fix for gedet with null enrichment value
        if hpge_meta.production.enrichment is None:
            log.warning("%s has no enrichment in metadata - setting to dummy value 0.86!", hpge_meta.name)
            hpge_meta.production.enrichment = 0.86

        hpge_string_id = str(hpge_meta.location.string)
        hpge_unit_id_in_string = hpge_meta.location.position

        if hpge_string_id not in strings_to_build:
            strings_to_build[hpge_string_id] = {}

        hpge_extra_meta = b.special_metadata.hpges[hpge_meta.name]
        strings_to_build[hpge_string_id][hpge_unit_id_in_string] = HPGeDetUnit(
            hpge_meta.name,
            hpge_meta.production.manufacturer,
            hpge_meta.daq.rawid,
            make_hpge(hpge_meta, b.registry),
            hpge_meta.geometry.height_in_mm,
            hpge_extra_meta["baseplate"],
            hpge_extra_meta["rodlength_in_mm"],
            hpge_meta,
        )

    # now, build all strings.
    for string_id, string in strings_to_build.items():
        _place_hpge_string(string_id, string, b)


@dataclass
class HPGeDetUnit:
    name: str
    manufacturer: str
    rawid: int
    lv: geant4.LogicalVolume
    height: float
    baseplate: str
    rodlength: float
    meta: AttrsDict


def _place_hpge_string(
    string_id: str,
    string_slots: list,
    b: core.InstrumentationData,
):
    """
    Place a single HPGe detector string.

    This includes all PEN plates and the nylon shroud around the string."""
    string_meta = b.special_metadata.hpge_string[string_id]

    angle_in_rad = math.pi * string_meta.angle_in_deg / 180
    x_pos = string_meta.radius_in_mm * math.cos(angle_in_rad) + string_meta.center.x_in_mm
    y_pos = -string_meta.radius_in_mm * math.sin(angle_in_rad) + string_meta.center.y_in_mm
    # rotation angle for anything in the string.
    string_rot = -np.pi + angle_in_rad
    string_rot_m = np.array(
        [[np.sin(string_rot), np.cos(string_rot)], [np.cos(string_rot), -np.sin(string_rot)]]
    )

    # offset the height of the string by the length of the string support rod.
    # z0_string is the upper z coordinate of the topmost detector unit.
    # TODO: REQUIRES XCHECK
    z0_string = b.top_plate_z_pos - 410.1 - 12

    # deliberately use max and range here. The code does not support sparse strings (i.e. with
    # unpopulated slots, that are _not_ at the end. In those cases it should produce a KeyError.
    max_unit_id = max(string_slots.keys())
    total_rod_length = 0
    for hpge_unit_id_in_string in range(1, max_unit_id + 1):
        det_unit = string_slots[hpge_unit_id_in_string]

        # convert the "warm" length of the rod to the (shorter) length in the cooled down state.
        total_rod_length += det_unit.rodlength * 0.997
        unit_length = det_unit.rodlength * 0.997

        z_unit_bottom = z0_string - total_rod_length

        # - note from CAD model: the distance between PEN plate top and detector bottom is 2.4 mm.
        pen_thickness = 2.4  #  mm
        clamp_thickness = 1.8  # mm
        cable_thickness = 0.076
        distance_det_to_pen = 2.4  # mm

        z_pos_clamp = z_unit_bottom + clamp_thickness / 2
        z_pos_cable = z_pos_clamp + clamp_thickness / 2 + cable_thickness / 2
        z_pos_pen = z_pos_cable + cable_thickness / 2 + pen_thickness / 2
        z_pos_det = z_pos_pen + pen_thickness / 2 + distance_det_to_pen

        det_pv = geant4.PhysicalVolume(
            [0, 0, 0],
            [x_pos, y_pos, z_pos_det],
            det_unit.lv,
            det_unit.name,
            b.mother_lv,
            b.registry,
        )
        det_pv.pygeom_active_dector = RemageDetectorInfo("germanium", det_unit.rawid, det_unit.meta)
        det_unit.lv.pygeom_color_rgba = (0, 1, 1, 1)

        # add germanium reflective surface.
        geant4.BorderSurface(
            "bsurface_lar_ge_" + det_pv.name,
            b.mother_pv,
            det_pv,
            b.materials.surfaces.to_germanium,
            b.registry,
        )

        baseplate = det_unit.baseplate
        # a lot of Ortec detectors have modified medium plates.
        if (
            det_unit.name.startswith("V")
            and det_unit.baseplate == "medium"
            and det_unit.manufacturer == "Ortec"
        ):
            # TODO: what is with "V01389A"?
            baseplate = "medium_ortec"
        pen_plate = _get_pen_plate(baseplate, b.materials, b.registry)

        # This rotation is not physical, but gets us closer to the real model of the PEN plates.
        # In the CAD model, most plates are mirrored, compared to reality (some are also correct in the
        # first place), i.e. how the plates in PGT were produced. So the STL mesh is also mirrored, so
        # flip it over.
        # note/TODO: this rotation should be replaced by a correct mesh, so that the counterbores are
        # on the correct side. This might be necessary to fit in other parts!
        pen_rot = Rotation.from_euler("XZ", [-math.pi, string_rot]).as_euler("xyz")
        pen_pv = geant4.PhysicalVolume(
            list(pen_rot),
            [x_pos, y_pos, z_pos_pen],
            pen_plate,
            det_unit.name + "_pen",
            b.mother_lv,
            b.registry,
        )
        _add_pen_surfaces(pen_pv, b.mother_pv, b.materials, b.registry)

        # add cable and clamp
        signal_cable, signal_clamp, signal_asic = _get_signal_cable_insulator_and_asic(
            det_unit.name, cable_thickness, clamp_thickness, unit_length, b.materials, b.mother_lv, b.registry
        )

        angle_signal = math.pi * 1 / 2.0 - string_rot
        clamp_to_origin = 2.5 + 4.0 + 1.5 + 5 / 2
        cable_to_origin = 2.5 + 4.0 + 16 / 2
        asic_to_origin = 2.5 + 4.0 + 11 + 1 / 2.0
        x_clamp = x_pos + clamp_to_origin * np.sin(string_rot)
        y_clamp = y_pos + clamp_to_origin * np.cos(string_rot)
        x_cable = x_pos + cable_to_origin * np.sin(string_rot)
        y_cable = y_pos + cable_to_origin * np.cos(string_rot)
        x_asic = x_pos + asic_to_origin * np.sin(string_rot)
        y_asic = y_pos + asic_to_origin * np.cos(string_rot)
        geant4.PhysicalVolume(
            [math.pi, 0, angle_signal],
            [x_cable, y_cable, z_pos_cable],  # this offset of 12 is measured from the CAD file.
            signal_cable,
            signal_cable.name + "_string_" + string_id,
            b.mother_lv,
            b.registry,
        )
        geant4.PhysicalVolume(
            [math.pi, 0, angle_signal],
            [x_clamp, y_clamp, z_pos_clamp],  # this offset of 12 is measured from the CAD file.
            signal_clamp,
            signal_clamp.name + "_string_" + string_id,
            b.mother_lv,
            b.registry,
        )
        geant4.PhysicalVolume(
            [math.pi, 0, angle_signal],
            [x_asic, y_asic, z_pos_cable + 0.5],  # this offset of 12 is measured from the CAD file.
            signal_asic,
            signal_asic.name + "_string_" + string_id,
            b.mother_lv,
            b.registry,
        )

        hv_cable, hv_clamp = _get_hv_cable_and_insulator(
            det_unit.name, cable_thickness, clamp_thickness, unit_length, b.materials, b.mother_lv, b.registry
        )

        angle_hv = math.pi * 1 / 2.0 + string_rot
        clamp_to_origin = 2.5 + 29.5 + 3.5 + 5 / 2
        cable_to_origin = 2.5 + 29.5 + 2.0 + 8 / 2
        x_clamp = x_pos - clamp_to_origin * np.sin(string_rot)
        y_clamp = y_pos - clamp_to_origin * np.cos(string_rot)
        x_cable = x_pos - cable_to_origin * np.sin(string_rot)
        y_cable = y_pos - cable_to_origin * np.cos(string_rot)

        geant4.PhysicalVolume(
            [0, 0, angle_hv],
            [x_clamp, y_clamp, z_pos_cable],
            hv_cable,
            hv_cable.name + "_string_" + string_id,
            b.mother_lv,
            b.registry,
        )
        geant4.PhysicalVolume(
            [0, 0, angle_hv],
            [x_clamp, y_clamp, z_pos_clamp],
            hv_clamp,
            hv_clamp.name + "_string_" + string_id,
            b.mother_lv,
            b.registry,
        )

    # the copper rod is slightly longer after the last detector.
    copper_rod_length_from_z0 = total_rod_length + 3.5
    copper_rod_length = copper_rod_length_from_z0 + 12

    support, tristar = _get_support_structure(string_slots[1].baseplate, b.materials, b.registry)
    geant4.PhysicalVolume(
        [0, 0, np.deg2rad(30) + string_rot],
        [x_pos, y_pos, z0_string + 12],  # this offset of 12 is measured from the CAD file.
        support,
        support.name + "_string_" + string_id,
        b.mother_lv,
        b.registry,
    )
    geant4.PhysicalVolume(
        [0, 0, string_rot],
        [x_pos, y_pos, z0_string + 12 - 1e-6],  # this offset of 12 is measured from the CAD file.
        tristar,
        tristar.name + "_string_" + string_id,
        b.mother_lv,
        b.registry,
    )

    copper_rod_r = string_meta.rod_radius_in_mm
    copper_rod_name = f"string_{string_id}_cu_rod"
    # the rod has a radius of 1.5 mm, but this would overlap with the coarse model of the PPC top PEN ring.
    copper_rod = geant4.solid.Tubs(copper_rod_name, 0, 1.43, copper_rod_length, 0, 2 * math.pi, b.registry)
    copper_rod = geant4.LogicalVolume(copper_rod, b.materials.metal_copper, copper_rod_name, b.registry)
    copper_rod.pygeom_color_rgba = (0.72, 0.45, 0.2, 1)
    for i in range(3):
        copper_rod_th = np.deg2rad(-30 - i * 120)
        delta = copper_rod_r * string_rot_m @ np.array([np.cos(copper_rod_th), np.sin(copper_rod_th)])
        geant4.PhysicalVolume(
            [0, 0, 0],
            [x_pos + delta[0], y_pos + delta[1], z0_string + 12 - copper_rod_length / 2],
            copper_rod,
            f"{copper_rod_name}_{i}",
            b.mother_lv,
            b.registry,
        )


def _get_pen_plate(
    size: str,
    materials: materials.OpticalMaterialRegistry,
    registry: geant4.Registry,
) -> geant4.LogicalVolume:
    if size not in ["small", "medium", "medium_ortec", "large", "xlarge", "ppc_small"]:
        msg = f"Invalid PEN-plate size {size}"
        raise ValueError(msg)

    # just for vis purposes...
    colors = {
        "small": (1, 0, 0, 1),
        "medium": (0, 1, 0, 1),
        "medium_ortec": (1, 0, 1, 1),
        "large": (0, 0, 1, 1),
        "xlarge": (1, 1, 0, 1),
        "ppc_small": (1, 0, 0, 1),
    }

    pen_lv_name = f"pen_{size}"
    if pen_lv_name not in registry.logicalVolumeDict:
        if size != "ppc_small":
            pen_file = resources.files("l1000geom") / "models" / f"BasePlate_{size}.stl"
        else:
            pen_file = resources.files("l1000geom") / "models" / "TopPlate_ppc.stl"

        pen_solid = pyg4ometry.stl.Reader(
            pen_file, solidname=f"pen_{size}", centre=False, registry=registry
        ).getSolid()
        pen_lv = geant4.LogicalVolume(pen_solid, materials.pen, pen_lv_name, registry)
        pen_lv.pygeom_color_rgba = colors[size]

    return registry.logicalVolumeDict[pen_lv_name]


def _get_support_structure(
    size: str,
    materials: materials.OpticalMaterialRegistry,
    registry: geant4.Registry,
) -> tuple[geant4.LogicalVolume, geant4.LogicalVolume]:
    """Get the (simplified) support structure and the tristar of the requested size.

    .. note :: Both models' coordinate origins are a the top face of the tristar structure."""
    if "string_support_structure" not in registry.logicalVolumeDict:
        support_file = resources.files("l1000geom") / "models" / "StringSupportStructure.stl"
        support_solid = pyg4ometry.stl.Reader(
            support_file, solidname="string_support_structure", centre=False, registry=registry
        ).getSolid()
        support_lv = geant4.LogicalVolume(
            support_solid, materials.metal_copper, "string_support_structure", registry
        )
        support_lv.pygeom_color_rgba = (0.72, 0.45, 0.2, 1)
    else:
        support_lv = registry.logicalVolumeDict["string_support_structure"]

    tristar_lv_name = f"tristar_{size}"
    if tristar_lv_name not in registry.logicalVolumeDict:
        pen_file = resources.files("l1000geom") / "models" / f"TriStar_{size}.stl"

        pen_solid = pyg4ometry.stl.Reader(
            pen_file, solidname=f"tristar_{size}", centre=False, registry=registry
        ).getSolid()
        tristar_lv = geant4.LogicalVolume(pen_solid, materials.pen, tristar_lv_name, registry)
        tristar_lv.pygeom_color_rgba = (0.72, 0.45, 0.2, 1)
    else:
        tristar_lv = registry.logicalVolumeDict[tristar_lv_name]

    return support_lv, tristar_lv


def _add_pen_surfaces(
    pen_pv: geant4.PhysicalVolume,
    mother_pv: geant4.LogicalVolume,
    mats: materials.OpticalMaterialRegistry,
    reg: geant4.Registry,
):
    # between LAr and PEN we need a surface in both directions.
    geant4.BorderSurface("bsurface_lar_pen_" + pen_pv.name, mother_pv, pen_pv, mats.surfaces.lar_to_pen, reg)
    geant4.BorderSurface("bsurface_tpb_pen_" + pen_pv.name, pen_pv, mother_pv, mats.surfaces.lar_to_pen, reg)


def _get_hv_cable_and_insulator(
    name: str,
    cable_thickness: float,
    clamp_thickness: float,
    cable_length: float,
    materials: materials.OpticalMaterialRegistry,
    mother_pv: geant4.LogicalVolume,
    reg: geant4.Registry,
):
    hv_cable_under_clamp = geant4.solid.Box(
        name + "_hv_cable_under_clamp",
        8,
        13,
        cable_thickness,
        reg,
        "mm",
    )
    hv_cable_clamp_to_curve = geant4.solid.Box(
        name + "_hv_cable_clamp_to_curve",
        5.5,
        2,
        cable_thickness,
        reg,
        "mm",
    )
    hv_cable_curve = geant4.solid.Tubs(
        name + "_hv_cable_curve", 3.08 - cable_thickness, 3.08, 2.0, 0, math.pi / 2.0, reg, "mm"
    )
    hv_cable_along_unit = geant4.solid.Box(
        name + "_hv_along_unit",
        cable_thickness,
        2.0,
        cable_length,
        reg,
        "mm",
    )
    hv_cable_part1 = geant4.solid.Union(
        name + "_hv_cable_part1",
        hv_cable_under_clamp,
        hv_cable_clamp_to_curve,
        [[0, 0, 0], [8 / 2.0 + 5.5 / 2.0, 0, 0]],
        reg,
    )
    hv_cable_part2 = geant4.solid.Union(
        name + "_hv_cable_part2",
        hv_cable_part1,
        hv_cable_curve,
        [[-np.pi / 2, 0, 0], [8 / 2.0 + 5.5, 0, 3.08]],
        reg,
    )
    hv_cable = geant4.solid.Union(
        name + "_hv_cable",
        hv_cable_part2,
        hv_cable_along_unit,
        [[0, 0, 0], [8 / 2.0 + 5.5 + 3.08 - cable_thickness, 0, cable_length / 2.0]],
        reg,
    )

    hv_clamp = geant4.solid.Box(
        name + "_hv_clamp",
        5,
        13,
        clamp_thickness,
        reg,
        "mm",
    )

    hv_cable_lv = geant4.LogicalVolume(
        hv_cable,
        materials.metal_copper,
        name + "_hv_cable",
        reg,
    )

    hv_clamp_lv = geant4.LogicalVolume(
        hv_clamp,
        materials.ultem,
        name + "_hv_clamp",
        reg,
    )

    return hv_cable_lv, hv_clamp_lv


def _get_signal_cable_insulator_and_asic(
    name: str,
    cable_thickness: float,
    clamp_thickness: float,
    cable_length: float,
    materials: materials.OpticalMaterialRegistry,
    mother_pv: geant4.LogicalVolume,
    reg: geant4.Registry,
):
    signal_cable_under_clamp = geant4.solid.Box(
        name + "_signal_cable_under_clamp",
        16,
        13,
        cable_thickness,
        reg,
        "mm",
    )
    signal_cable_clamp_to_curve = geant4.solid.Box(
        name + "_signal_cable_clamp_to_curve",
        23.25,
        2,
        cable_thickness,
        reg,
        "mm",
    )
    signal_cable_curve = geant4.solid.Tubs(
        name + "_signal_cable_curve", 3.08 - cable_thickness, 3.08, 2.0, 0, math.pi / 2.0, reg, "mm"
    )
    signal_cable_along_unit = geant4.solid.Box(
        name + "_signal_along_unit",
        cable_thickness,
        2.0,
        cable_length,
        reg,
        "mm",
    )
    signal_cable_part1 = geant4.solid.Union(
        name + "_signal_cable_part1",
        signal_cable_under_clamp,
        signal_cable_clamp_to_curve,
        [[0, 0, 0], [16 / 2.0 + 23.25 / 2.0, 0, 0]],
        reg,
    )
    signal_cable_part2 = geant4.solid.Union(
        name + "_signal_cable_part2",
        signal_cable_part1,
        signal_cable_curve,
        [[np.pi / 2, 0, 0], [16 / 2.0 + 23.25, 0, -3.08]],
        reg,
    )
    signal_cable = geant4.solid.Union(
        name + "_signal_cable",
        signal_cable_part2,
        signal_cable_along_unit,
        [[0, 0, 0], [16 / 2.0 + 23.25 + 3.08 - cable_thickness, 0, -3.08 - cable_length / 2.0]],
        reg,
    )

    signal_clamp_part1 = geant4.solid.Box(
        name + "_signal_clamp_part1",
        5,
        13,
        clamp_thickness,
        reg,
        "mm",
    )
    signal_clamp_part2 = geant4.solid.Box(
        name + "_signal_clamp_part2",
        9,
        2.5,
        clamp_thickness,
        reg,
        "mm",
    )
    signal_clamp_part3 = geant4.solid.Union(
        name + "_signal_clamp_part3",
        signal_clamp_part1,
        signal_clamp_part2,
        [[0, 0, 0], [5 / 2.0 + 9 / 2.0, 13 / 2.0 - 2.5 / 2.0, 0]],
        reg,
    )
    signal_clamp = geant4.solid.Union(
        name + "_signal_clamp",
        signal_clamp_part3,
        signal_clamp_part2,
        [[0, 0, 0], [5 / 2.0 + 9 / 2.0, -13 / 2.0 + 2.5 / 2.0, 0]],
        reg,
    )

    signal_asic = geant4.solid.Box(
        name + "_signal_asic",
        1,
        1,
        0.5,
        reg,
        "mm",
    )

    signal_cable_lv = geant4.LogicalVolume(
        signal_cable,
        materials.metal_copper,
        name + "_signal_cable",
        reg,
    )

    signal_clamp_lv = geant4.LogicalVolume(
        signal_clamp,
        materials.ultem,
        name + "_signal_clamp",
        reg,
    )

    signal_asic_lv = geant4.LogicalVolume(
        signal_asic,
        materials.silica,
        name + "_signal_asic",
        reg,
    )

    return signal_cable_lv, signal_clamp_lv, signal_asic_lv
