from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from pyg4ometry import geant4 as g4
from pygeomtools import RemageDetectorInfo

from . import core, hpge_strings, materials


def place_fiber_modules(b: core.InstrumentationData) -> None:
    """Construct LEGEND-1000 HPGe strings.

    detail options:
    ---------------
    "segmented" or "detailed"
        Switch between an implementation of single fibers (“detailed”) or
        slabs of fiber material (“segmented”).
    """
    if "fiber_curtain" not in b.detail:
        msg = "No 'fiber_curtain' detail specified in the special metadata."
        raise ValueError(msg)

    if b.detail["fiber_curtain"] == "omit":
        return

    use_detailed_fiber_model = b.detail["fiber_curtain"] == "detailed"
    fiber_metadata = b.special_metadata["fibers"]

    # Unroll the provided metadata into a structure better suited for the next steps.
    # The geometry here is based on physical modules and not on channels.
    modules = {}
    ch_map = b.channelmap.map("system", unique=False).spms
    for ch in ch_map.values():
        mod = modules.get(ch.location.fiber)

        if mod is None:
            # initialize a new module object if we don't have one yet.
            mod = FiberModuleData(
                name=ch.location.fiber,
                barrel=fiber_metadata[ch.location.fiber].type,
                tpb_thickness=fiber_metadata[ch.location.fiber].geometry.tpb.thickness_in_nm,
                x_position_mm=fiber_metadata[ch.location.fiber].location.x,
                y_position_mm=fiber_metadata[ch.location.fiber].location.y,
                module_num=fiber_metadata[ch.location.fiber].location.module_num,
                string_id=ch.location.barrel,
            )
            modules[ch.location.fiber] = mod

        assert getattr(mod, f"channel_{ch.location.position}_name") is None
        setattr(mod, f"channel_{ch.location.position}_name", ch.name)
        setattr(mod, f"channel_{ch.location.position}_rawid", ch.daq.rawid)

    factory = ModuleFactorySingleFibers if use_detailed_fiber_model else ModuleFactorySegment

    # note: actually the radius is only 150mm and another short straight segment of 60mm is following after
    # the bend. to simplify things here, those two are combined to one bent shape, to have at least the same
    # covered solid angle.
    # we do not add the full straight part here (this would make the radius to large), but just a tiny delta
    # that makes the bottom of the OB cover the whole area between the straight OB and IB fibers.

    radius_in_mm = 52.75  # 70
    fiber_length_mm = 1349  # 1622.3  # 1200.2 # 1000.2 + 200

    z_displacement_fiber_assembly = (
        # avoid the overlap of the top SiPMs with the top plate.
        hpge_strings.z_pos_dict["sipm_upper_holding_structure_upper_end"]
        # - fiber_length_mm   # from CAD model.
    )

    single_string_factory = factory(
        radius_mm=radius_in_mm,
        fiber_length_mm=fiber_length_mm,
        fiber_count_per_module=32,
        bend_radius_mm=None,
        number_of_modules=len(
            np.unique([fiber_metadata[ch.location.fiber].location.module_num for ch in ch_map.values()])
        ),
        z_displacement_mm=z_displacement_fiber_assembly,
        registry=b.registry,
        materials=b.materials,
    )

    for mod in modules.values():
        single_string_factory.create_module(mod, b)


@dataclass
class FiberModuleData:
    barrel: str
    name: str
    tpb_thickness: float
    channel_top_name: str | None = None
    channel_bottom_name: str | None = None
    channel_top_rawid: str | None = None
    channel_bottom_rawid: str | None = None
    x_position_mm: float = 0
    y_position_mm: float = 0
    module_num: int = 0
    string_id: int = 0


class ModuleFactoryBase(ABC):
    FIBER_DIM = 1  # 1.5  # mm
    FIBER_THICKNESS_CL1 = 0.04 * FIBER_DIM  # (BCF-91A document)
    FIBER_THICKNESS_CL2 = 0.02 * FIBER_DIM  # (BCF-91A document)

    # The "SiPM" is only a dummy implementation here, the fibers are not bent to the real geometry of 3x3
    # fibers coupled to one physical SiPM!
    SIPM_HEIGHT = 1  # mm, dummy
    # There is a LAr gap between the fiber end and SiPM:
    SIPM_GAP = 0.05  # mm
    # Because of this gap, we cannot use surfaces between fibers and the "SiPM". To stop stray light from
    # entering the "SiPM" from the other sides, we add an outer envelope that blocks light. On each outer
    # side of the SiPM volume, an additional solid of size "outer extra" is added:
    SIPM_OUTER_EXTRA = 0.2  # mm
    # To also stop stray light from directions more close to the fibers, the envelope extends a bit more
    # along the fibers:
    SIPM_OVERLAP = 0.3  # mm
    SIPM_GAP_SIDE = 0.02  # mm, for fitting problems with round "SiPMs" and square fibers.

    ANGLE_SAFETY = 1e-9  # rad

    ANGLE_PER_HOLDING_STRUCTURE = np.deg2rad(12)  # rad
    ANGLE_BETWEEN_MODULE_OTHERWISE = np.deg2rad(1)  # rad

    def __init__(
        self,
        radius_mm: float,
        fiber_length_mm: float,
        fiber_count_per_module: int,
        bend_radius_mm: float | None,
        number_of_modules: int,
        z_displacement_mm: float,
        materials: materials.OpticalMaterialRegistry,
        registry: g4.Registry,
    ):
        """
        Create a fiber module factory.

        Parameters
        ----------
        radius_mm
            radius of the fiber barrel
        fiber_length_mm
            length of the straight section of this fiber module
        fiber_count_per_module
            number of single fibers per module
        bend_radius_mm
            radius of the bottom bend, or None if the fibers are not bent at the bottom end.
        number_of_modules
            number of modules that cover the full circle
        z_displacement_mm
            displacement of the top of the fiber barrel, relative to the global zero point.
        """

        self.radius = radius_mm + 1e-9  # place fibers fully inside the specified radius
        self.fiber_length = fiber_length_mm
        self.fiber_count_per_module = fiber_count_per_module
        self.bend_radius_mm = bend_radius_mm
        self.number_of_modules = number_of_modules
        self.z_displacement = z_displacement_mm
        self.materials = materials
        self.registry = registry

        if self.number_of_modules % 3 != 0:
            msg = "number_of_modules must be a multiple of 3"
            raise ValueError(msg)

        self.angle_per_module = (
            2 * math.pi
            - 3 * self.ANGLE_PER_HOLDING_STRUCTURE
            - (self.number_of_modules - 3) * self.ANGLE_BETWEEN_MODULE_OTHERWISE
        ) / self.number_of_modules

    def _cached_sipm_volumes(self) -> None:
        """Creates (dummy) SiPM volumes for use at the top/bottom of straight fiber sections."""
        v_suffix = f"_r{self.radius}_nmod{self.number_of_modules}"
        v_name = f"sipm{v_suffix}"
        if v_name in self.registry.solidDict:
            return

        sipm_dim = self.FIBER_DIM + self.SIPM_GAP_SIDE  # GAP_SIDE to fit round->square
        fiber_segment = self.angle_per_module

        sipm = g4.solid.Tubs(
            v_name,
            self.radius - sipm_dim / 2,
            self.radius + sipm_dim / 2,
            self.SIPM_HEIGHT,
            self.ANGLE_SAFETY,
            fiber_segment - self.ANGLE_SAFETY,
            self.registry,
            "mm",
        )
        self.sipm_lv = g4.LogicalVolume(sipm, self.materials.metal_silicon, v_name, self.registry)

        sipm_outer1 = g4.solid.Tubs(
            f"sipm_outer1{v_suffix}",
            self.radius - sipm_dim / 2 - self.SIPM_OUTER_EXTRA,
            self.radius + sipm_dim / 2 + self.SIPM_OUTER_EXTRA,
            self.SIPM_HEIGHT + self.SIPM_OUTER_EXTRA + self.SIPM_OVERLAP,
            self.ANGLE_SAFETY,
            fiber_segment - self.ANGLE_SAFETY,
            self.registry,
            "mm",
        )
        sipm_outer2 = g4.solid.Tubs(
            f"sipm_outer2{v_suffix}",
            self.radius - sipm_dim / 2 - 1e-9,
            self.radius + sipm_dim / 2 + 1e-9,
            self.SIPM_HEIGHT + 2 * self.SIPM_GAP + self.SIPM_OVERLAP,
            self.ANGLE_SAFETY,
            fiber_segment - self.ANGLE_SAFETY,
            self.registry,
            "mm",
        )
        sipm_outer_top = g4.solid.Subtraction(
            f"sipm_outer_top{v_suffix}",
            sipm_outer1,
            sipm_outer2,
            [[0, 0, 0], [0, 0, -self.SIPM_OUTER_EXTRA / 2]],
            self.registry,
        )
        sipm_outer_bottom = g4.solid.Subtraction(
            f"sipm_outer_bottom{v_suffix}",
            sipm_outer1,
            sipm_outer2,
            [[0, 0, 0], [0, 0, +self.SIPM_OUTER_EXTRA / 2]],
            self.registry,
        )
        self.sipm_outer_top_lv = g4.LogicalVolume(
            sipm_outer_top,
            self.materials.metal_copper,
            f"sipm_outer_top{v_suffix}",
            self.registry,
        )
        self.sipm_outer_bottom_lv = g4.LogicalVolume(
            sipm_outer_bottom,
            self.materials.metal_copper,
            f"sipm_outer_bottom{v_suffix}",
            self.registry,
        )

    def start_angle(self, module_num: int) -> float:
        start_angle = self.ANGLE_PER_HOLDING_STRUCTURE / 2.0
        for i in range(module_num):
            start_angle += self.angle_per_module
            if (i + 1) % (self.number_of_modules // 3) == 0 and i != 0:
                start_angle += self.ANGLE_PER_HOLDING_STRUCTURE
            else:
                start_angle += self.ANGLE_BETWEEN_MODULE_OTHERWISE

        return start_angle

    @abstractmethod
    def create_module(
        self,
        mod: FiberModuleData,
        b: core.InstrumentationData,
        # mother_lv: g4.LogicalVolume,
        # mother_pv: g4.PhysicalVolume,
        x_position_mm: float,
        y_position_mm: float,
        module_num: int,
    ) -> None:
        raise NotImplementedError()

    def _create_sipm(
        self,
        mod: FiberModuleData,
        b: core.InstrumentationData,
        module_num: int,
        fibers: list[g4.PhysicalVolume],
        is_top: bool,
        mother_lv: g4.LogicalVolume,
        mother_pv: g4.PhysicalVolume,
        sipm_name: str,
        sipm_detector_id: int,
        z_displacement_straight: float,
        x_position_mm: float,
        y_position_mm: float,
    ) -> None:
        """Creates a (dummy) SiPM physical volume for use at the top/bottom of straight fiber sections."""
        z = +self.fiber_length / 2 + self.SIPM_HEIGHT / 2 + self.SIPM_GAP  # add small gap
        z_outer = (
            z + self.SIPM_OUTER_EXTRA / 2 - self.SIPM_OVERLAP / 2 - self.SIPM_GAP + 1e-9
            if is_top
            else -z - self.SIPM_OUTER_EXTRA / 2 + self.SIPM_OVERLAP / 2 + self.SIPM_GAP - 1e-9
        )
        z = z if is_top else -z
        z += z_displacement_straight
        z_outer += z_displacement_straight

        string_rot_output = hpge_strings.calculate_string_rotation(str(mod.string_id), b)

        start_angle = self.start_angle(module_num % self.number_of_modules) + string_rot_output["string_rot"]

        sipm_pv = g4.PhysicalVolume(
            [0, 0, -start_angle],
            [x_position_mm, y_position_mm, z],
            self.sipm_lv,
            sipm_name,
            mother_lv,
            self.registry,
        )
        sipm_pv.pygeom_active_detector = RemageDetectorInfo("optical", sipm_detector_id)
        # Add border surface to mother volume.
        g4.BorderSurface(
            f"bsurface_lar_{sipm_name}",
            mother_pv,
            sipm_pv,
            self.materials.surfaces.to_sipm_silicon,
            self.registry,
        )

        g4.PhysicalVolume(
            [0, 0, -start_angle],
            [x_position_mm, y_position_mm, z_outer],
            self.sipm_outer_top_lv if is_top else self.sipm_outer_bottom_lv,
            f"{sipm_name}_wrap",
            mother_lv,
            self.registry,
        )

    def _add_tpb_surfaces(
        self,
        fiber_pvs: list[g4.PhysicalVolume],
        mother_pv: g4.LogicalVolume,
    ):
        # between LAr and PEN we need a surface in both directions.
        for tpb_pv in fiber_pvs:
            g4.BorderSurface(
                "bsurface_lar_tpb_" + tpb_pv.name,
                mother_pv,
                tpb_pv,
                self.materials.surfaces.lar_to_tpb,
                self.registry,
            )
            g4.BorderSurface(
                "bsurface_tpb_lar_" + tpb_pv.name,
                tpb_pv,
                mother_pv,
                self.materials.surfaces.lar_to_tpb,
                self.registry,
            )


class ModuleFactorySingleFibers(ModuleFactoryBase):
    # for bent detailed fibers, the fibers would overlap a lot near the bottom SiPMs. To avoid
    # this, use a staggered design of the fibers.
    ALLOWED_DELTA_LENGTHS = (-6.96, -5.22, -3.48, -1.74, 0, 1.74, 3.48, 5.22, 6.96)

    def _cached_sipm_volumes_bend(self) -> None:
        """Creates (dummy) SiPM volumes for use at the bottom of bent fiber sections."""
        v_suffix = "_bend"  # this dummy SiPM is for one single fiber, so we do not need any attributes here.
        v_name = f"sipm{v_suffix}"
        if v_name in self.registry.solidDict:
            return

        sipm_dim = self.FIBER_DIM + self.SIPM_GAP_SIDE  # GAP_SIDE to fit round->square

        self.sipm_bend = g4.solid.Box(
            v_name,
            self.SIPM_HEIGHT,
            sipm_dim,
            sipm_dim,
            self.registry,
            "mm",
        )
        self.sipm_lv_bend = g4.LogicalVolume(
            self.sipm_bend, self.materials.metal_silicon, v_name, self.registry
        )

        sipm_outer1 = g4.solid.Box(
            f"sipm_outer1{v_suffix}",
            self.SIPM_HEIGHT + self.SIPM_OUTER_EXTRA + self.SIPM_OVERLAP,
            sipm_dim + 2 * self.SIPM_OUTER_EXTRA,
            sipm_dim + 2 * self.SIPM_OUTER_EXTRA,
            self.registry,
            "mm",
        )
        sipm_outer2 = g4.solid.Box(
            f"sipm_outer2{v_suffix}",
            self.SIPM_HEIGHT + 2 * self.SIPM_GAP + self.SIPM_OVERLAP,
            sipm_dim + 1e-8,
            sipm_dim + 1e-8,
            self.registry,
            "mm",
        )
        sipm_outer_bottom = g4.solid.Subtraction(
            f"sipm_outer_bottom{v_suffix}",
            sipm_outer1,
            sipm_outer2,
            [[0, 0, 0], [+self.SIPM_OUTER_EXTRA / 2, 0, 0]],
            self.registry,
        )
        self.sipm_outer_bottom_lv_bend = g4.LogicalVolume(
            sipm_outer_bottom,
            self.materials.metal_copper,
            f"sipm_outer_bottom{v_suffix}",
            self.registry,
        )

    def _cached_fiber_volumes(self) -> None:
        """Create solids, logical and physical volumes for the fibers, as specified by the parameters of this instance."""
        v_suffix = f"_l{self.fiber_length}_b{self.bend_radius_mm}"
        if f"fiber_cl2{v_suffix}" in self.registry.solidDict:
            return

        fibers_to_gen = [(v_suffix, self.fiber_length)]
        if self.bend_radius_mm is not None:
            for delta_length in self.ALLOWED_DELTA_LENGTHS:
                if delta_length == 0:
                    continue
                fibers_to_gen += [
                    (
                        f"_l{self.fiber_length + delta_length}_b{self.bend_radius_mm}",
                        self.fiber_length + delta_length,
                    )
                ]

        # create solids
        fiber_cl2 = {}
        fiber_cl1 = {}
        fiber_core = {}
        dim_cl1 = self.FIBER_DIM - 2 * self.FIBER_THICKNESS_CL1
        dim_core = self.FIBER_DIM - 2 * (self.FIBER_THICKNESS_CL1 + self.FIBER_THICKNESS_CL2)
        for [fiber_name, fiber_length] in fibers_to_gen:
            fiber_cl2[fiber_length] = g4.solid.Box(
                f"fiber_cl2{fiber_name}",
                self.FIBER_DIM,
                self.FIBER_DIM,
                fiber_length,
                self.registry,
                "mm",
            )
            fiber_cl1[fiber_length] = g4.solid.Box(
                f"fiber_cl1{fiber_name}",
                dim_cl1,
                dim_cl1,
                fiber_length,
                self.registry,
                "mm",
            )
            fiber_core[fiber_length] = g4.solid.Box(
                f"fiber_core{fiber_name}",
                dim_core,
                dim_core,
                fiber_length,
                self.registry,
                "mm",
            )
        if self.bend_radius_mm is not None:
            fiber_cl2_bend = g4.solid.Tubs(
                f"fiber_cl2_bend{v_suffix}",
                self.bend_radius_mm - self.FIBER_DIM / 2,
                self.bend_radius_mm + self.FIBER_DIM / 2,
                self.FIBER_DIM,
                0,
                math.pi / 2,
                self.registry,
                "mm",
            )
            fiber_cl1_bend = g4.solid.Tubs(
                f"fiber_cl1_bend{v_suffix}",
                self.bend_radius_mm - dim_cl1 / 2,
                self.bend_radius_mm + dim_cl1 / 2,
                dim_cl1,
                0,
                math.pi / 2,
                self.registry,
                "mm",
            )
            fiber_core_bend = g4.solid.Tubs(
                f"fiber_core_bend{v_suffix}",
                self.bend_radius_mm - dim_core / 2,
                self.bend_radius_mm + dim_core / 2,
                dim_core,
                0,
                math.pi / 2,
                self.registry,
                "mm",
            )

        self.fiber_cl2_lv = {}
        fiber_cl1_lv = {}
        fiber_core_lv = {}
        for [fiber_name, fiber_length] in fibers_to_gen:
            self.fiber_cl2_lv[fiber_length] = g4.LogicalVolume(
                fiber_cl2[fiber_length], self.materials.pmma_out, f"fiber_cl2{fiber_name}", self.registry
            )
            self.fiber_cl2_lv[fiber_length].pygeom_color_rgba = False
            fiber_cl1_lv[fiber_length] = g4.LogicalVolume(
                fiber_cl1[fiber_length], self.materials.pmma, f"fiber_cl1{fiber_name}", self.registry
            )
            fiber_cl1_lv[fiber_length].pygeom_color_rgba = False
            fiber_core_lv[fiber_length] = g4.LogicalVolume(
                fiber_core[fiber_length], self.materials.ps_fibers, f"fiber_core{fiber_name}", self.registry
            )
            fiber_core_lv[fiber_length].pygeom_color_rgba = False
        if self.bend_radius_mm is not None:
            self.fiber_cl2_bend_lv = g4.LogicalVolume(
                fiber_cl2_bend, self.materials.pmma_out, f"fiber_cl2_bend{v_suffix}", self.registry
            )
            self.fiber_cl2_bend_lv.pygeom_color_rgba = False
            fiber_cl1_bend_lv = g4.LogicalVolume(
                fiber_cl1_bend, self.materials.pmma, f"fiber_cl1_bend{v_suffix}", self.registry
            )
            fiber_cl1_bend_lv.pygeom_color_rgba = False
            fiber_core_bend_lv = g4.LogicalVolume(
                fiber_core_bend, self.materials.ps_fibers, f"fiber_core_bend{v_suffix}", self.registry
            )
            fiber_core_bend_lv.pygeom_color_rgba = False

        for [fiber_name, fiber_length] in fibers_to_gen:
            g4.PhysicalVolume(
                [0, 0, 0],
                [0, 0, 0],
                fiber_cl1_lv[fiber_length],
                f"fiber_cl1{fiber_name}",
                self.fiber_cl2_lv[fiber_length],
                self.registry,
            )
            g4.PhysicalVolume(
                [0, 0, 0],
                [0, 0, 0],
                fiber_core_lv[fiber_length],
                f"fiber_core{fiber_name}",
                fiber_cl1_lv[fiber_length],
                self.registry,
            )
        if self.bend_radius_mm is not None:
            g4.PhysicalVolume(
                [0, 0, 0],
                [0, 0, 0],
                fiber_cl1_bend_lv,
                f"fiber_cl1_bend{v_suffix}",
                self.fiber_cl2_bend_lv,
                self.registry,
            )
            g4.PhysicalVolume(
                [0, 0, 0],
                [0, 0, 0],
                fiber_core_bend_lv,
                f"fiber_core_bend{v_suffix}",
                fiber_cl1_bend_lv,
                self.registry,
            )

    def _cached_tpb_coating_volume(
        self, tpb_thickness_nm: float, bend: bool = False, delta_length: int = 0
    ) -> g4.LogicalVolume:
        """Create and cache a TPB coating layer of the specified thickness.

        The TPB-Layer is dependent on the module (i.e. the applied thickness varies slightly),
        so we cannot cache it globally on this instance.
        """
        if delta_length != 0 and bend:
            msg = "creating a bent volume with delta_length!=0 is not possible"
            raise ValueError(msg)
        if delta_length not in self.ALLOWED_DELTA_LENGTHS:
            msg = f"invalid delta length {delta_length}"
            raise ValueError(msg)
        fiber_length = self.fiber_length + delta_length

        v_suffix = f"{'_bend' if bend else ''}_l{fiber_length}_tpb{tpb_thickness_nm}"
        v_name = f"fiber_coating{v_suffix}"
        if v_name in self.registry.solidDict:
            return self.registry.logicalVolumeDict[v_name]

        coating_dim = self.FIBER_DIM + 2 * tpb_thickness_nm / 1e6
        if not bend:
            coating = g4.solid.Box(v_name, coating_dim, coating_dim, fiber_length, self.registry, "mm")
            inner_lv = self.fiber_cl2_lv[fiber_length]
        else:
            coating = g4.solid.Tubs(
                v_name,
                self.bend_radius_mm - coating_dim / 2,
                self.bend_radius_mm + coating_dim / 2,
                coating_dim,
                0,
                math.pi / 2,
                self.registry,
                "mm",
            )
            inner_lv = self.fiber_cl2_bend_lv
        coating_lv = g4.LogicalVolume(coating, self.materials.tpb_on_fibers, v_name, self.registry)
        g4.PhysicalVolume([0, 0, 0], [0, 0, 0], inner_lv, f"fiber_cl2{v_suffix}", coating_lv, self.registry)

        coating_lv.pygeom_color_rgba = [0, 1, 0.165, 0.01]  # 520 nm

        return coating_lv

    def create_module(self, mod: FiberModuleData, b: core.InstrumentationData) -> None:
        module_num = mod.module_num
        if module_num < 0 or module_num >= self.number_of_modules:
            msg = f"invalid module number {module_num} for a maximum of {self.number_of_modules}-1 modules."
            raise ValueError(msg)

        self._cached_fiber_volumes()
        self._cached_sipm_volumes()
        if self.bend_radius_mm is not None:
            self._cached_sipm_volumes_bend()
            coating_lv_bend = self._cached_tpb_coating_volume(mod.tpb_thickness, bend=True)

        string_rot_output = hpge_strings.calculate_string_rotation(str(mod.string_id), b)

        start_angle = self.start_angle(module_num % self.number_of_modules) + string_rot_output["string_rot"]

        z_displacement_straight = self.z_displacement - self.fiber_length / 2

        fibers = []
        sipm_transforms = []  # transforms for SiPMs in the MultiUnion structure.
        for n in range(self.fiber_count_per_module):
            delta_length = 0
            if self.bend_radius_mm is not None:
                # for bent detailed fibers, the fibers would overlap a lot near the bottom SiPMs. To avoid
                # this, use a staggered design of the fibers. This is certainly not the best/most
                # space-efficient packing for squares, but it is simple to implement. From above the solid
                # angle coverage is the same, but there are some holes between the fibers in the lower parts
                # if a photon arrives from the 'right' direction...
                delta_length = self.ALLOWED_DELTA_LENGTHS[n % len(self.ALLOWED_DELTA_LENGTHS)]

            coating_lv = self._cached_tpb_coating_volume(
                mod.tpb_thickness, bend=False, delta_length=delta_length
            )

            th = start_angle + self.angle_per_module / self.fiber_count_per_module * (n + 0.5)
            x = self.radius * math.cos(th) + mod.x_position_mm
            y = self.radius * math.sin(th) + mod.y_position_mm
            fibers.append(
                g4.PhysicalVolume(
                    [0, 0, -th],
                    [x, y, z_displacement_straight - delta_length / 2],
                    coating_lv,
                    f"fiber_{mod.name}_{n}",
                    b.mother_lv,
                    self.registry,
                )
            )
            if self.bend_radius_mm is not None:
                x2 = (self.radius - self.bend_radius_mm) * math.cos(th) + mod.x_position_mm
                y2 = (self.radius - self.bend_radius_mm) * math.sin(th) + mod.y_position_mm
                fibers.append(
                    g4.PhysicalVolume(
                        # this is an extrinsic rotation of pi/2 around X and -th around Z; expressed in intrinsic euler angles.
                        [math.pi / 2, th, 0],
                        [x2, y2, z_displacement_straight - self.fiber_length / 2 - delta_length],
                        coating_lv_bend,
                        f"fiber_bend_{mod.name}_{n}",
                        b.mother_lv,
                        self.registry,
                    )
                )

                # add per-fiber SiPMs (I do not know any other way...)
                sipm_placement_r = self.radius - self.bend_radius_mm - self.SIPM_GAP - self.SIPM_HEIGHT / 2
                x2 = sipm_placement_r * math.cos(th) + mod.x_position_mm
                y2 = sipm_placement_r * math.sin(th) + mod.y_position_mm
                z = z_displacement_straight - self.fiber_length / 2 - delta_length - self.bend_radius_mm
                sipm_transforms.append([[0, 0, th], [x2, y2, z]])

                sipm_placement_outer_r = (
                    sipm_placement_r
                    - self.SIPM_OUTER_EXTRA / 2
                    + self.SIPM_OVERLAP / 2
                    - self.SIPM_GAP
                    - 1e-9
                )
                x2 = sipm_placement_outer_r * math.cos(th) + mod.x_position_mm
                y2 = sipm_placement_outer_r * math.sin(th) + mod.y_position_mm
                g4.PhysicalVolume(
                    [0, 0, -th],
                    [x2, y2, z],
                    self.sipm_outer_bottom_lv_bend,
                    f"{mod.channel_bottom_name}_{n}_wrap",
                    b.mother_lv,
                    self.registry,
                )

        self._add_tpb_surfaces(fibers, b.mother_pv)
        # create SiPMs and attach to fibers
        self._create_sipm(
            mod,
            b,
            module_num,
            fibers,
            True,
            b.mother_lv,
            b.mother_pv,
            mod.channel_top_name,
            mod.channel_top_rawid,
            z_displacement_straight,
            mod.x_position_mm,
            mod.y_position_mm,
        )
        if self.bend_radius_mm is None:
            self._create_sipm(
                mod,
                b,
                module_num,
                fibers,
                False,
                b.mother_lv,
                b.mother_pv,
                mod.channel_bottom_name,
                mod.channel_bottom_rawid,
                z_displacement_straight,
                mod.x_position_mm,
                mod.y_position_mm,
            )

        if self.bend_radius_mm is not None:
            sipm_vols = [self.sipm_bend] * len(sipm_transforms)
            sipm_mu = g4.solid.MultiUnion(mod.channel_bottom_name, sipm_vols, sipm_transforms, self.registry)
            sipm_mu_lv = g4.LogicalVolume(
                sipm_mu, self.materials.metal_silicon, mod.channel_bottom_name, self.registry
            )
            sipm_pv = g4.PhysicalVolume(
                [0, 0, 0],
                [0, 0, 0],
                sipm_mu_lv,
                mod.channel_bottom_name,
                b.mother_lv,
                self.registry,
            )
            sipm_pv.pygeom_active_detector = RemageDetectorInfo("optical", mod.channel_bottom_rawid)
            # Add border surface to mother volume.
            g4.BorderSurface(
                f"bsurface_lar_{mod.channel_bottom_name}",
                b.mother_pv,
                sipm_pv,
                self.materials.surfaces.to_sipm_silicon,
                self.registry,
            )


class ModuleFactorySegment(ModuleFactoryBase):
    def _get_bend_polycone(
        self, inner_r: float, outer_r: float
    ) -> tuple[np.typing.ArrayLike, np.typing.ArrayLike]:
        """In the segmented model, there is no fundamental shape for the fiber bent available, so we
        use a polycone as a replacement.
        """
        delta_r_mm = (outer_r - inner_r) / 2
        bend_r_outer = self.bend_radius_mm + delta_r_mm
        bend_r_inner = self.bend_radius_mm - delta_r_mm

        angles = np.linspace(0, np.pi / 2, 100)
        z1 = bend_r_outer * np.sin(angles)
        r1 = bend_r_outer * np.cos(angles)
        z2 = bend_r_inner * np.sin(angles)
        r2 = bend_r_inner * np.cos(angles)

        z = self.bend_radius_mm - np.concatenate((z1, np.flip(z2)))
        # offset by the radius at the inner end of the bend.
        r = (outer_r - bend_r_outer) + np.concatenate((r1, np.flip(r2)))

        return z, r

    def _cached_sipm_volumes_bend(self) -> None:
        """Creates (dummy) SiPM volumes for use at the bottom of bent fiber sections."""
        v_suffix = f"_bend{self.bend_radius_mm}_r{self.radius}_nmod{self.number_of_modules}"
        v_name = f"sipm{v_suffix}"
        if v_name in self.registry.solidDict:
            return

        sipm_dim = self.FIBER_DIM + self.SIPM_GAP_SIDE  # GAP_SIDE to fit round->square
        fiber_segment = self.angle_per_module
        # radius of the inner circle at the bottom, already including the small gap between fibers and SiPM.
        inner_radius = self.radius - self.bend_radius_mm - self.SIPM_GAP

        sipm = g4.solid.Tubs(
            v_name,
            inner_radius - self.SIPM_HEIGHT,
            inner_radius,
            sipm_dim,
            self.ANGLE_SAFETY,
            fiber_segment - self.ANGLE_SAFETY,
            self.registry,
            "mm",
        )
        self.sipm_lv_bend = g4.LogicalVolume(sipm, self.materials.metal_silicon, v_name, self.registry)

        sipm_outer1 = g4.solid.Tubs(
            f"sipm_outer1{v_suffix}",
            inner_radius - self.SIPM_HEIGHT - self.SIPM_OUTER_EXTRA,
            inner_radius + self.SIPM_OVERLAP,
            sipm_dim + 2 * self.SIPM_OUTER_EXTRA,
            self.ANGLE_SAFETY,
            fiber_segment - self.ANGLE_SAFETY,
            self.registry,
            "mm",
        )
        sipm_outer2 = g4.solid.Tubs(
            f"sipm_outer2{v_suffix}",
            inner_radius - self.SIPM_HEIGHT - 1e-9,
            inner_radius + 2 * self.SIPM_GAP + self.SIPM_OVERLAP,
            sipm_dim + 1e-9,
            self.ANGLE_SAFETY,
            fiber_segment - self.ANGLE_SAFETY,
            self.registry,
            "mm",
        )
        sipm_outer_bottom = g4.solid.Subtraction(
            f"sipm_outer_bottom{v_suffix}",
            sipm_outer1,
            sipm_outer2,
            [[0, 0, 0], [0, 0, 0]],
            self.registry,
        )
        self.sipm_outer_bottom_lv_bend = g4.LogicalVolume(
            sipm_outer_bottom,
            self.materials.metal_copper,
            f"sipm_outer_bottom{v_suffix}",
            self.registry,
        )

    def _cached_fiber_volumes(self) -> None:
        """Create solids, logical and physical volumes for the fibers, as specified by the parameters of this instance."""
        v_suffix = f"_l{self.fiber_length}"
        if f"fiber_cl2{v_suffix}" in self.registry.solidDict:
            return

        # create solids
        angle = self.angle_per_module  # 2 * np.pi / self.number_of_modules
        dim_cl2 = self.FIBER_DIM
        fiber_cl2 = g4.solid.Tubs(
            f"fiber_cl2{v_suffix}",
            self.radius - dim_cl2 / 2,
            self.radius + dim_cl2 / 2,
            self.fiber_length,
            0,
            angle,
            self.registry,
            "mm",
        )
        dim_cl1 = self.FIBER_DIM - 2 * self.FIBER_THICKNESS_CL1
        fiber_cl1 = g4.solid.Tubs(
            f"fiber_cl1{v_suffix}",
            self.radius - dim_cl1 / 2,
            self.radius + dim_cl1 / 2,
            self.fiber_length,
            0,
            angle,
            self.registry,
            "mm",
        )
        dim_core = self.FIBER_DIM - 2 * (self.FIBER_THICKNESS_CL1 + self.FIBER_THICKNESS_CL2)
        fiber_core = g4.solid.Tubs(
            f"fiber_core{v_suffix}",
            self.radius - dim_core / 2,
            self.radius + dim_core / 2,
            self.fiber_length,
            0,
            angle,
            self.registry,
            "mm",
        )
        if self.bend_radius_mm is not None:
            z, r = self._get_bend_polycone(self.radius - dim_cl2 / 2, self.radius + dim_cl2 / 2)
            fiber_cl2_bend = g4.solid.GenericPolycone(
                f"fiber_cl2_bend{v_suffix}", 0, angle, r, z, self.registry, "mm"
            )
            z, r = self._get_bend_polycone(self.radius - dim_cl1 / 2, self.radius + dim_cl1 / 2)
            fiber_cl1_bend = g4.solid.GenericPolycone(
                f"fiber_cl1_bend{v_suffix}", 0, angle, r, z, self.registry, "mm"
            )
            z, r = self._get_bend_polycone(self.radius - dim_core / 2, self.radius + dim_core / 2)
            fiber_core_bend = g4.solid.GenericPolycone(
                f"fiber_core_bend{v_suffix}", 0, angle, r, z, self.registry, "mm"
            )

        self.fiber_cl2_lv = g4.LogicalVolume(
            fiber_cl2, self.materials.pmma_out, f"fiber_cl2{v_suffix}", self.registry
        )
        self.fiber_cl2_lv.pygeom_color_rgba = False
        fiber_cl1_lv = g4.LogicalVolume(fiber_cl1, self.materials.pmma, f"fiber_cl1{v_suffix}", self.registry)
        fiber_cl1_lv.pygeom_color_rgba = False
        fiber_core_lv = g4.LogicalVolume(
            fiber_core, self.materials.ps_fibers, f"fiber_core{v_suffix}", self.registry
        )
        fiber_core_lv.pygeom_color_rgba = False
        if self.bend_radius_mm is not None:
            self.fiber_cl2_bend_lv = g4.LogicalVolume(
                fiber_cl2_bend, self.materials.pmma_out, f"fiber_cl2_bend{v_suffix}", self.registry
            )
            self.fiber_cl2_bend_lv.pygeom_color_rgba = False
            fiber_cl1_bend_lv = g4.LogicalVolume(
                fiber_cl1_bend, self.materials.pmma, f"fiber_cl1_bend{v_suffix}", self.registry
            )
            fiber_cl1_bend_lv.pygeom_color_rgba = False
            fiber_core_bend_lv = g4.LogicalVolume(
                fiber_core_bend, self.materials.ps_fibers, f"fiber_core_bend{v_suffix}", self.registry
            )
            fiber_core_bend_lv.pygeom_color_rgba = False

        g4.PhysicalVolume(
            [0, 0, 0],
            [0, 0, 0],
            fiber_cl1_lv,
            f"fiber_cl1{v_suffix}",
            self.fiber_cl2_lv,
            self.registry,
        )
        g4.PhysicalVolume(
            [0, 0, 0],
            [0, 0, 0],
            fiber_core_lv,
            f"fiber_core{v_suffix}",
            fiber_cl1_lv,
            self.registry,
        )
        if self.bend_radius_mm is not None:
            g4.PhysicalVolume(
                [0, 0, 0],
                [0, 0, 0],
                fiber_cl1_bend_lv,
                f"fiber_cl1_bend{v_suffix}",
                self.fiber_cl2_bend_lv,
                self.registry,
            )
            g4.PhysicalVolume(
                [0, 0, 0],
                [0, 0, 0],
                fiber_core_bend_lv,
                f"fiber_core_bend{v_suffix}",
                fiber_cl1_bend_lv,
                self.registry,
            )

    def _cached_tpb_coating_volume(self, tpb_thickness_nm: float, bend: bool = False) -> g4.LogicalVolume:
        """Create and cache a TPB coating layer of the specified thickness.

        The TPB-Layer is dependent on the module (i.e. the applied thickness varies slightly),
        so we cannot cache it globally on this instance.
        """
        v_suffix = f"{'_bend' if bend else ''}_l{self.fiber_length}_tpb{tpb_thickness_nm}"
        v_name = f"fiber_coating{v_suffix}"
        if v_name in self.registry.solidDict:
            return self.registry.logicalVolumeDict[v_name]

        coating_dim = self.FIBER_DIM + 2 * tpb_thickness_nm / 1e6
        if not bend:
            coating = g4.solid.Tubs(
                v_name,
                self.radius - coating_dim / 2,
                self.radius + coating_dim / 2,
                self.fiber_length,
                0,
                self.angle_per_module,  # 2 * math.pi / self.number_of_modules,
                self.registry,
                "mm",
            )
            inner_lv = self.fiber_cl2_lv
        else:
            angle = self.angle_per_module
            z, r = self._get_bend_polycone(self.radius - coating_dim / 2, self.radius + coating_dim / 2)
            coating = g4.solid.GenericPolycone(v_name, 0, angle, r, z, self.registry, "mm")
            inner_lv = self.fiber_cl2_bend_lv
        coating_lv = g4.LogicalVolume(coating, self.materials.tpb_on_fibers, v_name, self.registry)
        g4.PhysicalVolume(
            [0, 0, 0],
            [0, 0, 0],
            inner_lv,
            f"fiber_cl2{v_suffix}",
            coating_lv,
            self.registry,
        )

        coating_lv.pygeom_color_rgba = [0, 1, 0.165, 0.01]  # 520 nm

        return coating_lv

    def create_module(self, mod: FiberModuleData, b: core.InstrumentationData) -> None:
        module_num = mod.module_num
        if module_num < 0 or module_num >= self.number_of_modules:
            msg = f"invalid module number {module_num} for a maximum of {self.number_of_modules}-1 modules."
            raise ValueError(msg)

        self._cached_fiber_volumes()
        self._cached_sipm_volumes()
        coating_lv = self._cached_tpb_coating_volume(mod.tpb_thickness, bend=False)
        if self.bend_radius_mm is not None:
            self._cached_sipm_volumes_bend()
            coating_lv_bend = self._cached_tpb_coating_volume(mod.tpb_thickness, bend=True)

        string_rot_output = hpge_strings.calculate_string_rotation(str(mod.string_id), b)

        start_angle = self.start_angle(module_num % self.number_of_modules) + string_rot_output["string_rot"]
        z_displacement_straight = self.z_displacement - self.fiber_length / 2

        fibers = []

        th = start_angle

        fibers.append(
            g4.PhysicalVolume(
                [0, 0, -th],
                [mod.x_position_mm, mod.y_position_mm, z_displacement_straight],
                coating_lv,
                f"fiber_{mod.name}_s",
                b.mother_lv,
                self.registry,
            )
        )
        if self.bend_radius_mm is not None:
            fibers.append(
                g4.PhysicalVolume(
                    [0, 0, -th],
                    [
                        mod.x_position_mm,
                        mod.y_position_mm,
                        z_displacement_straight - self.fiber_length / 2 - self.bend_radius_mm,
                    ],
                    coating_lv_bend,
                    f"fiber_bend_{mod.name}_s",
                    b.mother_lv,
                    self.registry,
                )
            )

        self._add_tpb_surfaces(fibers, b.mother_pv)

        # create SiPMs and attach to fibers
        self._create_sipm(
            mod,
            b,
            module_num,
            fibers,
            True,
            b.mother_lv,
            b.mother_pv,
            mod.channel_top_name,
            mod.channel_top_rawid,
            z_displacement_straight,
            mod.x_position_mm,
            mod.y_position_mm,
        )
        if self.bend_radius_mm is None:
            self._create_sipm(
                mod,
                b,
                module_num,
                fibers,
                False,
                b.mother_lv,
                b.mother_pv,
                mod.channel_bottom_name,
                mod.channel_bottom_rawid,
                z_displacement_straight,
                mod.x_position_mm,
                mod.y_position_mm,
            )
        else:
            z = z_displacement_straight - self.fiber_length / 2 - self.bend_radius_mm
            sipm_pv = g4.PhysicalVolume(
                [0, 0, -start_angle],
                [0, 0, z],
                self.sipm_lv_bend,
                mod.channel_bottom_name,
                b.mother_lv,
                self.registry,
            )
            sipm_pv.pygeom_active_dector = RemageDetectorInfo("optical", mod.channel_bottom_rawid)
            # Add border surface to mother volume.
            g4.BorderSurface(
                f"bsurface_lar_{mod.channel_bottom_name}",
                b.mother_pv,
                sipm_pv,
                self.materials.surfaces.to_sipm_silicon,
                self.registry,
            )

            g4.PhysicalVolume(
                [0, 0, -start_angle],
                [0, 0, z],
                self.sipm_outer_bottom_lv_bend,
                f"{mod.channel_bottom_name}_wrap",
                b.mother_lv,
                self.registry,
            )
