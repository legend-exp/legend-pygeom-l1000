from __future__ import annotations

from math import pi

import pyg4ometry.geant4 as g4

PMT_eff_radius = 131  # Best value to fit it to the CAD. The technical drawing is very unclear.
cutoff = 41  # The PMT front is just the top part of the ellipsoid
cathode_cutoff = 65


def construct_PMT_front(glassmat, vacmat, reg: g4.Registry) -> g4.LogicalVolume:
    top_window = g4.solid.Ellipsoid(
        "PMT_window", PMT_eff_radius, PMT_eff_radius, PMT_eff_radius, cutoff, 200, reg, "mm"
    )

    vacuum_radius = 128  # Results in a glass window thickness of ~3mm
    vacuum_height = PMT_eff_radius - 2

    top_vacuum = g4.solid.Ellipsoid(
        "PMT_vacuum", vacuum_radius, vacuum_radius, vacuum_height, cutoff, 200, reg, "mm"
    )

    top_window_logical = g4.LogicalVolume(top_window, glassmat, "PMT_window_logical", reg)
    top_vacuum_logical = g4.LogicalVolume(top_vacuum, vacmat, "PMT_vacuum_logical", reg)
    g4.PhysicalVolume(
        [0, 0, 0], [0, 0, 0], top_vacuum_logical, "PMT_vacuum_physical", top_window_logical, reg
    )

    top_cathode = g4.solid.Ellipsoid(
        "PMT_cathode", vacuum_radius, vacuum_radius, vacuum_height, cathode_cutoff, 200, reg, "mm"
    )

    top_cathode_logical = g4.LogicalVolume(top_cathode, vacmat, "PMT_cathode_logical", reg)

    g4.PhysicalVolume(
        [0, 0, 0], [0, 0, 0], top_cathode_logical, "PMT_cathode_physical", top_vacuum_logical, reg
    )
    return top_window_logical


def construct_PMT_back(mat, reg: g4.Registry) -> g4.LogicalVolume:
    base_r = 42.25
    base_z = 72
    r = [0, base_r, base_r, 52.25, 102.75, 125, 0]
    z = [0, 0, base_z, 82, 110, 145, 145]

    back = g4.solid.GenericPolycone("PMT_back", 0, 2 * pi, r, z, reg, "mm")
    return g4.LogicalVolume(back, mat, "PMT_back", reg)


# reg = g4.Registry()
# mat = g4.MaterialPredefined("G4_TEFLON")

# world_material = g4.MaterialPredefined("G4_Galactic")
# world = g4.solid.Box("world", 1, 2, 1, reg, "m")
# world_lv = g4.LogicalVolume(world, world_material, "world", reg)
# reg.setWorld(world_lv)

# l = construct_simplified_PMT(reg)
# pmt = construct_PMT_front(mat, world_material, reg)
# pmt_back = construct_PMT_back(mat, reg)

# g4.PhysicalVolume([0, 0, 0], [0, 0, 0], l, "tank", world_lv, reg)
# g4.PhysicalVolume([0, 0, 0], [0, 300, 145 - (PMT_eff_radius - 90)], pmt, "pmt_top", world_lv, reg)
# g4.PhysicalVolume([0, 0, 0], [0, 300, 0], pmt_back, "pmt_bot", world_lv, reg)

# l.pygeom_color_rgba = [1, 1, 0, 1]

# v = pyg4ometry.visualisation.VtkViewerColouredMaterial()

# v.addLogicalVolume(pmt)

# v.view()

# w = pyg4ometry.gdml.Writer()
# #
# w.addDetector(reg)
# #
# w.write('/home/eric/sim/ReMaGe/RMGApplications/05-NavBench/gdml/test.gdml')
