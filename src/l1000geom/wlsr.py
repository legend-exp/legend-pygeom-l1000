"""WLSR placement with TPB as parent volume and TTX as daughter"""

from __future__ import annotations

import numpy as np
import pyg4ometry.geant4 as g4

from .rt_profiles import (
    make_inner_wlsr_profiles,
    make_outer_wlsr_profiles,
)


def _add_wls_surfaces(
    materials,
    reg: g4.Registry,
    tpb_pv: g4.PhysicalVolume,
    tetratex_pv: g4.PhysicalVolume,
    lar_pv: g4.PhysicalVolume,
    prefix: str = "",
) -> None:
    """Add optical border surfaces for WLS layers."""

    g4.BorderSurface(
        f"bsurface_{prefix}tpb_ttx",
        tpb_pv,
        tetratex_pv,
        materials.surfaces.wlsr_tpb_to_tetratex,
        reg,
    )
    g4.BorderSurface(f"bsurface_{prefix}lar_tpb", lar_pv, tpb_pv, materials.surfaces.lar_to_tpb, reg)
    g4.BorderSurface(f"bsurface_{prefix}tpb_lar", tpb_pv, lar_pv, materials.surfaces.lar_to_tpb, reg)


def place_inner_wlsr_in_argon(
    materials,
    registry: g4.Registry,
    lar_cavity_lv: g4.LogicalVolume,
    lar_cavity_pv: g4.PhysicalVolume,
    neck_radius: float,
    tube_height: float,
    total_height: float,
    curve_fraction: float,
    wls_height: float,
    inner_z: list[float],
    inner_r: list[float],
    outer_z: list[float],
    outer_r: list[float],
) -> None:
    """
    Place inner WLS layers in the underground argon.
    """
    result = make_inner_wlsr_profiles(
        neck_radius, tube_height, total_height, curve_fraction, wls_height, inner_z, inner_r
    )

    # Create TPB polycones (PARENT/MOTHER volume)
    tpb_outer_bound = g4.solid.GenericPolycone(
        "tpb_inner_argon_outer_bound", 0, 2 * np.pi, result.tpb_outer_r, result.tpb_outer_z, registry, "mm"
    )
    tpb_inner_bound = g4.solid.GenericPolycone(
        "tpb_inner_argon_inner_bound", 0, 2 * np.pi, result.tpb_inner_r, result.tpb_inner_z, registry, "mm"
    )
    tpb_solid = g4.solid.Subtraction(
        "tpb_inner_argon_solid", tpb_outer_bound, tpb_inner_bound, [[0, 0, 0], [0, 0, 0, "mm"]], registry
    )

    wls_tpb_inner_lv = g4.LogicalVolume(
        tpb_solid, materials.tpb_on_tetratex, "wls_tpb_inner_argon_lv", registry
    )
    wls_tpb_inner_lv.pygeom_color_rgba = False
    tpb_inner_pv = g4.PhysicalVolume(
        [0, 0, 0],
        [0, 0, 0, "mm"],
        wls_tpb_inner_lv,
        "wls_tpb_inner_argon",
        lar_cavity_lv,
        registry=registry,
    )

    # Create TTX polycones (DAUGHTER volume inside TPB)
    tetratex_outer_bound = g4.solid.GenericPolycone(
        "tetratex_inner_argon_outer_bound",
        0,
        2 * np.pi,
        result.ttx_outer_r,
        result.ttx_outer_z,
        registry,
        "mm",
    )
    tetratex_inner_bound = g4.solid.GenericPolycone(
        "tetratex_inner_argon_inner_bound",
        0,
        2 * np.pi,
        result.ttx_inner_r,
        result.ttx_inner_z,
        registry,
        "mm",
    )
    tetratex_solid = g4.solid.Subtraction(
        "wls_tetratex_inner_argon_solid",
        tetratex_outer_bound,
        tetratex_inner_bound,
        [[0, 0, 0], [0, 0, 0, "mm"]],
        registry,
    )

    wls_tetratex_inner_lv = g4.LogicalVolume(
        tetratex_solid, materials.tetratex, "wls_tetratex_inner_argon_lv", registry
    )
    wls_tetratex_inner_lv.pygeom_color_rgba = (1.0, 1.0, 1.0, 0.1)

    # Place TTX INSIDE TPB (parent is TPB logical volume)
    tetratex_inner_pv = g4.PhysicalVolume(
        [0, 0, 0],
        [0, 0, 0, "mm"],
        wls_tetratex_inner_lv,
        "wls_tetratex_inner_argon",
        wls_tpb_inner_lv,
        registry=registry,
    )

    _add_wls_surfaces(materials, registry, tpb_inner_pv, tetratex_inner_pv, lar_cavity_pv, prefix="inner_")


def place_outer_wlsr_in_atmospheric(
    materials,
    registry: g4.Registry,
    lar_mother_lv: g4.LogicalVolume,
    lar_mother_pv: g4.PhysicalVolume,
    neck_radius: float,
    tube_height: float,
    total_height: float,
    curve_fraction: float,
    wls_height: float,
    outer_z: list[float],
    outer_r: list[float],
) -> None:
    """
    Place outer WLS layers in the atmospheric argon.
    """
    result = make_outer_wlsr_profiles(
        neck_radius, tube_height, total_height, curve_fraction, wls_height, outer_z, outer_r
    )

    # Create TPB polycones (PARENT/MOTHER volume)
    tpb_outer_bound = g4.solid.GenericPolycone(
        "tpb_outer_atmospheric_outer_bound",
        0,
        2 * np.pi,
        result.tpb_outer_r,
        result.tpb_outer_z,
        registry,
        "mm",
    )
    tpb_inner_bound = g4.solid.GenericPolycone(
        "tpb_outer_atmospheric_inner_bound",
        0,
        2 * np.pi,
        result.tpb_inner_r,
        result.tpb_inner_z,
        registry,
        "mm",
    )
    tpb_solid = g4.solid.Subtraction(
        "tpb_outer_atmospheric_solid",
        tpb_outer_bound,
        tpb_inner_bound,
        [[0, 0, 0], [0, 0, 0, "mm"]],
        registry,
    )

    wls_tpb_outer_lv = g4.LogicalVolume(
        tpb_solid, materials.tpb_on_tetratex, "wls_tpb_outer_atmospheric_lv", registry
    )
    wls_tpb_outer_lv.pygeom_color_rgba = False
    tpb_outer_pv = g4.PhysicalVolume(
        [0, 0, 0],
        [0, 0, 0, "mm"],
        wls_tpb_outer_lv,
        "wls_tpb_outer_atmospheric",
        lar_mother_lv,
        registry=registry,
    )

    # Create TTX polycones (DAUGHTER volume inside TPB)
    tetratex_outer_bound = g4.solid.GenericPolycone(
        "tetratex_outer_atmospheric_outer_bound",
        0,
        2 * np.pi,
        result.ttx_outer_r,
        result.ttx_outer_z,
        registry,
        "mm",
    )
    tetratex_inner_bound = g4.solid.GenericPolycone(
        "tetratex_outer_atmospheric_inner_bound",
        0,
        2 * np.pi,
        result.ttx_inner_r,
        result.ttx_inner_z,
        registry,
        "mm",
    )
    tetratex_solid = g4.solid.Subtraction(
        "wls_tetratex_outer_atmospheric_solid",
        tetratex_outer_bound,
        tetratex_inner_bound,
        [[0, 0, 0], [0, 0, 0, "mm"]],
        registry,
    )

    wls_tetratex_outer_lv = g4.LogicalVolume(
        tetratex_solid, materials.tetratex, "wls_tetratex_outer_atmospheric_lv", registry
    )
    wls_tetratex_outer_lv.pygeom_color_rgba = (1.0, 1.0, 1.0, 0.1)

    # Place TTX INSIDE TPB (parent is TPB logical volume)
    tetratex_outer_pv = g4.PhysicalVolume(
        [0, 0, 0],
        [0, 0, 0, "mm"],
        wls_tetratex_outer_lv,
        "wls_tetratex_outer_atmospheric",
        wls_tpb_outer_lv,
        registry=registry,
    )

    _add_wls_surfaces(materials, registry, tpb_outer_pv, tetratex_outer_pv, lar_mother_pv, prefix="outer_")
