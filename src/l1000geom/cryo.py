from __future__ import annotations

import logging
from importlib import resources
from math import pi

import pyg4ometry
import pyg4ometry.geant4 as g4

from . import core

log = logging.getLogger(__name__)

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
The cryostat dimensions seem to change every few months. This cryostat has been made with a mixture of
imagination, extracting information from CAD drawings by eye, and vaguely remembered TC discussions.
Feel free to change any of the values as you see fit - the script can handle it, within reason.
"""

"""
All units in mm.
"""


def make_z_and_r(
    totalheight: float,
    neckheight: float,
    bodyheight: float,
    neckradius: float,
    barrelradius: float,
    shoulderfraction: float,
    bottomfraction: float,
) -> tuple[list, list]:
    # The definitions of each variable, even when they seem obvious:
    # totalheight - the z span of everything, from the bottom edge of the skirt/foot to the top of the neck
    # neckheight - the z span of the neck
    # bodyheight - the z span of all three pieces of the body (shoulder, barrel, bottom)
    # neckradius - the r span of the neck
    # barrelradius - the r span of the barrel. This is the maximum radius of the polycone
    # shoulderfraction - the fraction, from 0 to 1 not inclusive, of the body which is dedicated to this part
    # bottomfraction - same as shoulderfraction, but for the bottom

    # The total height of the skirt is the remainder, except the bottom which exists happily in the skirt
    skirtheight = totalheight - neckheight - (bodyheight * (1 - bottomfraction))
    # The foot at the bottom of the skirt, which I have absolutely no reference for right now
    # Looks like it's about 1/6th of the skirt's total height in the CAD drawing
    # skirtfootfraction = 0.16

    # It's easier for me to visualize this as a top-down process, so we build the heights like that

    # First point - the top of the neck, easy
    z = [totalheight]
    # We need two of them though, to close the neck of the cryostat
    z.append(totalheight - 0.01)
    # Bottom of the neck/top of the body's shoulder
    z.append(totalheight - neckheight)

    # Now, things get a bit weird. I used a plot digitizer to estimate the curve of the shoulder and
    # bottom, with (0,0) and (100,100) being the leftmost and rightmost points. I picked the points
    # by hand, and my hands are unsteady, so apologies if it's not perfectly smooth. I arbitrarily chose
    # 24 data points as the correct amount to model the curves. If you don't like it, you can replace
    # this section with your own data points.
    shoulderzfractions = [
        98.30,
        97.20,
        93.91,
        91.28,
        88.43,
        86.90,
        83.17,
        80.10,
        76.59,
        73.52,
        70.01,
        66.72,
        63.21,
        59.05,
        56.20,
        51.81,
        46.98,
        42.38,
        36.46,
        30.32,
        23.96,
        17.38,
        10.58,
        0.05,
    ]

    for i in shoulderzfractions:
        j = i * 0.01
        z.append(round(totalheight - neckheight - ((1 - j) * shoulderfraction * bodyheight), 2))

    # One last point for good measure, to put us right at the top of the barrel/bottom of the shoulder
    z.append(totalheight - neckheight - (shoulderfraction * bodyheight))
    # Since there are no changes in radius along the barrel, we can skip to the connection of the barrel and the bottom+skirt
    z.append(skirtheight)

    # We do for the bottom as we did for the shoulder, but I reversed the z directionality because it was either that or the
    # radius directionality, and it felt more natural to flip z
    bottomzfractions = [
        16.39,
        26.23,
        33.61,
        40.98,
        47.54,
        53.28,
        55.74,
        59.02,
        64.75,
        67.21,
        70.49,
        74.59,
        78.69,
        80.33,
        82.79,
        86.07,
        88.52,
        90.98,
        92.62,
        94.26,
        95.90,
        97.54,
        99.18,
        99.88,
    ]

    for i in bottomzfractions:
        j = i * 0.01
        z.append(round(skirtheight - (j * bottomfraction * bodyheight), 2))

    # And finally, cap the cryostat's bottom z value
    z.append(round(skirtheight - (bottomfraction * bodyheight), 2))

    # Same process for radius, but with more duplicate values

    # Make sure the neck is solid
    r = [0]
    r.append(neckradius)
    # The neck's height is constant down to where it meets the shoulder
    r.append(neckradius)

    # Same process as for the z values of the shoulder's curve
    shoulderrfractions = [
        98.25,
        92.84,
        86.99,
        81.43,
        76.17,
        70.91,
        65.94,
        60.67,
        55.70,
        50.29,
        45.76,
        40.94,
        36.26,
        32.02,
        27.63,
        23.54,
        19.30,
        15.35,
        11.84,
        8.48,
        5.99,
        3.95,
        1.75,
        0.58,
    ]
    shouldertotalr = barrelradius - neckradius

    for i in shoulderrfractions:
        j = i * 0.01
        r.append(round((1 - j) * shouldertotalr + neckradius, 2))

    # Next, the point at the meeting of the shoulder and the barrel
    r.append(barrelradius)
    # The barrel stays constant, and we skip to the end of the barrel section
    r.append(barrelradius)

    # One more curve for the bottom, and we can move on
    bottomrfractions = [
        1.89,
        4.17,
        6.82,
        10.23,
        14.02,
        18.56,
        21.21,
        23.86,
        28.79,
        31.82,
        34.47,
        39.39,
        44.32,
        46.97,
        49.62,
        54.55,
        59.47,
        64.39,
        68.56,
        73.11,
        76.52,
        82.58,
        88.64,
        93.94,
    ]

    for i in bottomrfractions:
        j = i * 0.01
        r.append(round((1 - j) * barrelradius, 2))

    # The bottom closes to a single point as well, of course
    r.append(0)

    # Final formatting adjustments and diagnostics

    # Polycones are weird - it might behoove us to simply adjust the z values here
    for i in range(len(z)):
        z[i] = z[i] - 5000

    # Turns out pyg4ometry only has the historic definition of G4GenericPolycone added :^/
    # Not a huge deal, but it does mean we have to inverse the r and z lists
    # since the historic definition only allows to build from the bottom upwards
    r.reverse()
    z.reverse()

    # For testing/diagnostics
    # print(r)
    # print(z)
    # print(len(z))
    # print(len(r))

    return z, r


def make_z_and_r_inner_volumes(
    neckradius: float, tubeheight: float, totalheight: float, curvefraction: float
) -> tuple[list, list]:
    # The RT is much simpler - it only has one curved side and one radius

    # Start at the top, as usual
    z = [totalheight - 1]

    # Makes sure it's a closed polycone
    z.append(totalheight - 1.00001)

    # Go all the way to the bottom of the cylindrical section
    nowheight = totalheight - tubeheight * (1 - curvefraction)
    z.append(nowheight)

    # For now just use the r and z fractions from the bottom of the cryostat
    curvezfractions = [
        16.39,
        26.23,
        33.61,
        40.98,
        47.54,
        53.28,
        55.74,
        59.02,
        64.75,
        67.21,
        70.49,
        74.59,
        78.69,
        80.33,
        82.79,
        86.07,
        88.52,
        90.98,
        92.62,
        94.26,
        95.90,
        97.54,
        99.18,
        99.88,
    ]

    for i in curvezfractions:
        j = i * 0.01
        z.append(round(nowheight - (j * curvefraction * tubeheight), 2))

    # Final point where r = 0
    z.append(totalheight - tubeheight)

    # Closed polycone
    r = [0]
    r.append(neckradius)
    # To the bottom of the cylindrical section
    r.append(neckradius)

    curverfractions = [
        1.89,
        4.17,
        6.82,
        10.23,
        14.02,
        18.56,
        21.21,
        23.86,
        28.79,
        31.82,
        34.47,
        39.39,
        44.32,
        46.97,
        49.62,
        54.55,
        59.47,
        64.39,
        68.56,
        73.11,
        76.52,
        82.58,
        88.64,
        93.94,
    ]

    for i in curverfractions:
        j = i * 0.01
        r.append(neckradius * (1 - j))

    # Final point where r = 0
    r.append(0)

    # Final formatting adjustments and diagnostics

    # Polycones are weird - it might behoove us to simply adjust the z values here
    for i in range(len(z)):
        z[i] = z[i] - 5000

    r.reverse()
    z.reverse()

    # For testing/diagnostics
    # print(r)
    # print(z)
    # print(len(z))
    # print(len(r))

    return z, r


def make_moderator_z_r_r(
    modheight: float, modradius: float, modthickness: float, tuberadius: float
) -> tuple[list, list, list]:
    # Instead of a polycone, we use a G4Polyhedra for the moderator
    # It's assumed that the moderator will not have curved sides

    # z first since it's easiest
    z = [modheight]
    # First change happens after one thickness
    z.append(modheight - modthickness)
    # But happens suddenly
    z.append(modheight - modthickness - 0.001)
    # Next happens one thickness from the bottom
    z.append(modthickness + 0.001)
    # And suddenly
    z.append(modthickness)
    # Final point at the bottom
    z.append(0)

    # Outer radius is actually probably easiest - it's constant lmao
    r_outer = [modradius, modradius, modradius, modradius, modradius, modradius]

    # Inner radius leaves a hole for the reentrance tube, hollows out the inside,
    # then closes the bottom. The hole's "radius" is the radius of an
    # inscribing circle, so that the polyhedron is larger than the circle.
    r_inner = [tuberadius]
    # Stays constant until the aperture is through the mod's thickness
    r_inner.append(tuberadius)
    r_inner.append(modradius - modthickness)
    r_inner.append(modradius - modthickness)
    r_inner.append(0)
    r_inner.append(0)

    # print(z)
    # print(r_inner)
    # print(r_outer)

    return z, r_inner, r_outer


def construct_outer_cryostat(
    cryostat_material: g4.Material, reg: g4.Registry, ocryo_r: list, ocryo_z: list
) -> g4.LogicalVolume:
    ocryo_solid = g4.solid.GenericPolycone("ocryo_sol", 0, 2 * pi, ocryo_r, ocryo_z, reg, "mm")

    return g4.LogicalVolume(ocryo_solid, cryostat_material, "outercryostat", reg)


def construct_vacuum_gap(
    vac_material: g4.Material, reg: g4.Registry, vac_r: list, vac_z: list
) -> g4.LogicalVolume:
    vac_solid = g4.solid.GenericPolycone("vac_sol", 0, 2 * pi, vac_r, vac_z, reg, "mm")

    return g4.LogicalVolume(vac_solid, vac_material, "vacuumgap", reg)


def construct_inner_cryostat(
    cryostat_material: g4.Material, reg: g4.Registry, icryo_r: list, icryo_z: list
) -> g4.LogicalVolume:
    icryo_solid = g4.solid.GenericPolycone("icryo_sol", 0, 2 * pi, icryo_r, icryo_z, reg, "mm")

    return g4.LogicalVolume(icryo_solid, cryostat_material, "innercryostat", reg)


def construct_atmospheric_lar(
    lar_material: g4.Material, reg: g4.Registry, atmlar_r: list, atmlar_z: list
) -> g4.LogicalVolume:
    atmlar_solid = g4.solid.GenericPolycone("atmlar_sol", 0, 2 * pi, atmlar_r, atmlar_z, reg, "mm")

    return g4.LogicalVolume(atmlar_solid, lar_material, "atmosphericlar", reg)


def construct_reentrance_tube(
    tube_material: g4.Material, reg: g4.Registry, tube_r: list, tube_z: list
) -> g4.LogicalVolume:
    tube_solid = g4.solid.GenericPolycone("tube_sol", 0, 2 * pi, tube_r, tube_z, reg, "mm")

    return g4.LogicalVolume(tube_solid, tube_material, "reentrancetube", reg)


def construct_underground_lar(
    lar_material: g4.Material, reg: g4.Registry, uglar_r: list, uglar_z: list
) -> g4.LogicalVolume:
    uglar_solid = g4.solid.GenericPolycone("uglar_sol", 0, 2 * pi, uglar_r, uglar_z, reg, "mm")

    return g4.LogicalVolume(uglar_solid, lar_material, "undergroundlar", reg)


def construct_moderator_simple(
    mod_material: g4.Material,
    reg: g4.Registry,
    mod_r_inner: list,
    mod_r_outer: list,
    mod_z: list,
    modnsides: int,
    mother_lv: g4.LogicalVolume,
):
    mod_solid = g4.solid.Polyhedra(
        "mod_sol", 0, 2 * pi, modnsides, len(mod_z), mod_z, mod_r_inner, mod_r_outer, reg, "mm"
    )
    mod_lv = g4.LogicalVolume(mod_solid, mod_material, "neutronmoderator", reg)
    g4.PhysicalVolume([0, 0, 0], [0, 0, -2900], mod_lv, "neutronmoderator", mother_lv, reg)  # -3000
    # Z value used to be -bodyheight/2.*(1-bottomfraction)
    # Could import this if we wanted, but maybe this method has enough arguments already...


def construct_moderator_stl(mod_material: g4.Material, reg: g4.Registry, mother_lv: g4.LogicalVolume):
    # There are 50 parts for the neutron moderator, numbered 0 to 49
    # There are an additional 289(!) parts for the moderator's metal support structure
    # The steel pieces are also much more complex than the plastic pieces
    # For now, omitting the steel pieces. If a RMG user really cares about them, we can implement them
    for i in range(49):
        mod_name = f"moderator_{i}"
        mod_file = resources.files("l1000geom") / "models" / f"modpiece_{i}.stl"
        mod_solid = pyg4ometry.stl.Reader(mod_file, solidname=mod_name, registry=reg).getSolid()
        mod_lv = g4.LogicalVolume(mod_solid, mod_material, mod_name, reg)
        g4.PhysicalVolume([0, 0, 0], [0, 0, -1250], mod_lv, mod_name, mother_lv, reg)


def construct_and_place_cryostat(instr: core.InstrumentationData) -> g4.PhysicalVolume:
    if "cryostat" not in instr.detail:
        msg = "No 'cryostat' detail specified in the special metadata."
        raise ValueError(msg)

    if instr.detail["cryostat"] == "omit":
        return instr

    # We must define these 7 parameters for each of the cryostat polycones
    # You can find the definitions in the preamble or in make_z_and_r
    totalheight = 10000  # 10200
    neckheight = 1940  # 2000
    bodyheight = 7750  # 8000 #7000
    neckradius = 1200
    # neckradius = 1900 / 2. # 1.9m diameter
    # barrelradius = 3800
    shoulderfraction = 0.233
    bottomfraction = 0.233

    # The following parameters are internal to this class. Definitions should be obvious if you read the definitions in the other
    # two places mentioned before
    ocryo_thickness = 60
    # However, I should mention the vacuum gap is asymmetric - it has distinct values at the neck, barrel, and bottom
    vgapthickness_neck = 120
    vgapthickness_barrel = 200  # 500  # 400
    vgapthickness_bottom = 150  # 100
    icryo_thickness = 40

    barrelradius = 3500 + icryo_thickness + ocryo_thickness + vgapthickness_barrel

    # Separated, because these are parameters for the reentrance tube and the UGLar, which have another make_z_and_r class
    # However the radius is controlled by the cryostat neck radius, and doesn't get specified manually
    # tubeheight = 7500
    tubeheight = 6750  # - 494.45 #7500 #7000  #
    curvefraction = 0.05
    tubethickness = 1

    # The skirt and moderator are unlike any other shapes and need their own parameters and constructors
    # The skirt borrows some parameters from the outer cryostat, to make sure it connects with the barrel
    # The one thing we can define about the moderator is that the aperture should be just slightly bigger than the neckradius

    modheight = 3200
    modradius = 1820
    modthickness = 100
    modnsides = 12

    skirtheight = totalheight - neckheight - (bodyheight * (1 - bottomfraction))
    skirtradius = barrelradius
    skirtz = -bodyheight / 2 - ocryo_thickness * 3.2
    skirtthickness = 60  # A guess
    footheight = 150
    footwidth = 150  # Not really a guess so much as a placeholder...

    skirt_solid = g4.solid.Tubs(
        "skirt_sol",
        skirtradius - skirtthickness,
        skirtradius,
        skirtheight - (ocryo_thickness * 7),
        0,
        2 * pi,
        instr.registry,
        "mm",
    )
    skirt_lv = g4.LogicalVolume(skirt_solid, instr.materials.metal_steel, "skirt", instr.registry)
    foot_solid = g4.solid.Tubs(
        "foot_sol", skirtradius, skirtradius + footwidth, footheight, 0, 2 * pi, instr.registry, "mm"
    )
    foot_lv = g4.LogicalVolume(foot_solid, instr.materials.metal_steel, "foot", instr.registry)

    ocryo_z, ocryo_r = make_z_and_r(
        totalheight, neckheight, bodyheight, neckradius, barrelradius, shoulderfraction, bottomfraction
    )

    outercryo_lv = construct_outer_cryostat(instr.materials.metal_steel, instr.registry, ocryo_r, ocryo_z)
    outercryo_lv.pygeom_color_rgba = [0.5, 0.5, 0.5, 0.25]

    # For the vacuum gap, it should be as simple as subtracting the outer cryostat thicknesses
    # The neck height stays the same, effectively lowering the body by the thickness
    # The totalheight actually controls where the top of the polycone is, and we only want to lower it by one thickness.
    # We could opt to not lower it at all, effectively leaving the top open, but I think it's better to have a 'cap' to at
    # least slightly represent the lock system.

    totalheight = totalheight - ocryo_thickness
    bodyheight = bodyheight - 2 * ocryo_thickness
    neckradius = neckradius - ocryo_thickness
    barrelradius = barrelradius - ocryo_thickness

    vac_z, vac_r = make_z_and_r(
        totalheight, neckheight, bodyheight, neckradius, barrelradius, shoulderfraction, bottomfraction
    )

    vac_lv = construct_vacuum_gap(instr.materials.vacuum, instr.registry, vac_r, vac_z)
    vac_lv.pygeom_color_rgba = [0.6, 0.0, 0.6, 0.1]

    # Here things are a bit more complicated with the asymmetric vacuum gap
    # Of course, there is no vacuum gap at the top of the neck - that's where the lock goes

    # Again, effectively push the body downwards using the neck height as our activator
    neckheight = neckheight + vgapthickness_neck
    # ...Which means the body must be shortened by this amount, plus the bottom vacgap amount
    bodyheight = bodyheight - vgapthickness_neck - vgapthickness_bottom

    neckradius = neckradius - vgapthickness_neck
    barrelradius = barrelradius - vgapthickness_barrel

    icryo_z, icryo_r = make_z_and_r(
        totalheight, neckheight, bodyheight, neckradius, barrelradius, shoulderfraction, bottomfraction
    )

    icryo_lv = construct_inner_cryostat(instr.materials.liquidargon, instr.registry, icryo_r, icryo_z)
    icryo_lv.pygeom_color_rgba = [0.5, 0.5, 0.5, 0.25]

    # The next layer should be again just subtracting by the inner cryo thickness everywhere
    totalheight = totalheight - icryo_thickness
    bodyheight = bodyheight - 2 * icryo_thickness
    neckradius = neckradius - icryo_thickness
    barrelradius = barrelradius - icryo_thickness

    atmlar_z, atmlar_r = make_z_and_r(
        totalheight, neckheight, bodyheight, neckradius, barrelradius, shoulderfraction, bottomfraction
    )

    atmlar_lv = construct_atmospheric_lar(instr.materials.liquidargon, instr.registry, atmlar_r, atmlar_z)
    atmlar_lv.pygeom_color_rgba = [0.1, 0.8, 0.3, 0.1]

    # The RT and UGLAr have a totally different shape than the cryostat bodies
    # They need to have their own smaller r/z method

    tube_z, tube_r = make_z_and_r_inner_volumes(neckradius, tubeheight, totalheight, curvefraction)

    tube_lv = construct_reentrance_tube(instr.materials.metal_copper, instr.registry, tube_r, tube_z)
    tube_lv.pygeom_color_rgba = [0.8, 0.7, 0.1, 0.2]

    if "nm_plastic" not in instr.detail:
        log.warning("Warning: neutron moderator not specified. Omitting by default.")

    elif instr.detail["nm_plastic"] == "simple":
        mod_z, mod_r_inn, mod_r_out = make_moderator_z_r_r(modheight, modradius, modthickness, neckradius + 1)
        construct_moderator_simple(
            instr.materials.pmma, instr.registry, mod_r_inn, mod_r_out, mod_z, modnsides, atmlar_lv
        )

    elif instr.detail["nm_plastic"] == "stl":
        construct_moderator_stl(instr.materials.pmma, instr.registry, atmlar_lv)

    # Finally, the RT should be filled with LAr

    neckradius = neckradius - tubethickness
    tubeheight = tubeheight - tubethickness

    uglar_z, uglar_r = make_z_and_r_inner_volumes(neckradius, tubeheight, totalheight, curvefraction)

    uglar_lv = construct_underground_lar(instr.materials.liquidargon, instr.registry, uglar_r, uglar_z)
    uglar_lv.pygeom_color_rgba = [0.1, 0.8, 0.3, 0.1]

    # Place the physical volumes at the end
    # Move the cryostat back in a central position

    if instr.detail["watertank"] == "omit":
        g4.PhysicalVolume([0, 0, 0], [0, 0, skirtz], skirt_lv, "skirt", instr.mother_lv, instr.registry)
        g4.PhysicalVolume(
            [0, 0, 0],
            [0, 0, skirtz - skirtheight / 2 + footheight / 2],
            foot_lv,
            "foot",
            instr.mother_lv,
            instr.registry,
        )
    else:
        g4.PhysicalVolume(
            [0, 0, 0], [0, 0, skirtheight / 2.0], skirt_lv, "skirt", instr.mother_lv, instr.registry
        )
        g4.PhysicalVolume(
            [0, 0, 0], [0, 0, footheight / 2.0 + 20], foot_lv, "foot", instr.mother_lv, instr.registry
        )

    g4.PhysicalVolume(
        [0, 0, 0],
        [0, 0, -instr.mother_z_displacement],
        outercryo_lv,
        "outercryostat",
        instr.mother_lv,
        instr.registry,
    )

    g4.PhysicalVolume([0, 0, 0], [0, 0, 0], vac_lv, "vacuumgap", outercryo_lv, instr.registry)
    g4.PhysicalVolume([0, 0, 0], [0, 0, 0], icryo_lv, "innercryostat", vac_lv, instr.registry)
    g4.PhysicalVolume([0, 0, 0], [0, 0, 0], atmlar_lv, "atmosphericlar", icryo_lv, instr.registry)
    g4.PhysicalVolume([0, 0, 0], [0, 0, 0], tube_lv, "reentrancetube", atmlar_lv, instr.registry)
    uglar_pv = g4.PhysicalVolume([0, 0, 0], [0, 0, 0], uglar_lv, "undergroundlar", tube_lv, instr.registry)

    # NamedTuples are immutable, so we need to create a copy
    return instr._replace(mother_lv=uglar_lv, mother_pv=uglar_pv, mother_z_displacement=0)
