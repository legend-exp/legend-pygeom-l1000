"""
Updated to the CAD status shown by Matthew Busch on 2025-11-05 LEGEND Collaboration Meeting.
"""

from __future__ import annotations

import logging
from math import pi

import numpy as np
import pyg4ometry.geant4 as g4
from pygeomtools import RemageDetectorInfo

from . import core, watertank
from .rt_profiles import (
    make_316l_ss_profiles,
    make_inner_profile,
    make_ofhc_cu_profiles,
    make_outer_profile,
)

# Import new reentrance tube profile and WLSR functions
from .utils import COLORS
from .wlsr import place_inner_wlsr_in_argon, place_outer_wlsr_in_atmospheric

log = logging.getLogger(__name__)

# clearance left between the top rim of the skirt and the curved cryostat bottom it wraps around.
SKIRT_CRYO_GAP = 0.1  # mm


def _first_z_at_radius(prof_z: list[float], prof_r: list[float], r_limit: float) -> float:
    """Find the height at which the cryostat profile first widens to ``r_limit``."""
    for i in range(len(prof_z) - 1):
        r0, r1 = prof_r[i], prof_r[i + 1]
        if r0 <= r_limit < r1 and prof_z[i + 1] > prof_z[i]:
            frac = (r_limit - r0) / (r1 - r0)
            return prof_z[i] + frac * (prof_z[i + 1] - prof_z[i])

    msg = f"cryostat profile never reaches r = {r_limit} mm"
    raise ValueError(msg)


"""

The cryostat consists of three main pieces:
The top piece which encloses the reentrance tube, separating it from the water volume (the "neck")
The central piece, which encloses the LAr shielding (I call this the "body", although the name is up for debate)
The bottom piece, which supports the body and separates the "pillbox" water volume from the rest of the volume.
I call this the "skirt", but again, name is debatable.
The skirt technically isn't part of the cryostat - but, well, it's not really part of anything else, either.
Since it's made of steel, connected to the cryostat, and enclosed by the water, we include it here anyways.
The skirt also has a square support at the bottom, which I call the "foot".

The body also consists of three sections: the curved top section, the cylindrical middle section, and the
curved bottom section. I call these the "shoulder", the "barrel", and the "bottom".

Unless stated otherwise, all radii and heights are from the outermost edge of each volume, not the inner.
Unless stated otherwise, all radii and heights are measured from the outside of each object.

Only two radii need to be explicitly defined: the radius of the neck and the radius of the barrel.
The neck's radius stays constant, and the body's top radius = neck radius, while the bottom radius tapers to 0.

There are multiple z points to consider: top of the neck, bottom of the neck/top of the shoulder,
top and bottom of the body's barrel (basically where the constant radius piece of the body begins and ends),
bottom of the bottom (where the radius tapers to 0), and the height/width of the skirt's "foot".

I will also note that the top of the skirt is connected to the bottom of the barrel.
The bottom z value of the skirt is fixed by the water tank height and should always connect with the floor.
For now, I'll just set a hard value for the total height, and at the end, the skirt can have what's left
to work with in the z direction.

The inner cryostat is a separate thing altogether, with its own curve, thicknesses and r/z values.
These, too, will mostly be computed automatically from the outer cryostat values.
The only inputs needed are the gaps between the inner and outer cryostat at some key points, and thickness.
Let's say, at the neck, at the barrel, and at the bottom.

"""

"""
The vessels, the skirt, the base ring and the reentrance tube follow the LEGEND-1000 cryostat drawings by
Tobias Sterr (28.09.2026). All heads there are torispherical (a crown radius blended into a knuckle radius), and the
inner surface of each shell is the outer one offset by the wall thickness.
"""

"""
All units in mm.
"""


def cryo_floor_z() -> float:
    """Height of the floor in the cryostat frame.

    Heights from the drawings are measured from the floor: the bottom of the base ring, which stands on the
    inner floor of the water tank. The cryostat frame itself is unchanged, so everything placed inside the
    argon (HPGe strings, fibers) stays where it was. A function, as watertank imports this module.
    """
    return watertank.tank_horizontal_wall - (
        watertank.tank_pit_height + watertank.tank_central_part_height / 2
    )


# Outside surface of each vessel: barrel radius, crown and knuckle radii of the heads, and the height of
# the tangent lines where the heads meet the barrel (above the floor).
OUTER_VESSEL = {
    "barrel_radius": 3480.0,
    "crown_radius": 5585.2,
    "knuckle_radius": 1084.5,
    "z_bottom_tangent": 2622.1,
    "z_top_tangent": 6772.0,
}
INNER_VESSEL = {
    "barrel_radius": 3215.0,
    "crown_radius": 5156.5,
    "knuckle_radius": 1002.6,
    "z_bottom_tangent": 2625.2,
    "z_top_tangent": 6707.6,
}
# Wall thicknesses as (bottom head, barrel, top head). Only the barrels are 15 mm.
OUTER_VESSEL_WALL = (15.2, 15.0, 12.5)
INNER_VESSEL_WALL = (12.5, 15.0, 12.5)
# The neck tubes have 10 mm walls.
OUTER_NECK_WALL = 10.0
INNER_NECK_RADIUS = 1000.0

# Reentrance tube: Ø1847 inner diameter with a 1.5 mm wall, closed by a torispherical head.
REENTRANCE_TUBE_RADIUS = 924.9
REENTRANCE_TUBE_BOTTOM_Z = 3856.3  # apex of the head, above the floor
REENTRANCE_TUBE_TANGENT_Z = 4215.8  # where the head meets the cylinder, above the floor

# Segments per head section. Each layer uses the same angles, so neighbouring layers stay parallel.
N_CROWN_SEGMENTS = 8
N_KNUCKLE_SEGMENTS = 8

# JACKODUR (XPS foam) insulation around the outer vessel
INSULATION_THICKNESS = 10.0


def _head(
    barrel_radius: float, crown_radius: float, knuckle_radius: float, sign: int
) -> tuple[np.ndarray, np.ndarray]:
    """(r, dz) of a torispherical head from the axis out to the tangent line.

    dz is measured from the tangent line: negative for a bottom head (``sign=-1``), positive for a top head.
    """
    alpha = np.arcsin((barrel_radius - knuckle_radius) / (crown_radius - knuckle_radius))
    crown_center = -(crown_radius - knuckle_radius) * np.cos(alpha)
    a = np.linspace(0, alpha, N_CROWN_SEGMENTS + 1)
    b = np.linspace(alpha, pi / 2, N_KNUCKLE_SEGMENTS + 1)[1:]
    r = np.r_[crown_radius * np.sin(a), barrel_radius - knuckle_radius + knuckle_radius * np.sin(b)]
    dz = np.r_[crown_center + crown_radius * np.cos(a), knuckle_radius * np.cos(b)]
    return r, sign * dz


def make_vessel_profile(
    vessel: dict, wall: tuple[float, float, float], neck_radius: float, neck_top: float
) -> tuple[list, list]:
    """Closed (z, r) outline of one cryostat layer, in the cryostat frame.

    The layer is the outside surface ``vessel`` moved inwards by ``wall`` = (bottom head, barrel,
    top head) thickness, with a neck of ``neck_radius`` from the top head up to ``neck_top``.
    """
    t_bottom, t_barrel, t_top = wall

    def shifted(t):
        return {
            "barrel_radius": vessel["barrel_radius"] - t,
            "crown_radius": vessel["crown_radius"] - t,
            "knuckle_radius": vessel["knuckle_radius"] - t,
        }

    z_bot = vessel["z_bottom_tangent"] + cryo_floor_z()
    z_top = vessel["z_top_tangent"] + cryo_floor_z()
    r_b, dz_b = _head(**shifted(t_bottom), sign=-1)
    r_t, dz_t = _head(**shifted(t_top), sign=+1)

    # bottom head, barrel (a thinner head than barrel leaves a small step at the tangent line), top head
    r_barrel = vessel["barrel_radius"] - t_barrel
    r = np.r_[r_b, r_barrel, r_barrel, r_t[::-1]]
    z = np.r_[z_bot + dz_b, z_bot, z_top, z_top + dz_t[::-1]]

    # cut the top head off where it reaches the neck, then go straight up the neck
    top = shifted(t_top)
    alpha = np.arcsin(
        (top["barrel_radius"] - top["knuckle_radius"]) / (top["crown_radius"] - top["knuckle_radius"])
    )
    crown_center = z_top - (top["crown_radius"] - top["knuckle_radius"]) * np.cos(alpha)
    keep = (r > neck_radius) | (z < z_top)
    r = np.r_[r[keep], neck_radius, neck_radius, 0]
    z = np.r_[z[keep], crown_center + np.sqrt(top["crown_radius"] ** 2 - neck_radius**2), neck_top, neck_top]

    # G4GenericPolycone does not accept repeated points (a head as thick as the barrel)
    repeated = np.r_[False, (np.diff(r) == 0) & (np.diff(z) == 0)]
    return [float(v) for v in z[~repeated]], [float(v) for v in r[~repeated]]


def make_insulation_profile(neck_radius: float, insulation_top: float, top: float) -> tuple[list, list]:
    """Closed (z, r) outline of the insulation around the outer vessel, in the cryostat frame.

    The insulation is the mother volume of the outer vessel: its outside surface moved outwards by the
    insulation thickness (sampled at the same angles), up to ``insulation_top`` under the water-tank roof.
    Above that, the radius is adjusted to ``neck_radius`` while the neck is reduced by 1 nm for navigation.
    """
    t = INSULATION_THICKNESS
    z, r = make_vessel_profile(OUTER_VESSEL, (-t, -t, -t), neck_radius + t, insulation_top)
    # replace the closing point on the axis: step in to the neck and continue up to the top
    return [*z[:-1], insulation_top, top, top], [*r[:-1], neck_radius, neck_radius, 0]


def make_moderator_z_r_r(
    mod_height: float, mod_radius: float, mod_thickness: float, tube_radius: float
) -> tuple[list, list, list]:
    # Instead of a polycone, we use a G4Polyhedra for the moderator
    # It's assumed that the moderator will not have curved sides

    # z first since it's easiest
    z = [mod_height]
    # First change happens after one thickness
    z.append(mod_height - mod_thickness)
    # But happens suddenly
    z.append(mod_height - mod_thickness - 0.001)
    # Next happens one thickness from the bottom
    z.append(mod_thickness + 0.001)
    # And suddenly
    z.append(mod_thickness)
    # Final point at the bottom
    z.append(0)

    # Outer radius is actually probably easiest - it's constant lmao
    r_outer = [mod_radius, mod_radius, mod_radius, mod_radius, mod_radius, mod_radius]

    # Inner radius leaves a hole for the reentrance tube, hollows out the inside,
    # then closes the bottom. The hole's "radius" is the radius of an
    # inscribing circle, so that the polyhedron is larger than the circle.
    r_inner = [tube_radius]
    # Stays constant until the aperture is through the mod's thickness
    r_inner.append(tube_radius)
    r_inner.append(mod_radius - mod_thickness)
    r_inner.append(mod_radius - mod_thickness)
    r_inner.append(0)
    r_inner.append(0)

    # print(z)
    # print(r_inner)
    # print(r_outer)

    return z[::-1], r_inner[::-1], r_outer[::-1]


def construct_outer_cryostat(
    cryostat_material: g4.Material, reg: g4.Registry, ocryo_r: list, ocryo_z: list
) -> g4.LogicalVolume:
    ocryo_solid = g4.solid.GenericPolycone(
        "cryostat_outer_steel_316L", 0, 2 * pi, ocryo_r, ocryo_z, reg, "mm"
    )

    return g4.LogicalVolume(ocryo_solid, cryostat_material, "cryostat_outer_steel_316L", reg)


def construct_vacuum_gap(
    vac_material: g4.Material, reg: g4.Registry, vac_r: list, vac_z: list
) -> g4.LogicalVolume:
    vac_solid = g4.solid.GenericPolycone("cryostat_insulation_vacuum", 0, 2 * pi, vac_r, vac_z, reg, "mm")

    return g4.LogicalVolume(vac_solid, vac_material, "cryostat_insulation_vacuum", reg)


def construct_inner_cryostat(
    cryostat_material: g4.Material, reg: g4.Registry, icryo_r: list, icryo_z: list
) -> g4.LogicalVolume:
    icryo_solid = g4.solid.GenericPolycone(
        "cryostat_inner_steel_316L", 0, 2 * pi, icryo_r, icryo_z, reg, "mm"
    )

    return g4.LogicalVolume(icryo_solid, cryostat_material, "cryostat_inner_steel_316L", reg)


def construct_atmospheric_lar(
    lar_material: g4.Material, reg: g4.Registry, atmlar_r: list, atmlar_z: list
) -> g4.LogicalVolume:
    atmlar_solid = g4.solid.GenericPolycone(
        "liquid_argon_atmospheric", 0, 2 * pi, atmlar_r, atmlar_z, reg, "mm"
    )

    return g4.LogicalVolume(atmlar_solid, lar_material, "liquid_argon_atmospheric", reg)


def construct_reentrance_tube_with_layers(
    materials,
    reg: g4.Registry,
    atmlar_lv: g4.LogicalVolume,
    atmlar_pv: g4.PhysicalVolume,
    neck_radius: float,
    tube_height: float,
    total_height: float,
    curve_fraction: float,
    wls_height: float,
    ofhc_start_height: float,
    ofhc_end_height: float,
    ss_start_height: float,
) -> tuple[g4.LogicalVolume, g4.PhysicalVolume]:
    """
    Construct reentrance tube with WLSR, OFHC Cu, and 316L SS layers.

    All layers are always present in the geometry:
    - Copper tube with variable thickness
    - OFHC copper layer (2179-4184mm height)
    - 316L stainless steel layer (4184mm-top)
    - Inner WLSR (TPB + Tetratex) in underground argon
    - Outer WLSR (TPB + Tetratex) in atmospheric argon

    Returns:
        Tuple of (underground_argon_lv, underground_argon_pv)
    """

    # Generate steel tube profiles using functions from profiles.py
    outer_z, outer_r = make_outer_profile(neck_radius, tube_height, total_height, curve_fraction, wls_height)
    inner_z, inner_r = make_inner_profile(neck_radius, tube_height, total_height, curve_fraction, wls_height)

    # Construct steel tube
    tube_solid = g4.solid.GenericPolycone("reentrance_tube_copper", 0, 2 * np.pi, outer_r, outer_z, reg, "mm")
    tube_lv = g4.LogicalVolume(tube_solid, materials.metal_copper, "reentrance_tube_copper", reg)
    tube_lv.pygeom_color_rgba = COLORS["copper"]
    g4.PhysicalVolume([0, 0, 0], [0, 0, 0, "mm"], tube_lv, "reentrance_tube_copper", atmlar_lv, registry=reg)

    # Construct underground argon cavity
    uglar_solid = g4.solid.GenericPolycone(
        "liquid_argon_underground", 0, 2 * np.pi, inner_r, inner_z, reg, "mm"
    )
    uglar_lv = g4.LogicalVolume(uglar_solid, materials.liquidargon, "liquid_argon_underground", reg)
    uglar_lv.pygeom_color_rgba = False  # we show the reentrance tube.
    uglar_pv = g4.PhysicalVolume(
        [0, 0, 0], [0, 0, 0, "mm"], uglar_lv, "liquid_argon_underground", tube_lv, registry=reg
    )

    # Place inner WLSR in underground argon (function from wlsr.py)
    place_inner_wlsr_in_argon(
        materials,
        reg,
        uglar_lv,
        uglar_pv,
        neck_radius,
        tube_height,
        total_height,
        curve_fraction,
        wls_height,
        inner_z,
        inner_r,
        outer_z,
        outer_r,
    )

    # Place outer WLSR in atmospheric argon (function from wlsr.py)
    place_outer_wlsr_in_atmospheric(
        materials,
        reg,
        atmlar_lv,
        atmlar_pv,
        neck_radius,
        tube_height,
        total_height,
        curve_fraction,
        wls_height,
        outer_z,
        outer_r,
    )

    # Construct OFHC copper layer (always present)
    ofhc_outer_z, ofhc_outer_r, ofhc_inner_z, ofhc_inner_r = make_ofhc_cu_profiles(
        neck_radius,
        tube_height,
        total_height,
        curve_fraction,
        ofhc_start_height,
        ofhc_end_height,
        outer_z,
        outer_r,
        inner_z,
        inner_r,
    )

    ofhc_outer_bound = g4.solid.GenericPolycone(
        "reentrance_tube_layer_copper_ofhc_outer_bound", 0, 2 * np.pi, ofhc_outer_r, ofhc_outer_z, reg, "mm"
    )
    ofhc_inner_bound = g4.solid.GenericPolycone(
        "reentrance_tube_layer_copper_ofhc_inner_bound", 0, 2 * np.pi, ofhc_inner_r, ofhc_inner_z, reg, "mm"
    )
    ofhc_solid = g4.solid.Subtraction(
        "reentrance_tube_layer_copper_ofhc",
        ofhc_outer_bound,
        ofhc_inner_bound,
        [[0, 0, 0], [0, 0, 0, "mm"]],
        reg,
    )
    ofhc_lv = g4.LogicalVolume(ofhc_solid, materials.metal_copper, "reentrance_tube_layer_copper_ofhc", reg)
    ofhc_lv.pygeom_color_rgba = (0.72, 0.45, 0.2, 1)
    g4.PhysicalVolume(
        [0, 0, 0], [0, 0, 0, "mm"], ofhc_lv, "reentrance_tube_layer_copper_ofhc", tube_lv, registry=reg
    )

    # Construct 316L stainless steel layer (always present)
    ss_outer_z, ss_outer_r, ss_inner_z, ss_inner_r = make_316l_ss_profiles(
        neck_radius,
        tube_height,
        total_height,
        curve_fraction,
        ss_start_height,
        outer_z,
        outer_r,
        inner_z,
        inner_r,
    )

    ss_outer_bound = g4.solid.GenericPolycone(
        "reentrance_tube_layer_steel_316L_outer_bound", 0, 2 * np.pi, ss_outer_r, ss_outer_z, reg, "mm"
    )
    ss_inner_bound = g4.solid.GenericPolycone(
        "reentrance_tube_layer_steel_316L_inner_bound", 0, 2 * np.pi, ss_inner_r, ss_inner_z, reg, "mm"
    )
    ss_solid = g4.solid.Subtraction(
        "reentrance_tube_layer_steel_316L",
        ss_outer_bound,
        ss_inner_bound,
        [[0, 0, 0], [0, 0, 0, "mm"]],
        reg,
    )
    ss_lv = g4.LogicalVolume(ss_solid, materials.metal_steel_316L, "reentrance_tube_layer_steel_316L", reg)
    ss_lv.pygeom_color_rgba = (0.7, 0.7, 0.8, 1.0)
    g4.PhysicalVolume(
        [0, 0, 0], [0, 0, 0, "mm"], ss_lv, "reentrance_tube_layer_steel_316L", tube_lv, registry=reg
    )

    return uglar_lv, uglar_pv


def construct_moderator_simple(
    mod_material: g4.Material,
    reg: g4.Registry,
    mod_r_inner: list,
    mod_r_outer: list,
    mod_z: list,
    mod_n_sides: int,
    mother_lv: g4.LogicalVolume,
):
    mod_solid = g4.solid.Polyhedra(
        "neutron_moderator_pmma",
        0,
        2 * pi,
        mod_n_sides,
        len(mod_z),
        mod_z,
        mod_r_inner,
        mod_r_outer,
        reg,
        "mm",
    )
    mod_lv = g4.LogicalVolume(mod_solid, mod_material, "neutron_moderator_pmma", reg)
    mod_lv.pygeom_color_rgba = COLORS["acrylic"]
    # g4.PhysicalVolume([0, 0, 0], [0, 0, -2900], mod_lv, "neutron_moderator_pmma", mother_lv, reg)  # -3000
    g4.PhysicalVolume([0, 0, 0], [0, 0, -2397], mod_lv, "neutron_moderator_pmma", mother_lv, reg)  # -3000
    # Z value used to be -body_height/2.*(1-bottom_fraction)
    # Could import this if we wanted, but maybe this method has enough arguments already...


NECKRADIUS_START = 1135  # Global to be used in the Watertank to avoid an overlapping issue


def construct_and_place_cryostat(instr: core.InstrumentationData) -> core.InstrumentationData:
    if "cryostat" not in instr.detail:
        msg = "No 'cryostat' detail specified in the special metadata."
        raise ValueError(msg)

    if instr.detail["cryostat"] == "omit":
        return instr

    # Tops of the four polycones in the cryostat frame. The outer neck top is where the water tank's neck
    # cut-out is built around. The vacuum ends one cap below it, to represent the lock system. The inner
    # neck stops 1 mm below the vacuum top, so the two do not share a face: a shared face makes the Geant4
    # navigator step from the daughter straight into the grandmother.
    outer_neck_top = 5020
    cap_thickness = 16
    vac_top = outer_neck_top - cap_thickness
    icryo_top = vac_top - 1
    atmlar_top = vac_top - cap_thickness

    neck_radius = NECKRADIUS_START - 2e-9

    # Parameters for the new reentrance tube with WLSR and metal layers.
    # rt_profiles measures heights from 5000 mm below the cryostat origin.
    tube_bottom = REENTRANCE_TUBE_BOTTOM_Z + cryo_floor_z()
    tube_height = atmlar_top - tube_bottom
    curve_fraction = (REENTRANCE_TUBE_TANGENT_Z - REENTRANCE_TUBE_BOTTOM_Z) / tube_height

    # WLSR and metal layer parameters (always enabled)
    wls_height = 2179  # Height where WLS layers extend to
    ofhc_start_height = 2179  # Start of OFHC copper layer
    ofhc_end_height = 4184  # End of OFHC copper layer
    ss_start_height = 4184  # Start of 316L SS layer

    # The skirt and moderator are unlike any other shapes and need their own parameters and constructors
    # The skirt borrows some parameters from the outer cryostat, to make sure it connects with the barrel
    # The one thing we can define about the moderator is that the aperture should be just slightly bigger than the neck_radius

    mod_height = 3200
    mod_radius = 1750
    mod_thickness = 100
    mod_n_sides = 12

    # The insulation, if placed, is the mother volume of the outer vessel. Where the neck passes through
    # the water-tank roof there is no room for it, so there the outer vessel's neck is made 1 nm thinner
    # and lower than the insulation volume for navigation purposes.
    build_insulation = instr.detail.get("cryostat_insulation", "omit") != "omit"
    nesting_gap = 1e-6 if build_insulation else 0  # mm
    ocryo_z, ocryo_r = make_vessel_profile(
        OUTER_VESSEL, (0, 0, 0), neck_radius - nesting_gap, outer_neck_top - nesting_gap
    )

    # The skirt continues the outer shell down to the floor. The base ring ("foot") surrounds its bottom.
    skirt_radius = OUTER_VESSEL["barrel_radius"]
    skirt_thickness = OUTER_VESSEL_WALL[1]

    foot_height = 375
    # 1e-9 to avoid sharing a surface with the bottom of the water volume.
    foot_bottom = cryo_floor_z() + 1e-9
    skirt_bottom = foot_bottom

    # The skirt is a plain cylinder, but the cryostat bottom it surrounds is curved: simply
    # shortening the skirt by a fixed amount does not reliably clear that curve. Instead, solve the
    # cryostat profile for the height at which it grows into the skirt wall and end the skirt there.
    # With the insulation, the skirt ends where it meets the insulation instead of the steel.
    if build_insulation:
        # Up the neck the insulation ends 1 mm below the underside of the water-tank roof.
        insulation_top = (
            watertank.tank_top_height
            - watertank.tank_top_bulge_depth
            - watertank.tank_horizontal_wall
            - (watertank.tank_pit_height + watertank.tank_central_part_height / 2)
            - 1
        )
        ins_z, ins_r = make_insulation_profile(neck_radius, insulation_top, outer_neck_top)
        skirt_top = _first_z_at_radius(ins_z, ins_r, skirt_radius - skirt_thickness) - SKIRT_CRYO_GAP
    else:
        skirt_top = _first_z_at_radius(ocryo_z, ocryo_r, skirt_radius - skirt_thickness) - SKIRT_CRYO_GAP

    # The base ring is a ring of steel fins of ~215mm depth and ~560 kg around the bottom of the skirt. It is modelled as a
    # solid ring of the drawn height, whose outer radius is set by mass instead of the drawn Ø7390 diameter. It also
    # takes the missing steel of the skirt, so that skirt and base ring together weigh what the drawing says.
    foot_mass = 560e3  # g
    skirt_area = pi * (skirt_radius**2 - (skirt_radius - skirt_thickness) ** 2)
    missing_skirt_volume = skirt_area * (OUTER_VESSEL["z_bottom_tangent"] + cryo_floor_z() - skirt_top)
    foot_volume = foot_mass / (instr.materials.metal_steel_316L.density * 1e-3) + missing_skirt_volume
    foot_inner_radius = skirt_radius + 1e-9
    foot_outer_radius = np.sqrt(foot_inner_radius**2 + foot_volume / foot_height / pi)

    actual_skirt_height = skirt_top - skirt_bottom
    skirt_z = (skirt_top + skirt_bottom) / 2

    skirt_solid = g4.solid.Tubs(
        "cryostat_skirt_steel_316L",
        skirt_radius - skirt_thickness,
        skirt_radius,
        actual_skirt_height,
        0,
        2 * pi,
        instr.registry,
        "mm",
    )
    skirt_lv = g4.LogicalVolume(
        skirt_solid, instr.materials.metal_steel_316L, "cryostat_skirt_steel_316L", instr.registry
    )
    skirt_lv.pygeom_color_rgba = COLORS["steel"]
    foot_solid = g4.solid.Tubs(
        "cryostat_foot_steel_316L",
        foot_inner_radius,
        foot_outer_radius,
        foot_height,
        0,
        2 * pi,
        instr.registry,
        "mm",
    )
    foot_lv = g4.LogicalVolume(
        foot_solid, instr.materials.metal_steel_316L, "cryostat_foot_steel_316L", instr.registry
    )
    foot_lv.pygeom_color_rgba = COLORS["steel"]

    outercryo_lv = construct_outer_cryostat(
        instr.materials.metal_steel_316L, instr.registry, ocryo_r, ocryo_z
    )
    outercryo_lv.pygeom_color_rgba = COLORS["steel"]

    # Each further layer is the outside surface of its vessel moved inwards by the wall thickness.
    vac_z, vac_r = make_vessel_profile(
        OUTER_VESSEL, OUTER_VESSEL_WALL, neck_radius - OUTER_NECK_WALL, vac_top
    )

    vac_lv = construct_vacuum_gap(instr.materials.vacuum, instr.registry, vac_r, vac_z)
    vac_lv.pygeom_color_rgba = False

    icryo_z, icryo_r = make_vessel_profile(INNER_VESSEL, (0, 0, 0), INNER_NECK_RADIUS, icryo_top)

    icryo_lv = construct_inner_cryostat(instr.materials.metal_steel_316L, instr.registry, icryo_r, icryo_z)
    icryo_lv.pygeom_color_rgba = COLORS["steel"]

    atmlar_z, atmlar_r = make_vessel_profile(
        INNER_VESSEL, INNER_VESSEL_WALL, INNER_NECK_RADIUS - OUTER_NECK_WALL, atmlar_top
    )

    atmlar_lv = construct_atmospheric_lar(instr.materials.liquidargon, instr.registry, atmlar_r, atmlar_z)
    atmlar_lv.pygeom_color_rgba = False  # we already show the cryostat

    # Place atmospheric argon first (needed as mother volume for reentrance tube)
    atmlar_pv = g4.PhysicalVolume(
        [0, 0, 0], [0, 0, 0], atmlar_lv, "liquid_argon_atmospheric", icryo_lv, instr.registry
    )

    atmlar_pv.set_pygeom_active_detector(RemageDetectorInfo("scintillator", 10000, {}))

    neck_radius = REENTRANCE_TUBE_RADIUS
    total_height = atmlar_top + 5000

    # Construct the new reentrance tube with all layers (WLSR, OFHC Cu, 316L SS, UAr)
    uglar_lv, uglar_pv = construct_reentrance_tube_with_layers(
        instr.materials,
        instr.registry,
        atmlar_lv,
        atmlar_pv,
        neck_radius,
        tube_height,
        total_height,
        curve_fraction,
        wls_height,
        ofhc_start_height,
        ofhc_end_height,
        ss_start_height,
    )

    uglar_pv.set_pygeom_active_detector(RemageDetectorInfo("scintillator", 10001, {}))

    # Construct neutron moderator if specified
    if "nm_plastic" not in instr.detail:
        log.warning("Warning: neutron moderator not specified. Omitting by default.")
    elif instr.detail["nm_plastic"] == "simple":
        mod_z, mod_r_inn, mod_r_out = make_moderator_z_r_r(
            mod_height, mod_radius, mod_thickness, neck_radius + 2
        )
        construct_moderator_simple(
            instr.materials.pmma, instr.registry, mod_r_inn, mod_r_out, mod_z, mod_n_sides, atmlar_lv
        )

    # Place the physical volumes at the end
    # Move the cryostat back in a central position

    g4.PhysicalVolume(
        [0, 0, 0],
        [instr.mother_x_displacement, 0, skirt_z + instr.mother_z_displacement],
        skirt_lv,
        "cryostat_skirt_steel_316L",
        instr.mother_lv,
        instr.registry,
    )
    g4.PhysicalVolume(
        [0, 0, 0],
        [instr.mother_x_displacement, 0, foot_bottom + foot_height / 2 + instr.mother_z_displacement],
        foot_lv,
        "cryostat_foot_steel_316L",
        instr.mother_lv,
        instr.registry,
    )

    # the outer vessel sits in the insulation, if that is placed, and in the water otherwise
    ocryo_mother_lv = instr.mother_lv
    ocryo_pos = [instr.mother_x_displacement, 0, instr.mother_z_displacement]
    if build_insulation:
        insulation_solid = g4.solid.GenericPolycone(
            "cryostat_insulation_jackodur", 0, 2 * pi, ins_r, ins_z, instr.registry, "mm"
        )
        insulation_lv = g4.LogicalVolume(
            insulation_solid, instr.materials.jackodur, "cryostat_insulation_jackodur", instr.registry
        )
        insulation_lv.pygeom_color_rgba = COLORS["insulation"]
        g4.PhysicalVolume(
            [0, 0, 0],
            ocryo_pos,
            insulation_lv,
            "cryostat_insulation_jackodur",
            instr.mother_lv,
            instr.registry,
        )
        # the insulation now faces the water instead of the steel
        g4.SkinSurface("insulation_surface", insulation_lv, instr.materials.surfaces.to_tyvek, instr.registry)
        ocryo_mother_lv = insulation_lv
        ocryo_pos = [0, 0, 0]

    g4.PhysicalVolume(
        [0, 0, 0], ocryo_pos, outercryo_lv, "cryostat_outer_steel_316L", ocryo_mother_lv, instr.registry
    )

    # with the insulation placed, it faces the water instead and carries this surface
    if not build_insulation:
        g4.SkinSurface("ocryo_surface", outercryo_lv, instr.materials.surfaces.to_tyvek, instr.registry)
    g4.SkinSurface("skirt_surface", skirt_lv, instr.materials.surfaces.to_tyvek, instr.registry)
    g4.SkinSurface("foot_surface", foot_lv, instr.materials.surfaces.to_tyvek, instr.registry)

    g4.PhysicalVolume(
        [0, 0, 0], [0, 0, 0], vac_lv, "cryostat_insulation_vacuum", outercryo_lv, instr.registry
    )
    g4.PhysicalVolume([0, 0, 0], [0, 0, 0], icryo_lv, "cryostat_inner_steel_316L", vac_lv, instr.registry)
    # atmlar_pv already placed above

    # NamedTuples are immutable, so we need to create a copy
    return instr._replace(mother_lv=uglar_lv, mother_pv=uglar_pv, mother_z_displacement=0)
