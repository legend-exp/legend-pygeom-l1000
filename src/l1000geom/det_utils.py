from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pyg4ometry.geant4 as g4

log = logging.getLogger(__name__)


@dataclass
class RemageDetectorInfo:
    detector_type: Literal["optical", "germanium"]
    uid: int


def _detector_macro_recursive(pv: g4.PhysicalVolume, macro_lines: dict) -> None:
    if hasattr(pv, "pygeom_active_dector") and pv.name not in macro_lines:
        det = pv.pygeom_active_dector
        assert isinstance(det, RemageDetectorInfo)
        mac = f"/RMG/Geometry/RegisterDetector k{det.detector_type.title()} {pv.name} {det.uid}\n"
        macro_lines[pv.name] = mac

    for dv in pv.logicalVolume.daughterVolumes:
        if pv.type == "placement":
            _detector_macro_recursive(dv, macro_lines)


def generate_detector_macro(registry: g4.Registry, filename: str) -> None:
    """Create a Geant4 macro file containing the defined active detector volumes for use in remage."""
    macro_lines = {}
    for pv in registry.worldVolume.daughterVolumes:
        _detector_macro_recursive(pv, macro_lines)
    macro_contents = "".join(macro_lines.values())

    with Path.open(filename, "w", encoding="utf-8") as f:
        f.write(macro_contents)
