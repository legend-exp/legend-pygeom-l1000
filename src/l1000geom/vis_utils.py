from __future__ import annotations

import logging
from pathlib import Path

import pyg4ometry.geant4 as g4
from pyg4ometry import visualisation

log = logging.getLogger(__name__)


def _color_recursive(lv: g4.LogicalVolume, viewer: visualisation.ViewerBase) -> None:
    if hasattr(lv, "pygeom_color_rgba"):
        for vis in viewer.instanceVisOptions[lv.name]:
            if lv.pygeom_color_rgba is False:
                vis.alpha = 0
                vis.visible = False
            else:
                vis.colour = lv.pygeom_color_rgba[0:3]
                vis.alpha = lv.pygeom_color_rgba[3]
                vis.visible = vis.alpha > 0

    for pv in lv.daughterVolumes:
        if pv.type == "placement":
            _color_recursive(pv.logicalVolume, viewer)


def visualize(registry: g4.Registry) -> None:
    v = visualisation.VtkViewerColouredNew()
    v.addLogicalVolume(registry.worldVolume)

    _color_recursive(registry.worldVolume, v)

    v.buildPipelinesAppend()
    v.addAxes(length=5000)
    v.view()


def _color_macro_recursive(lv: g4.LogicalVolume, macro_lines: dict) -> None:
    if hasattr(lv, "pygeom_color_rgba") and lv.name not in macro_lines:
        mac = f"/vis/geometry/set/forceSolid {lv.name}\n"
        if lv.pygeom_color_rgba is False or lv.pygeom_color_rgba[3] == 0:
            mac += f"/vis/geometry/set/visibility {lv.name} -1 false\n"
        else:
            rgba = " ".join([str(c) for c in lv.pygeom_color_rgba])
            mac += f"/vis/geometry/set/colour {lv.name} 0 {rgba}\n"
        macro_lines[lv.name] = mac

    for pv in lv.daughterVolumes:
        if pv.type == "placement":
            _color_macro_recursive(pv.logicalVolume, macro_lines)


def generate_color_macro(registry: g4.Registry, filename: str) -> None:
    """Create a Geant4 macro file containing the defined visualization attributes."""
    macro_lines = {}
    _color_macro_recursive(registry.worldVolume, macro_lines)
    macro_contents = "".join(macro_lines.values())

    with Path.open(filename, "w", encoding="utf-8") as f:
        f.write(macro_contents)
