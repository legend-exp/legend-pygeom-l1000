from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from importlib import resources

import numpy as np
import pyg4ometry
from dbetto import AttrsDict
from pyg4ometry import geant4
from pygeomhpges import make_hpge
from pygeomtools import RemageDetectorInfo
from scipy.spatial.transform import Rotation

from . import core, materials

log = logging.getLogger(__name__)

# top of the top plate, this is still a dummy value! (Moved here from core)
# copper_rod_upper_end_z_pos = 11.1
# modified to keep relative distance with new tube


copper_rod_upper_end_z_pos = (
    4913.0  # max of underground lar
    + 107  # distance from outer cryostat max z to underground lar max z
    + 11.8  # distance from water tank max z to outer cryostat max z
    + 769  # distance from lock flange sealing surface to water tank max z
    - 5552.708  # distance from lock flange sealing surface to copper rod upper end
)

z_pos_dict = {
    "copper_rod_upper_end": copper_rod_upper_end_z_pos,
    "first_individual_copper_segment_upper_end": copper_rod_upper_end_z_pos - 27,
    "first_detector_bottom": copper_rod_upper_end_z_pos - 154.9,
    "sipm_upper_holding_structure_upper_end": copper_rod_upper_end_z_pos + 93 + 8,
}


def calculate_string_rotation(string_id: str, b: core.InstrumentationData) -> float:
    string_meta = b.special_metadata.hpge_string[string_id]
    angle_in_rad = math.pi * string_meta.angle_in_deg / 180
    x_pos = string_meta.radius_in_mm * math.cos(angle_in_rad) + string_meta.center.x_in_mm
    y_pos = -string_meta.radius_in_mm * math.sin(angle_in_rad) + string_meta.center.y_in_mm
    # rotation angle for anything in the string.
    string_rot = -np.pi + angle_in_rad
    string_rot_m = np.array(
        [[np.sin(string_rot), np.cos(string_rot)], [np.cos(string_rot), -np.sin(string_rot)]]
    )
    return {
        "string_rot": string_rot,
        "string_rot_m": string_rot_m,
        "x_pos": x_pos,
        "y_pos": y_pos,
        "string_meta": string_meta,
    }


def place_hpge_strings(b: core.InstrumentationData) -> None:
    """Construct LEGEND-1000 HPGe strings."""
    # derive the strings from the channelmap.
    if "HPGe_dets" not in b.detail:
        msg = "No 'HPGe_dets' detail specified in the special metadata."
        raise ValueError(msg)

    if b.detail["HPGe_dets"] == "omit":
        return

    if b.detail["HPGe_dets"] == "simple":
        msg = "simple HPGe_dets not implemented yet. Can build only from Legendmetadata. (Implement me!)"
        raise ValueError(msg)

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
            hpge_meta.geometry.radius_in_mm,
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
    radius: float
    baseplate: str
    rodlength: float
    meta: AttrsDict


def _place_front_end_and_insulators(
    det_unit: HPGeDetUnit,
    unit_length: float,
    string_info: dict,
    b: core.InstrumentationData,
    z_pos: dict,
    thickness: dict,
    parts_origin: dict,
):
    # add cable and clamp
    signal_cable, signal_clamp, signal_asic = _get_signal_cable_and_asic(
        det_unit.name,
        thickness["cable"],
        thickness["clamp"],
        unit_length,
        b.materials,
        b.mother_lv,
        b.registry,
    )
    signal_cable.pygeom_color_rgba = (0.72, 0.45, 0.2, 1)
    signal_clamp.pygeom_color_rgba = (0.3, 0.3, 0.3, 1)
    signal_asic.pygeom_color_rgba = (0.73, 0.33, 0.4, 1)

    angle_signal = math.pi * 1 / 2.0 - string_info["string_rot"]
    x_clamp, y_clamp = np.array([string_info["x_pos"], string_info["y_pos"]]) + parts_origin["signal"][
        "clamp"
    ] * np.array([np.sin(string_info["string_rot"]), np.cos(string_info["string_rot"])])
    x_cable, y_cable = np.array([string_info["x_pos"], string_info["y_pos"]]) + parts_origin["signal"][
        "cable"
    ] * np.array([np.sin(string_info["string_rot"]), np.cos(string_info["string_rot"])])
    x_asic, y_asic = np.array([string_info["x_pos"], string_info["y_pos"]]) + parts_origin["signal"][
        "asic"
    ] * np.array([np.sin(string_info["string_rot"]), np.cos(string_info["string_rot"])])

    geant4.PhysicalVolume(
        [math.pi, 0, angle_signal],
        [x_cable, y_cable, z_pos["cable"]],  # this offset of 12 is measured from the CAD file.
        signal_cable,
        signal_cable.name + "_string_" + string_info["string_id"],
        b.mother_lv,
        b.registry,
    )
    geant4.PhysicalVolume(
        [math.pi, 0, angle_signal],
        [x_clamp, y_clamp, z_pos["clamp"]],  # this offset of 12 is measured from the CAD file.
        signal_clamp,
        signal_clamp.name + "_string_" + string_info["string_id"],
        b.mother_lv,
        b.registry,
    )
    geant4.PhysicalVolume(
        [math.pi, 0, angle_signal],
        [
            x_asic,
            y_asic,
            z_pos["cable"] - thickness["cable"] - 0.5,
        ],  # this offset of 12 is measured from the CAD file.
        signal_asic,
        signal_asic.name + "_string_" + string_info["string_id"],
        b.mother_lv,
        b.registry,
    )

    hv_cable, hv_clamp = _get_hv_cable(
        det_unit.name,
        thickness["cable"],
        thickness["clamp"],
        unit_length,
        b.materials,
        b.mother_lv,
        b.registry,
    )
    hv_cable.pygeom_color_rgba = (0.72, 0.45, 0.2, 1)
    hv_clamp.pygeom_color_rgba = (0.3, 0.3, 0.3, 1)

    angle_hv = math.pi * 1 / 2.0 + string_info["string_rot"]
    x_clamp, y_clamp = np.array([string_info["x_pos"], string_info["y_pos"]]) - parts_origin["hv"][
        "clamp"
    ] * np.array([np.sin(string_info["string_rot"]), np.cos(string_info["string_rot"])])
    x_cable, y_cable = np.array([string_info["x_pos"], string_info["y_pos"]]) - parts_origin["hv"][
        "cable"
    ] * np.array([np.sin(string_info["string_rot"]), np.cos(string_info["string_rot"])])

    geant4.PhysicalVolume(
        [0, 0, angle_hv],
        [x_clamp, y_clamp, z_pos["cable"]],
        hv_cable,
        hv_cable.name + "_string_" + string_info["string_id"],
        b.mother_lv,
        b.registry,
    )
    geant4.PhysicalVolume(
        [0, 0, angle_hv],
        [x_clamp, y_clamp, z_pos["clamp"]],
        hv_clamp,
        hv_clamp.name + "_string_" + string_info["string_id"],
        b.mother_lv,
        b.registry,
    )

    insulator_top_length = string_info["string_meta"].rod_radius_in_mm - det_unit.radius + 1.5

    weldment, insulator = _get_weldment_and_insulator(
        det_unit,
        thickness["weldment"],
        thickness["insulator"],
        insulator_top_length,
        b.materials,
        b.registry,
    )
    weldment.pygeom_color_rgba = (0.6, 0.6, 0.6, 1)
    insulator.pygeom_color_rgba = (0.6, 0.6, 0.6, 1)

    for i in range(3):
        copper_rod_th = np.deg2rad(-30 - i * 120)
        pieces_th = string_info["string_rot"] + np.deg2rad(-(i + 1) * 120)
        delta_weldment = (
            (string_info["string_meta"].rod_radius_in_mm - 5.6)
            * string_info["string_rot_m"]
            @ np.array([np.cos(copper_rod_th), np.sin(copper_rod_th)])
        )
        delta_insulator = (
            (string_info["string_meta"].rod_radius_in_mm - (16.5 / 2.0 - 1.5))
            * string_info["string_rot_m"]
            @ np.array([np.cos(copper_rod_th), np.sin(copper_rod_th)])
        )
        geant4.PhysicalVolume(
            [0, 0, pieces_th],
            [
                string_info["x_pos"] + delta_weldment[0],
                string_info["y_pos"] + delta_weldment[1],
                z_pos["weldment"],
            ],
            weldment,
            f"{weldment.name}_{i}",
            b.mother_lv,
            b.registry,
        )
        geant4.PhysicalVolume(
            [0, 0, pieces_th],
            [
                string_info["x_pos"] + delta_insulator[0],
                string_info["y_pos"] + delta_insulator[1],
                z_pos["insulator"],
            ],
            insulator,
            f"{insulator.name}_{i}",
            b.mother_lv,
            b.registry,
        )


def _place_hpge_unit(
    z_unit_bottom: float,
    det_unit: HPGeDetUnit,
    unit_length: float,
    string_info: dict,
    thicknesses: dict,
    b: core.InstrumentationData,
):
    safety_margin = 0.001  # 0.001 # 1 micro meter

    pen_offset = -0.15  # mm

    z_pos = {
        "det": z_unit_bottom,
        "insulator": z_unit_bottom - thicknesses["insulator"] / 2.0 - safety_margin,
        "pen": z_unit_bottom
        - thicknesses["insulator"]
        - thicknesses["pen"] / 2.0
        - pen_offset
        - safety_margin * 2,
        "weldment": z_unit_bottom
        - thicknesses["insulator"]
        - thicknesses["pen"]
        - thicknesses["weldment"] / 2.0
        - safety_margin * 3,
        "cable": z_unit_bottom
        - thicknesses["insulator"]
        - thicknesses["pen"]
        - thicknesses["cable"] / 2.0
        - safety_margin * 3,
        "clamp": z_unit_bottom
        - thicknesses["insulator"]
        - thicknesses["pen"]
        - thicknesses["cable"]
        - thicknesses["clamp"] / 2.0
        - safety_margin * 4,
    }

    det_pv = geant4.PhysicalVolume(
        [0, 0, 0],
        [string_info["x_pos"], string_info["y_pos"], z_pos["det"]],
        det_unit.lv,
        det_unit.name,
        b.mother_lv,
        b.registry,
    )
    det_pv.pygeom_active_detector = RemageDetectorInfo("germanium", det_unit.rawid, det_unit.meta)
    det_unit.lv.pygeom_color_rgba = (0.5, 0.5, 0.5, 1)

    # add germanium reflective surface.
    geant4.BorderSurface(
        "bsurface_lar_ge_" + det_pv.name,
        b.mother_pv,
        det_pv,
        b.materials.surfaces.to_germanium,
        b.registry,
    )

    if "PEN_plates" in b.detail and b.detail["PEN_plates"] != "omit":
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
        pen_rot = Rotation.from_euler("XZ", [-math.pi, string_info["string_rot"]]).as_euler("xyz")
        pen_pv = geant4.PhysicalVolume(
            list(pen_rot),
            [string_info["x_pos"], string_info["y_pos"], z_pos["pen"]],
            pen_plate,
            "pen_" + det_unit.name,
            b.mother_lv,
            b.registry,
        )
        _add_pen_surfaces(pen_pv, b.mother_pv, b.materials, b.registry)

    if "front-end_and_insulators" in b.detail and b.detail["front-end_and_insulators"] != "omit":
        front_enc_and_insulator_parts_origin = {
            "signal": {
                "clamp": 2.5
                + 4.0
                + 1.5
                + 5 / 2,  # position from center of detector to center of volume center
                "cable": 2.5 + 4.0 + 16 / 2,
                "asic": 2.5 + 4.0 + 11 + 1 / 2.0,
            },
            "hv": {"clamp": 2.5 + 29.5 + 3.5 + 5 / 2, "cable": 2.5 + 29.5 + 2.0 + 8 / 2},
        }

        _place_front_end_and_insulators(
            det_unit, unit_length, string_info, b, z_pos, thicknesses, front_enc_and_insulator_parts_origin
        )


def _place_hpge_string(
    string_id: str,
    string_slots: list,
    b: core.InstrumentationData,
):
    """
    Place a single HPGe detector string.

    This includes all PEN plates and the nylon shroud around the string."""

    string_rot_output = calculate_string_rotation(string_id, b)
    string_rot = string_rot_output["string_rot"]
    string_rot_m = string_rot_output["string_rot_m"]
    x_pos = string_rot_output["x_pos"]
    y_pos = string_rot_output["y_pos"]
    string_meta = string_rot_output["string_meta"]

    # offset the height of the string by the length of the string support rod.
    # z0_string is the upper z coordinate of the topmost detector unit.
    # TODO: real measurements (slides of M. Bush on 2024-07-08) show an additional offset -0.6 mm.
    # TODO: this is also still a warm length.

    # z0_string = copper_rod_upper_end_z_pos - distance_upper_end_of_individual_copper_rod_to_upper_end_of_whole_copper_rod - distance_z0_to_upper_end_of_individual_copper_rod  # from CAD model.

    # deliberately use max and range here. The code does not support sparse strings (i.e. with
    # unpopulated slots, that are _not_ at the end. In those cases it should produce a KeyError.
    max_unit_id = max(string_slots.keys())
    total_rod_length = 0

    for hpge_unit_id_in_string in range(1, max_unit_id + 1):
        det_unit = string_slots[hpge_unit_id_in_string]

        # convert the "warm" length of the rod to the (shorter) length in the cooled down state.

        z_unit_bottom = (
            z_pos_dict["first_detector_bottom"] - total_rod_length
        )  # defined as the bottom of the clap at the moment.
        unit_length = det_unit.rodlength  # * 0.997
        string_info = {
            "string_id": string_id,
            "string_rot": string_rot,
            "string_rot_m": string_rot_m,
            "string_meta": string_meta,
            "x_pos": x_pos,
            "y_pos": y_pos,
        }

        thicknesses = {
            "pen": 1.5,  # mm
            "cable": 0.076,  # mm
            "clamp": 1.8,  # mm
            "weldment": 1.5,  # mm flap thickness
            "insulator": 2.4,  # mm flap thickness
        }

        _place_hpge_unit(z_unit_bottom, det_unit, unit_length, string_info, thicknesses, b)

        total_rod_length += det_unit.rodlength  # * 0.997

    # the copper rod is slightly longer after the last detector.
    copper_rod_length = total_rod_length + (
        z_pos_dict["copper_rod_upper_end"] - z_pos_dict["first_individual_copper_segment_upper_end"]
    )

    support, tristar = _get_support_structure(string_slots[1].baseplate, b.materials, b.registry)
    geant4.PhysicalVolume(
        [0, 0, np.deg2rad(30) + string_rot],
        [x_pos, y_pos, z_pos_dict["copper_rod_upper_end"]],
        support,
        support.name + "_string_" + string_id,
        b.mother_lv,
        b.registry,
    )
    geant4.PhysicalVolume(
        [0, 0, string_rot],
        [x_pos, y_pos, z_pos_dict["copper_rod_upper_end"] - 1e-6],
        tristar,
        tristar.name + "_string_" + string_id,
        b.mother_lv,
        b.registry,
    )

    copper_rod_r = string_meta.rod_radius_in_mm
    copper_rod_name = f"hpge_support_copper_rod_string_{string_id}"
    # the rod has a radius of 1.5 mm, but this would overlap with the coarse model of the PPC top PEN ring.
    copper_rod = geant4.solid.Tubs(copper_rod_name, 0, 1.5, copper_rod_length, 0, 2 * math.pi, b.registry)
    copper_rod = geant4.LogicalVolume(copper_rod, b.materials.metal_copper, copper_rod_name, b.registry)
    copper_rod.pygeom_color_rgba = (0.72, 0.45, 0.2, 1)
    for i in range(3):
        copper_rod_th = np.deg2rad(-30 - i * 120)
        delta = copper_rod_r * string_rot_m @ np.array([np.cos(copper_rod_th), np.sin(copper_rod_th)])
        geant4.PhysicalVolume(
            [0, 0, 0],
            [x_pos + delta[0], y_pos + delta[1], z_pos_dict["copper_rod_upper_end"] - copper_rod_length / 2],
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

    pen_lv_name = f"pen_{size}"
    if pen_lv_name not in registry.logicalVolumeDict:
        if size != "ppc_small":
            pen_file = resources.files("pygeoml1000") / "models" / f"BasePlate_{size}.stl"
        else:
            pen_file = resources.files("pygeoml1000") / "models" / "TopPlate_ppc.stl"

        pen_solid = pyg4ometry.stl.Reader(
            pen_file, solidname=f"pen_{size}", centre=False, registry=registry
        ).getSolid()
        pen_lv = geant4.LogicalVolume(pen_solid, materials.pen, pen_lv_name, registry)
        pen_lv.pygeom_color_rgba = (1, 1, 1, 0.3)

    return registry.logicalVolumeDict[pen_lv_name]


def _get_support_structure(
    size: str,
    materials: materials.OpticalMaterialRegistry,
    registry: geant4.Registry,
) -> tuple[geant4.LogicalVolume, geant4.LogicalVolume]:
    """Get the (simplified) support structure and the tristar of the requested size.

    .. note :: Both models' coordinate origins are a the top face of the tristar structure."""

    if "hpge_support_copper_string_support_structure" not in registry.logicalVolumeDict:
        support_file = resources.files("pygeoml1000") / "models" / "StringSupportStructure.stl"
        support_solid = pyg4ometry.stl.Reader(
            support_file, solidname="string_support_structure", centre=False, registry=registry
        ).getSolid()
        support_lv = geant4.LogicalVolume(
            support_solid, materials.metal_copper, "hpge_support_copper_string_support_structure", registry
        )
        support_lv.pygeom_color_rgba = (0.72, 0.45, 0.2, 1)
    else:
        support_lv = registry.logicalVolumeDict["hpge_support_copper_string_support_structure"]

    tristar_lv_name = f"hpge_support_copper_tristar_{size}"
    if tristar_lv_name not in registry.logicalVolumeDict:
        pen_file = resources.files("pygeoml1000") / "models" / f"TriStar_{size}.stl"

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


def _get_hv_cable(
    name: str,
    cable_thickness: float,
    clamp_thickness: float,
    cable_length: float,
    materials: materials.OpticalMaterialRegistry,
    mother_pv: geant4.LogicalVolume,
    reg: geant4.Registry,
):
    safety_margin = 1  # mm
    cable_length -= safety_margin

    hv_cable_under_clamp = geant4.solid.Box(
        "hv_cable_under_clamp_" + name,
        8,
        13,
        cable_thickness,
        reg,
        "mm",
    )
    hv_cable_clamp_to_curve = geant4.solid.Box(
        "hv_cable_clamp_to_curve_" + name,
        5.5,
        2,
        cable_thickness,
        reg,
        "mm",
    )

    hv_cable_curve = geant4.solid.Tubs(
        "hv_cable_curve_" + name, 3.08, 3.08 + cable_thickness, 2.0, 0, math.pi / 2.0, reg, "mm"
    )

    hv_cable_along_unit = geant4.solid.Box(
        "hv_along_unit_" + name,
        cable_thickness,
        2.0,
        cable_length,
        reg,
        "mm",
    )

    hv_cable_part1 = geant4.solid.Union(
        "hv_cable_part1_" + name,
        hv_cable_under_clamp,
        hv_cable_clamp_to_curve,
        [[0, 0, 0], [8 / 2.0 + 5.5 / 2.0, 0, 0]],
        reg,
    )

    hv_cable_part2 = geant4.solid.Union(
        "hv_cable_part2_" + name,
        hv_cable_part1,
        hv_cable_curve,
        [[-np.pi / 2, 0, 0], [8 / 2.0 + 5.5, 0, 3.08 + cable_thickness / 2.0]],
        reg,
    )

    hv_cable = geant4.solid.Union(
        "cable_hv_" + name,
        hv_cable_part2,
        hv_cable_along_unit,
        [[0, 0, 0], [8 / 2.0 + 5.5 + 3.08 + cable_thickness / 2.0, 0, 3.08 + cable_length / 2.0]],
        reg,
    )

    hv_clamp = geant4.solid.Box(
        "ultem_clamp_hv_" + name,
        5,
        13,
        clamp_thickness,
        reg,
        "mm",
    )

    hv_cable_lv = geant4.LogicalVolume(
        hv_cable,
        materials.metal_copper,
        "cable_hv_" + name,
        reg,
    )

    hv_clamp_lv = geant4.LogicalVolume(
        hv_clamp,
        materials.ultem,
        "ultem_clamp_hv_" + name,
        reg,
    )

    return hv_cable_lv, hv_clamp_lv


def _get_signal_cable_and_asic(
    name: str,
    cable_thickness: float,
    clamp_thickness: float,
    cable_length: float,
    materials: materials.OpticalMaterialRegistry,
    mother_pv: geant4.LogicalVolume,
    reg: geant4.Registry,
):
    safety_margin = 1  # mm
    cable_length -= safety_margin

    signal_cable_under_clamp = geant4.solid.Box(
        "signal_cable_under_clamp_" + name,
        16,
        13,
        cable_thickness,
        reg,
        "mm",
    )
    signal_cable_clamp_to_curve = geant4.solid.Box(
        "signal_cable_clamp_to_curve_" + name,
        23.25,
        2,
        cable_thickness,
        reg,
        "mm",
    )
    signal_cable_curve = geant4.solid.Tubs(
        "signal_cable_curve_" + name, 3.08, 3.08 + cable_thickness, 2.0, 0, math.pi / 2.0, reg, "mm"
    )
    signal_cable_along_unit = geant4.solid.Box(
        "signal_along_unit_" + name,
        cable_thickness,
        2.0,
        cable_length,
        reg,
        "mm",
    )
    signal_cable_part1 = geant4.solid.Union(
        "signal_cable_part1_" + name,
        signal_cable_under_clamp,
        signal_cable_clamp_to_curve,
        [[0, 0, 0], [16 / 2.0 + 23.25 / 2.0, 0, 0]],
        reg,
    )
    signal_cable_part2 = geant4.solid.Union(
        "signal_cable_part2_" + name,
        signal_cable_part1,
        signal_cable_curve,
        [[np.pi / 2, 0, 0], [16 / 2.0 + 23.25, 0, -3.08 - cable_thickness / 2.0]],
        reg,
    )
    signal_cable = geant4.solid.Union(
        "cable_signal_" + name,
        signal_cable_part2,
        signal_cable_along_unit,
        [[0, 0, 0], [16 / 2.0 + 23.25 + 3.08 + cable_thickness / 2.0, 0, -3.08 - cable_length / 2.0]],
        reg,
    )

    signal_clamp_part1 = geant4.solid.Box(
        "signal_clamp_part1_" + name,
        5,
        13,
        clamp_thickness,
        reg,
        "mm",
    )
    signal_clamp_part2 = geant4.solid.Box(
        "signal_clamp_part2_" + name,
        9,
        2.5,
        clamp_thickness,
        reg,
        "mm",
    )
    signal_clamp_part3 = geant4.solid.Union(
        "signal_clamp_part3_" + name,
        signal_clamp_part1,
        signal_clamp_part2,
        [[0, 0, 0], [5 / 2.0 + 9 / 2.0, 13 / 2.0 - 2.5 / 2.0, 0]],
        reg,
    )
    signal_clamp = geant4.solid.Union(
        "ultem_clamp_signal_" + name,
        signal_clamp_part3,
        signal_clamp_part2,
        [[0, 0, 0], [5 / 2.0 + 9 / 2.0, -13 / 2.0 + 2.5 / 2.0, 0]],
        reg,
    )

    signal_asic = geant4.solid.Box(
        "signal_asic_" + name,
        1,
        1,
        0.5,
        reg,
        "mm",
    )

    signal_cable_lv = geant4.LogicalVolume(
        signal_cable,
        materials.metal_copper,
        "cable_signal_" + name,
        reg,
    )

    signal_clamp_lv = geant4.LogicalVolume(
        signal_clamp,
        materials.ultem,
        "ultem_clamp_signal_" + name,
        reg,
    )

    signal_asic_lv = geant4.LogicalVolume(
        signal_asic,
        materials.silica,
        "signal_asic_" + name,
        reg,
    )

    return signal_cable_lv, signal_clamp_lv, signal_asic_lv


def _get_weldment_and_insulator(
    det_unit: HPGeDetUnit,
    weldment_top_flap_thickness: float,
    insulator_du_holder_flap_thickness: float,
    insulator_top_length: float,
    materials: materials.OpticalMaterialRegistry,
    reg: geant4.Registry,
):
    safety_margin = 0.1
    weldment_top_flap = geant4.solid.Box(
        "hpge_support_copper_weldment_top_flap_" + det_unit.name,
        20.8,
        5,
        weldment_top_flap_thickness,
        reg,
        "mm",
    )

    weldment_top_clamp = geant4.solid.Box(
        "hpge_support_copper_weldment_top_clamp_" + det_unit.name,
        7.8,
        5,
        2.2,
        reg,
        "mm",
    )

    # Union the flap and clamp
    weldment_top_without_hole = geant4.solid.Union(
        "hpge_support_copper_weldment_top_without_hole_" + det_unit.name,
        weldment_top_flap,
        weldment_top_clamp,
        [[0, 0, 0], [20.8 / 2.0 - 7.8 / 2.0, 0, -2.2 / 2.0 - weldment_top_flap_thickness / 2.0]],
        reg,
    )

    weldment_top_carving_hole = geant4.solid.Tubs(
        "hpge_support_copper_weldment_top_carving_hole_" + det_unit.name,
        0,
        1.5 + safety_margin,
        2 * (weldment_top_flap_thickness + 2.2),
        0,
        math.pi * 2,
        reg,
        "mm",
    )

    # Perform subtraction only once
    weldment_top = geant4.solid.Subtraction(
        "hpge_support_copper_weldment_top_" + det_unit.name,
        weldment_top_without_hole,
        weldment_top_carving_hole,
        [[0, 0, 0], [5.60, 0, 0]],  # Adjust the position of the hole as needed
        reg,
    )

    insulator_du_holder_flap = geant4.solid.Box(
        "ultem_insulator_du_holder_flap_" + det_unit.name,
        16.5,
        7,
        insulator_du_holder_flap_thickness,
        reg,
        "mm",
    )

    safety_margin_touching_detector = 0.25

    insulator_du_holder_clamp = geant4.solid.Box(
        "ultem_insulator_du_holder_clamp_" + det_unit.name,
        insulator_top_length - safety_margin_touching_detector,
        7,
        5.5 - insulator_du_holder_flap_thickness,
        reg,
        "mm",
    )

    # Union the flap and clamp
    insulator_du_holder_without_hole = geant4.solid.Union(
        "ultem_insulator_du_holder_without_hole_ " + det_unit.name,
        insulator_du_holder_flap,
        insulator_du_holder_clamp,
        [
            [0, 0, 0],
            [
                16.5 / 2.0 - (insulator_top_length - safety_margin_touching_detector) / 2.0,
                0,
                (5.5 - insulator_du_holder_flap_thickness) / 2.0 + insulator_du_holder_flap_thickness / 2.0,
            ],
        ],
        reg,
    )

    insulator_du_holder_carving_hole = geant4.solid.Tubs(
        "ultem_insulator_du_holder_carving_hole_" + det_unit.name,
        0,
        1.5 + safety_margin,
        3 * 5.5,
        0,
        math.pi * 2,
        reg,
        "mm",
    )

    # Perform subtraction only once
    insulator_du_holder = geant4.solid.Subtraction(
        "ultem_insulator_du_holder_" + det_unit.name,
        insulator_du_holder_without_hole,
        insulator_du_holder_carving_hole,
        [[0, 0, 0], [16.5 / 2.0 - 1.5, 0, 0]],  # Adjust the position of the hole as needed
        reg,
    )

    weldment_top_lv = geant4.LogicalVolume(
        weldment_top,
        materials.metal_copper,
        "hpge_support_copper_weldment_top_" + det_unit.name,
        reg,
    )

    insulator_du_holder_lv = geant4.LogicalVolume(
        insulator_du_holder,
        materials.ultem,
        "ultem_insulator_du_holder_" + det_unit.name,
        reg,
    )

    return weldment_top_lv, insulator_du_holder_lv
