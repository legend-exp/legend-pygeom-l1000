"""Subpackage to provide all implemented materials and their (optical) material properties."""

from __future__ import annotations

import pyg4ometry.geant4 as g4
from pygeomtools.materials import LegendMaterialRegistry

from .surfaces import OpticalSurfaceRegistry


class OpticalMaterialRegistry(LegendMaterialRegistry):
    def __init__(self, g4_registry: g4.Registry, enable_optical: bool | list[str] = True):
        if isinstance(enable_optical, bool):
            super().__init__(g4_registry=g4_registry, enable_optical=enable_optical)
        else:
            enable_optical = LegendMaterialRegistry(g4.Registry(), enable_optical).enable_optical
            super().__init__(g4_registry=g4_registry, enable_optical=False)
            self.enable_optical = enable_optical

        self.surfaces = OpticalSurfaceRegistry(g4_registry)
