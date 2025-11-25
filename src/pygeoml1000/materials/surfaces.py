"""Subpackage to provide all implemented optical surfaces and their properties."""

from __future__ import annotations

import numpy as np
import pint
import pyg4ometry.geant4 as g4
import pygeomoptics.copper
import pygeomoptics.germanium
import pygeomoptics.silicon
import pygeomoptics.tetratex
import pygeomoptics.tyvek
from pygeomtools.materials import cached_property

from .ketek_sipm import ketek_sipm_efficiency

u = pint.get_application_registry()


class OpticalSurfaceRegistry:
    """Register and define optical surfaces.

    Note on Models
    --------------

    * UNIFIED model:
        `value` is the `sigma_alpha` parameter, the stddev of the newly chosen facet normal direction.
        For details on this model and its parameters, see `UNIFIED model diagram`_.
    * GLISUR model:
        `value` as smoothness, in range [0,1] (0=rough, 1=perfectly smooth).

    UNIFIED is more comprehensive, but is not directly equivalent to GLISUR. One notable difference is
    that UNIFIED/ground surfaces w/o specular probabilities set will not perform total internal reflection
    according to alpha1=alpha2, whereas GFLISUR/ground will do! Polished surfaces should behave similar
    between UNIFIED and GLISUR.

    .. _UNIFIED model diagram: https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/_images/UNIFIED_model_diagram.png
    """

    def __init__(self, reg: g4.Registry):
        self.g4_registry = reg
        # do not change the surface model w/o also changing all surface values below!
        self._model = "unified"

    @cached_property
    def to_copper(self) -> g4.solid.OpticalSurface:
        """Reflective surface for copper structure."""
        _to_copper = g4.solid.OpticalSurface(
            "surface_to_copper",
            finish="ground",
            model=self._model,
            surf_type="dielectric_metal",
            value=0.5,  # rad. converted from 0.5, probably a GLISUR smoothness parameter, in MaGe.
            registry=self.g4_registry,
        )

        pygeomoptics.copper.pyg4_copper_attach_reflectivity(_to_copper, self.g4_registry)

        return _to_copper

    @cached_property
    def to_germanium(self) -> g4.solid.OpticalSurface:
        """Reflective surface for germanium detectors."""
        _to_germanium = g4.solid.OpticalSurface(
            "surface_to_germanium",
            finish="ground",
            model=self._model,
            surf_type="dielectric_metal",
            value=0.3,  # rad. converted from 0.5, probably a GLISUR smoothness parameter, in MaGe.
            registry=self.g4_registry,
        )

        pygeomoptics.germanium.pyg4_germanium_attach_reflectivity(_to_germanium, self.g4_registry)

        return _to_germanium

    @cached_property
    def wlsr_tpb_to_tetratex(self) -> g4.solid.OpticalSurface:
        """Reflective surface Tetratex diffuse reflector."""
        _wlsr_tpb_to_tetratex = g4.solid.OpticalSurface(
            "surface_wlsr_tpb_to_tetratex",
            finish="groundfrontpainted",  # only lambertian reflection
            model=self._model,
            surf_type="dielectric_dielectric",
            value=0,  # rad. perfectly lambertian reflector.
            registry=self.g4_registry,
        )

        pygeomoptics.tetratex.pyg4_tetratex_attach_reflectivity(_wlsr_tpb_to_tetratex, self.g4_registry)

        return _wlsr_tpb_to_tetratex

    @cached_property
    def to_sipm_silicon(self) -> g4.solid.OpticalSurface:
        """Reflective surface for KETEK SiPM."""
        _to_sipm_silicon = g4.solid.OpticalSurface(
            "surface_to_sipm_silicon",
            finish="ground",
            model=self._model,
            surf_type="dielectric_metal",
            value=0.05,  # converted from 0.9, probably a GLISUR smoothness parameter, in MaGe.
            registry=self.g4_registry,
        )

        pygeomoptics.silicon.pyg4_silicon_attach_complex_rindex(_to_sipm_silicon, self.g4_registry)

        # add custom efficiency for the KETEK SiPMs. This is not part of pygeomoptics.
        λ, eff = ketek_sipm_efficiency()
        with u.context("sp"):
            _to_sipm_silicon.addVecPropertyPint("EFFICIENCY", λ.to("eV"), eff)

        return _to_sipm_silicon

    @cached_property
    def lar_to_tpb(self) -> g4.solid.OpticalSurface:
        """Optical surface between LAr and TBP wavelength shifting coating."""
        return g4.solid.OpticalSurface(
            "surface_lar_to_tpb",
            finish="ground",
            model="unified",
            surf_type="dielectric_dielectric",
            value=0.3,  # rad. converted from 0.5, probably a GLISUR smoothness parameter, in MaGe.
            registry=self.g4_registry,
        )

    @cached_property
    def lar_to_pen(self) -> g4.solid.OpticalSurface:
        """Optical surface between LAr and PEN scintillator/wavelength shifting coating."""
        _lar_to_pen = g4.solid.OpticalSurface(
            "surface_lar_to_pen",
            finish="ground",
            model="unified",
            surf_type="dielectric_dielectric",
            # sigma_alpha corresponds to the value from L. Manzanillas et al 2022 JINST 17 P09007.
            value=0.01,  # rad.
            registry=self.g4_registry,
        )

        # set specular spike/lobe probabilities. From a presentation by L. Manzanillas ("Update on PEN optical
        # parameters for Geant4 studies", 29.04.2021); slide 12 "Recommended data for PEN simulations", both are 0.5.
        # note: MaGe has specularlobe=0.4, specularspike=0.6; but commented out. Luis' last code uses the same values
        # as MaGe:
        # https://github.com/lmanzanillas/AttenuationPenSetup/blob/11ff9664e3b2da3c0ebf726b60ad96111e9b2aaa/src/DetectorConstruction.cc#L1771-L1786
        λ = np.array([650.0, 115.0]) * u.nm
        specular_lobe = np.array([0.4, 0.4])
        specular_spike = np.array([0.6, 0.6])
        with u.context("sp"):
            _lar_to_pen.addVecPropertyPint("SPECULARSPIKECONSTANT", λ.to("eV"), specular_spike)
            _lar_to_pen.addVecPropertyPint("SPECULARLOBECONSTANT", λ.to("eV"), specular_lobe)

        return _lar_to_pen

    @cached_property
    def to_steel(self) -> g4.solid.OpticalSurface:
        """Optical surface of steel."""
        _to_steel = g4.solid.OpticalSurface(
            name="pmt_steel_surface",
            finish="polished",
            model="unified",
            surf_type="dielectric_metal",
            value=0.3,
            registry=self.g4_registry,
        )

        pygeomoptics.pmts.pyg4_pmt_attach_steel_reflectivity(_to_steel, self.g4_registry)

        return _to_steel

    @cached_property
    def to_tyvek(self) -> g4.solid.OpticalSurface:
        """Reflective surface for tyvek."""
        # Create material properties table for tyvek surface
        _to_tyvek = g4.solid.OpticalSurface(
            name="tyvek_foil_surface",
            finish="groundfrontpainted",
            model="unified",
            surf_type="dielectric_dielectric",
            value=0.3,
            registry=self.g4_registry,
        )

        pygeomoptics.tyvek.pyg4_tyvek_attach_reflectivity(_to_tyvek, self.g4_registry)

        return _to_tyvek

    @cached_property
    def to_photocathode(self) -> g4.solid.OpticalSurface:
        """Optical surface of the PMT photocathode."""
        # Detector Surface
        _to_photocathode = g4.solid.OpticalSurface(
            name="pmt_cathode_surface",
            finish="polished",
            model="unified",
            surf_type="dielectric_metal",
            value=0.01,
            registry=self.g4_registry,
        )

        # Need reflectivity. Otherwise Geant4 just assumes 1 and ignores the efficiency (dont ask why)
        pygeomoptics.pmts.pyg4_pmt_attach_photocathode_reflectivity(_to_photocathode, self.g4_registry)
        pygeomoptics.pmts.pyg4_pmt_attach_photocathode_efficiency(
            _to_photocathode, self.g4_registry, name="r7081"
        )

        return _to_photocathode
