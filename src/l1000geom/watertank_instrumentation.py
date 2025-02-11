"""Construct the instrumentation inside of the water tank.

Dimensions from latest CAD from 2025-01-24.
"""

from __future__ import annotations

from math import pi

import pyg4ometry.geant4 as g4

from . import watertank

# The reflective Teflon foil that separates the active optical volume
teflon_outer_radius = 4785.0
teflon_inner_radius = 4775.0
# Some trygonometry to get the effective height of the teflon foil
out = watertank.tank_base_radius - 10 - teflon_outer_radius
h_diff = watertank.tank_top_height - watertank.tank_base_height
inner = watertank.tank_base_radius - 20 - watertank.tank_top_bulge_width / 2
teflon_effective_height = (
    watertank.tank_base_height - 40 + out * h_diff / inner
)  # Such that it ends flush with the top of the water tank


# The PMT parts
# The PMTs are the R7081-20-100 from Hammamatsu
# https://hep.hamamatsu.com/content/dam/hamamatsu-photonics/sites/documents/99_SALES_LIBRARY/etd/LARGE_AREA_PMT_TPMH1376E.pdf
PMT_eff_radius = (
    131  # Best value to fit the spherical part to 250mm diameter. The technical drawing is very unclear.
)
cutoff = 41  # Cutoff to take the top part of the ellipsoid resulting in 250mm diameter.
cathode_cutoff = 65  # cutoff such that the effective cathode radius is 220mm.


def construct_PMT_front(reg: g4.Registry) -> g4.solid:
    """Construct the solids for the front part of the PMT.
    Consists of glass window, vacuum and cathode.
    These solids should be placed as mother-to-daughter: window <- vacuum <- cathode
    """
    top_window = g4.solid.Ellipsoid(
        "PMT_window", PMT_eff_radius, PMT_eff_radius, PMT_eff_radius, cutoff, 200, reg, "mm"
    )

    vacuum_radius = 128  # Results in a glass window thickness of ~2-3mm
    vacuum_height = PMT_eff_radius - 2

    top_vacuum = g4.solid.Ellipsoid(
        "PMT_vacuum", vacuum_radius, vacuum_radius, vacuum_height, cutoff, 200, reg, "mm"
    )

    top_cathode = g4.solid.Ellipsoid(
        "PMT_cathode", vacuum_radius, vacuum_radius, vacuum_height, cathode_cutoff, 200, reg, "mm"
    )

    # To be able to register the individual photocathodes as detectors,
    # we need to place them individually. So return only logical volumes here.
    return top_window, top_vacuum, top_cathode


def construct_PMT_back(reg: g4.Registry) -> g4.LogicalVolume:
    base_r = 42.25  # values roughly measured from the CAD.
    base_z = 72  # They do not need to be precise
    r = [0, base_r, base_r, 52.25, 102.75, 125, 0]
    z = [0, 0, base_z, 82, 110, 145, 145]

    return g4.solid.GenericPolycone("PMT_back", 0, 2 * pi, r, z, reg, "mm")


def construct_teflon_foil(reg: g4.Registry) -> g4.solid:
    return g4.solid.Tubs(
        "water_teflon_foil",
        teflon_inner_radius,
        teflon_outer_radius,
        teflon_effective_height,
        0,
        2 * pi,
        reg,
        "mm",
    )


def construct_instrumentation(
    wl: g4.LogicalVolume, mat, reg: g4.Registry, detail: str = "low"
) -> g4.LogicalVolume:
    """Construct the instrumentation inside of the water tank.

    Parameters
    ----------
    wl : g4.LogicalVolume
        The logical volume of the water.
    detail : str
        The level of detail to use for the construction. Options are "low", "medium" and "high".
    """

    # Place Teflon foil
    # (This way the whole water is optical, which is not optimal)

    # Place inner PMT parts

    session = construct_teflon_foil(reg)
    return g4.LogicalVolume(session, mat, "teflon", reg)
    # if detail == "low":

    # # Place Scaffold

    # # Place outer PMT parts
