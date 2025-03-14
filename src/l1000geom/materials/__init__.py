"""Subpackage to provide all implemented materials and their (optical) material properties."""

from __future__ import annotations

import legendoptics.fibers
import legendoptics.lar
import legendoptics.nylon
import legendoptics.pen
import legendoptics.tpb
import numpy as np
import pint
import pyg4ometry.geant4 as g4

from .surfaces import OpticalSurfaceRegistry


class OpticalMaterialRegistry:
    def __init__(self, g4_registry: g4.Registry):
        self.g4_registry = g4_registry
        self.lar_temperature = 88.8

        self._elements = {}
        self._elements_cb = {}
        self._define_elements()

        self.surfaces = OpticalSurfaceRegistry(g4_registry)

    def get_element(self, symbol: str) -> g4.Element:
        if (symbol in self._elements_cb) and (symbol not in self._elements):
            self._elements[symbol] = (self._elements_cb[symbol])()
        return self._elements[symbol]

    def _add_element(self, name: str, symbol: str, Z: int, A: float) -> None:
        """Lazily define an element on the current registry."""
        assert symbol not in self._elements_cb
        self._elements_cb[symbol] = lambda: g4.ElementSimple(
            name=name, symbol=symbol, Z=Z, A=A, registry=self.g4_registry
        )

    def _define_elements(self) -> None:
        """Lazily define all used elements."""
        self._add_element(name="Hydrogen", symbol="H", Z=1, A=1.00794)
        self._add_element(name="Carbon", symbol="C", Z=6, A=12.011)
        self._add_element(name="Nitrogen", symbol="N", Z=7, A=14.01)
        self._add_element(name="Oxygen", symbol="O", Z=8, A=16.00)
        self._add_element(name="Fluorine", symbol="F", Z=9, A=19.00)
        self._add_element(name="Silicon", symbol="Si", Z=14, A=28.09)
        self._add_element(name="argon", symbol="Ar", Z=18, A=39.95)
        self._add_element(name="Chromium", symbol="Cr", Z=24, A=51.9961)
        self._add_element(name="Manganese", symbol="Mn", Z=25, A=54.93805)
        self._add_element(name="Iron", symbol="Fe", Z=26, A=55.845)
        self._add_element(name="Indium", symbol="In", Z=49, A=114.82)
        self._add_element(name="Cobalt", symbol="Co", Z=27, A=58.9332)
        self._add_element(name="Nickel", symbol="Ni", Z=28, A=58.6934)
        self._add_element(name="Copper", symbol="Cu", Z=29, A=63.55)
        self._add_element(name="Tantalum", symbol="Ta", Z=73, A=180.94)
        self._add_element(name="Gold", symbol="Au", Z=79, A=196.967)

    @property
    def liquidargon(self) -> g4.Material:
        """LEGEND liquid argon."""
        if hasattr(self, "_liquidargon"):
            return self._liquidargon

        self._liquidargon = g4.Material(
            name="LiquidArgon",
            density=1.390,  # g/cm3
            number_of_components=1,
            state="liquid",
            temperature=self.lar_temperature,  # K
            pressure=1.0 * 1e5,  # pascal
            registry=self.g4_registry,
        )
        self._liquidargon.add_element_natoms(self.get_element("Ar"), natoms=1)

        u = pint.get_application_registry().get()
        legendoptics.lar.pyg4_lar_attach_rindex(
            self._liquidargon,
            self.g4_registry,
        )
        legendoptics.lar.pyg4_lar_attach_attenuation(
            self._liquidargon,
            self.g4_registry,
            self.lar_temperature * u.K,
        )
        legendoptics.lar.pyg4_lar_attach_scintillation(
            self._liquidargon,
            self.g4_registry,
            triplet_lifetime_method="legend200-llama",
        )

        return self._liquidargon

    @property
    def metal_steel(self) -> g4.Material:
        """Stainless steel of the GERDA cryostat."""
        if hasattr(self, "_metal_steel"):
            return self._metal_steel

        self._metal_steel = g4.Material(
            name="metal_steel",
            density=7.9,
            number_of_components=5,
            registry=self.g4_registry,
        )
        self._metal_steel.add_element_massfraction(self.get_element("Si"), massfraction=0.01)
        self._metal_steel.add_element_massfraction(self.get_element("Cr"), massfraction=0.20)
        self._metal_steel.add_element_massfraction(self.get_element("Mn"), massfraction=0.02)
        self._metal_steel.add_element_massfraction(self.get_element("Fe"), massfraction=0.67)
        self._metal_steel.add_element_massfraction(self.get_element("Ni"), massfraction=0.10)

        return self._metal_steel

    @property
    def vacuum(self) -> g4.Material:
        """Vacuum-equivalent material - extremely diffuse hydrogen."""
        if hasattr(self, "_vacuum"):
            return self._vacuum

        self._vacuum = g4.Material(
            name="vacuum",
            density=0.00000000001,
            number_of_components=1,
            registry=self.g4_registry,
        )
        self._vacuum.add_element_massfraction(self.get_element("H"), massfraction=1.)

        return self._vacuum

    @property
    def metal_silicon(self) -> g4.Material:
        """Silicon."""
        if hasattr(self, "_metal_silicon"):
            return self._metal_silicon

        self._metal_silicon = g4.Material(
            name="metal_silicon",
            density=2.330,
            number_of_components=1,
            registry=self.g4_registry,
        )
        self._metal_silicon.add_element_natoms(self.get_element("Si"), natoms=1)

        return self._metal_silicon

    @property
    def metal_tantalum(self) -> g4.Material:
        """Tantalum."""
        if hasattr(self, "_metal_tantalum"):
            return self._metal_tantalum

        self._metal_tantalum = g4.Material(
            name="metal_tantalum",
            density=16.69,
            number_of_components=1,
            registry=self.g4_registry,
        )
        self._metal_tantalum.add_element_natoms(self.get_element("Ta"), natoms=1)

        return self._metal_tantalum

    @property
    def metal_copper(self) -> g4.Material:
        """Copper structures.

        .. warning:: For full optics support, a reflective surface is needed, see
            :py:func:`surfaces.OpticalSurfaceRegistry.to_copper`.
        """
        if hasattr(self, "_metal_copper"):
            return self._metal_copper

        self._metal_copper = g4.Material(
            name="metal_copper",
            density=8.960,
            number_of_components=1,
            registry=self.g4_registry,
        )
        self._metal_copper.add_element_natoms(self.get_element("Cu"), natoms=1)

        return self._metal_copper

    @property
    def metal_caps_gold(self) -> g4.Material:
        """Gold for calibration source.

        .. note:: modified density in order to have the equivalent of two 2x2cm gold
            foils, with 20 um thickness.
        """
        if hasattr(self, "_metal_caps_gold"):
            return self._metal_caps_gold

        # quoting https://doi.org/10.1088/1748-0221/18/02/P02001:
        # After the deposition, the external part of the foil with no 228Th
        # activity was cut off, and the foil rolled

        volume_of_foil = np.pi * (1 / 8 * 2.54) ** 2 * 50e-4  # 1/4” diameter, 50 um thickness
        volume_of_inner = np.pi * 0.2**2 * 0.4  # 2 cm radius, 4 cm height
        self._metal_caps_gold = g4.Material(
            name="metal_caps_gold",
            density=19.3 * volume_of_foil / volume_of_inner,
            number_of_components=1,
            registry=self.g4_registry,
        )
        self._metal_caps_gold.add_element_natoms(self.get_element("Au"), natoms=1)

        return self._metal_caps_gold

    @property
    def peek(self) -> g4.Material:
        """PEEK for the SIS absorber holder."""
        if hasattr(self, "_peek"):
            return self._peek

        self._peek = g4.Material(
            name="peek", density=1.320, number_of_components=3, registry=self.g4_registry
        )
        self._peek.add_element_natoms(self.get_element("C"), natoms=19)
        self._peek.add_element_natoms(self.get_element("H"), natoms=12)  # TODO: MaGe uses C19H1203??
        self._peek.add_element_natoms(self.get_element("O"), natoms=3)

        return self._peek

    @property
    def pmma(self) -> g4.Material:
        """PMMA for the inner fiber cladding layer."""
        if hasattr(self, "_pmma"):
            return self._pmma

        self._pmma = g4.Material(name="pmma", density=1.2, number_of_components=3, registry=self.g4_registry)
        self._pmma.add_element_natoms(self.get_element("H"), natoms=8)
        self._pmma.add_element_natoms(self.get_element("C"), natoms=5)
        self._pmma.add_element_natoms(self.get_element("O"), natoms=2)

        legendoptics.fibers.pyg4_fiber_cladding1_attach_rindex(
            self._pmma,
            self.g4_registry,
        )

        return self._pmma

    @property
    def pmma_out(self) -> g4.Material:
        """PMMA for the outer fiber cladding layer."""
        if hasattr(self, "_pmma_out"):
            return self._pmma_out

        self._pmma_out = g4.Material(
            name="pmma_cl2",
            density=1.2,
            number_of_components=3,
            registry=self.g4_registry,
        )
        self._pmma_out.add_element_natoms(self.get_element("H"), natoms=8)
        self._pmma_out.add_element_natoms(self.get_element("C"), natoms=5)
        self._pmma_out.add_element_natoms(self.get_element("O"), natoms=2)

        legendoptics.fibers.pyg4_fiber_cladding2_attach_rindex(
            self._pmma_out,
            self.g4_registry,
        )

        return self._pmma_out

    @property
    def ps_fibers(self) -> g4.Material:
        """Polystyrene for the fiber core."""
        if hasattr(self, "_ps_fibers"):
            return self._ps_fibers

        self._ps_fibers = g4.Material(
            name="ps_fibers",
            density=1.05,
            number_of_components=2,
            registry=self.g4_registry,
        )
        self._ps_fibers.add_element_natoms(self.get_element("H"), natoms=8)
        self._ps_fibers.add_element_natoms(self.get_element("C"), natoms=8)

        legendoptics.fibers.pyg4_fiber_core_attach_rindex(
            self._ps_fibers,
            self.g4_registry,
        )
        legendoptics.fibers.pyg4_fiber_core_attach_absorption(
            self._ps_fibers,
            self.g4_registry,
        )
        legendoptics.fibers.pyg4_fiber_core_attach_wls(
            self._ps_fibers,
            self.g4_registry,
        )

        return self._ps_fibers

    def _tpb(self, name: str, **wls_opts) -> g4.Material:
        t = g4.Material(
            name=name,
            density=1.08,
            number_of_components=2,
            state="solid",
            registry=self.g4_registry,
        )
        t.add_element_natoms(self.get_element("H"), natoms=22)
        t.add_element_natoms(self.get_element("C"), natoms=28)

        legendoptics.tpb.pyg4_tpb_attach_rindex(t, self.g4_registry)
        legendoptics.tpb.pyg4_tpb_attach_wls(t, self.g4_registry, **wls_opts)

        return t

    @property
    def tpb_on_fibers(self) -> g4.Material:
        """Tetraphenyl-butadiene wavelength shifter (evaporated on fibers)."""
        if hasattr(self, "_tpb_on_fibers"):
            return self._tpb_on_fibers

        self._tpb_on_fibers = self._tpb("tpb_on_fibers")

        return self._tpb_on_fibers

    @property
    def tpb_on_tetratex(self) -> g4.Material:
        """Tetraphenyl-butadiene wavelength shifter (evaporated on Tetratex)."""
        if hasattr(self, "_tpb_on_tetratex"):
            return self._tpb_on_tetratex

        self._tpb_on_tetratex = self._tpb("tpb_on_tetratex")

        return self._tpb_on_tetratex

    @property
    def tpb_on_nylon(self) -> g4.Material:
        """Tetraphenyl-butadiene wavelength shifter (in nylon matrix)."""
        if hasattr(self, "_tpb_on_nylon"):
            return self._tpb_on_nylon

        # as a base, use the normal TPB properties.
        self._tpb_on_nylon = self._tpb(
            "tpb_on_nylon",
            # For 30% TPB 70% PS the WLS light yield is reduced by 30% [Alexey]
            quantum_efficiency=0.7 * legendoptics.tpb.tpb_quantum_efficiency(),
            # the emission spectrum differs significantly.
            emission_spectrum="polystyrene_matrix",
        )

        # add absorption length from nylon.
        legendoptics.nylon.pyg4_nylon_attach_absorption(self._tpb_on_nylon, self.g4_registry)

        return self._tpb_on_nylon

    @property
    def tetratex(self) -> g4.Material:
        """Tetratex diffuse reflector.

        .. warning:: For full optics support, a reflective surface is needed, see
            :py:func:`surfaces.OpticalSurfaceRegistry.wlsr_tpb_to_tetratex`.
        """
        if hasattr(self, "_tetratex"):
            return self._tetratex

        self._tetratex = g4.Material(
            name="tetratex",
            density=0.35,
            number_of_components=2,
            registry=self.g4_registry,
        )
        self._tetratex.add_element_massfraction(self.get_element("F"), massfraction=0.76)
        self._tetratex.add_element_massfraction(self.get_element("C"), massfraction=0.24)

        return self._tetratex

    @property
    def nylon(self) -> g4.Material:
        """Nylon (from Borexino)."""
        if hasattr(self, "_nylon"):
            return self._nylon

        self._nylon = g4.Material(
            name="nylon",
            density=1.15,
            number_of_components=4,
            registry=self.g4_registry,
        )
        self._nylon.add_element_natoms(self.get_element("H"), natoms=2)
        self._nylon.add_element_natoms(self.get_element("N"), natoms=2)
        self._nylon.add_element_natoms(self.get_element("O"), natoms=3)
        self._nylon.add_element_natoms(self.get_element("C"), natoms=13)

        legendoptics.nylon.pyg4_nylon_attach_rindex(self._nylon, self.g4_registry)
        legendoptics.nylon.pyg4_nylon_attach_absorption(self._nylon, self.g4_registry)

        return self._nylon

    @property
    def pen(self) -> g4.Material:
        """PEN wavelength-shifter and scintillator."""
        if hasattr(self, "_pen"):
            return self._pen

        self._pen = g4.Material(
            name="pen",
            density=1.3,
            number_of_components=3,
            registry=self.g4_registry,
        )
        self._pen.add_element_natoms(self.get_element("C"), natoms=14)
        self._pen.add_element_natoms(self.get_element("H"), natoms=10)
        self._pen.add_element_natoms(self.get_element("O"), natoms=4)

        legendoptics.pen.pyg4_pen_attach_rindex(self._pen, self.g4_registry)
        legendoptics.pen.pyg4_pen_attach_attenuation(self._pen, self.g4_registry)
        legendoptics.pen.pyg4_pen_attach_wls(self._pen, self.g4_registry)
        legendoptics.pen.pyg4_pen_attach_scintillation(self._pen, self.g4_registry)

        return self._pen

    @property
    def ultem(self) -> g4.Material:
        """Ultem for the cable insulator."""
        if hasattr(self, "_ultem"):
            return self._ultem

        self._ultem = g4.Material(
            name="ultem",
            density=1.27,
            number_of_components=4,
            registry=self.g4_registry,
        )
        self._ultem.add_element_natoms(self.get_element("C"), natoms=37)
        self._ultem.add_element_natoms(self.get_element("H"), natoms=24)
        self._ultem.add_element_natoms(self.get_element("O"), natoms=6)
        self._ultem.add_element_natoms(self.get_element("N"), natoms=2)

        return self._ultem

    @property
    def silica(self) -> g4.Material:
        """Silica for the fiber core."""
        if hasattr(self, "_silica"):
            return self._silica

        self._silica = g4.Material(
            name="silica",
            density=2.2,
            number_of_components=2,
            registry=self.g4_registry,
        )
        self._silica.add_element_natoms(self.get_element("Si"), natoms=1)
        self._silica.add_element_natoms(self.get_element("O"), natoms=2)

        return self._silica

    @property
    def teflon(self) -> g4.Material:
        """Teflon for the click and du holder."""
        if hasattr(self, "_teflon"):
            return self._teflon

        self._teflon = g4.Material(
            name="teflon",
            density=2.2,
            number_of_components=2,
            registry=self.g4_registry,
        )
        self._teflon.add_element_natoms(self.get_element("F"), natoms=4)
        self._teflon.add_element_natoms(self.get_element("C"), natoms=2)

        return self._teflon
