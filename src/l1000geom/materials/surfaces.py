"""Subpackage to provide all implemented optical surfaces and their properties."""

from __future__ import annotations

import legendoptics.copper
import legendoptics.silicon
import legendoptics.tetratex
import numpy as np
import pint
import pyg4ometry.geant4 as g4

u = pint.get_application_registry()


class OpticalSurfaceRegistry:
    """Register and define optical surfaces.

    Note on Models
    --------------

    * UNIFIED model:
        `value` is the `sigma_alpha` parameter, the stddev of the newly chosen facet normal direction.
        For details on this model and its parameters, see `UNIFIED model diagram`_.
    * GLISUR model:
        `value` as smoothness, in range [0,1]

    .. _UNIFIED model diagram: https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/_images/UNIFIED_model_diagram.png
    """

    def __init__(self, reg: g4.Registry):
        self.g4_registry = reg
        self._model = "unified"

    @property
    def to_copper(self) -> g4.Material:
        """Reflective surface for copper structure."""
        if hasattr(self, "_to_copper"):
            return self._to_copper

        self._to_copper = g4.solid.OpticalSurface(
            "surface_to_copper",
            finish="ground",
            model=self._model,
            surf_type="dielectric_metal",
            value=0.9,
            registry=self.g4_registry,
        )

        legendoptics.copper.pyg4_copper_attach_reflectivity(
            self._to_copper,
            self.g4_registry,
        )

        return self._to_copper

    @property
    def wlsr_tpb_to_tetratex(self) -> g4.Material:
        """Reflective surface Tetratex diffuse reflector."""
        if hasattr(self, "_wlsr_tpb_to_tetratex"):
            return self._wlsr_tpb_to_tetratex

        self._wlsr_tpb_to_tetratex = g4.solid.OpticalSurface(
            "surface_wlsr_tpb_to_tetratex",
            finish="groundfrontpainted",
            model=self._model,
            surf_type="dielectric_dielectric",
            value=0.9,
            registry=self.g4_registry,
        )

        legendoptics.tetratex.pyg4_tetratex_attach_reflectivity(
            self._wlsr_tpb_to_tetratex,
            self.g4_registry,
        )

        return self._wlsr_tpb_to_tetratex

    @property
    def to_sipm_silicon(self) -> g4.Material:
        """Reflective surface for KETEK SiPM."""
        if hasattr(self, "_to_sipm_silicon"):
            return self._to_sipm_silicon

        self._to_sipm_silicon = g4.solid.OpticalSurface(
            "surface_to_sipm_silicon",
            finish="ground",
            model=self._model,
            surf_type="dielectric_metal",
            value=0.9,
            registry=self.g4_registry,
        )

        legendoptics.silicon.pyg4_silicon_attach_complex_rindex(
            self._to_sipm_silicon,
            self.g4_registry,
        )

        # add custom efficiency for the KETEK SiPMs. This is not part of legendoptics.
        λ = np.array([100, 280, 310, 350, 400, 435, 505, 525, 595, 670][::-1]) * u.nm
        eff = np.array([0.0, 0.19, 0.30, 0.32, 0.33, 0.32, 0.27, 0.19, 0.12, 0.07][::-1])
        with u.context("sp"):
            self._to_sipm_silicon.addVecPropertyPint("EFFICIENCY", λ.to("eV"), eff)

        return self._to_sipm_silicon
