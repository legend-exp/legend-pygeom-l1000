"""Render the images embedded in ``docs/source/description.md``.

Run this after changing the geometry and inspect (or ``git diff``) the resulting
PNGs.

Usage::

    python docs/generate_docs_images.py            # render everything
    python docs/generate_docs_images.py string     # render a single view
    python docs/generate_docs_images.py --fast     # coarse meshes, for iterating
"""

from __future__ import annotations

import argparse
import logging
import math
import re
from pathlib import Path

import numpy as np
from pyg4ometry import config as meshconfig
from pyg4ometry import geant4 as g4
from pyg4ometry.transformation import tbxyz2matrix
from pygeomtools import viewer, write_pygeom

from pygeoml1000 import config, core

log = logging.getLogger("generate_docs_images")

IMAGE_DIR = Path(__file__).parent / "source" / "images"

HIDE = False

_VIEW_DIRECTION = (-1.0, -0.35, 0.45)

_VIEW_DIRECTION_LEVEL = (-1.0, -0.35, 0.15)

_VIEW_DIRECTION_BELOW = (-1.0, -0.35, -1.25)

_VIEW_ANGLE_DEG = 30.0

STEEL = (0.5, 0.5, 0.5, 0.10)
TUBE = (0.45, 0.55, 0.75, 0.10)
WATER = (0, 0, 1, 0.08)
AIR = (0.85, 0.9, 1, 0.07)

CRYOSTAT_LVS = (
    "reentrance_tube_copper",
    "cryostat_outer_steel_316L",
    "cryostat_inner_steel_316L",
    "cryostat_insulation_vacuum",
    "liquid_argon_underground",
    "liquid_argon_atmospheric",
    "reentrance_tube_layer_copper_ofhc",
    "reentrance_tube_layer_steel_316L",
    "neutron_moderator_pmma",
    "cryostat_skirt_steel_316L",
    "cryostat_foot_steel_316L",
    "underground_wlsr_tpb",
    "underground_wlsr_tetratex",
    "atmospheric_wlsr_tpb",
    "atmospheric_wlsr_tetratex",
)
HIDE_CRYOSTAT = dict.fromkeys(CRYOSTAT_LVS, HIDE)
HIDE_STRING_SUPPORT = {"hpge_string_support_hanger_copper": HIDE}
ARRAY_ASSEMBLIES = ["cryostat", "HPGe_dets", "PEN_plates", "front-end_and_insulators"]

# ----------------------------------------------------------------------------
# the renderings
# ----------------------------------------------------------------------------

IMAGES = {
    "detector_unit": {
        "assemblies": ARRAY_ASSEMBLIES,
        "strings": {1},
        "positions": {1},
        "overrides": {**HIDE_CRYOSTAT, **HIDE_STRING_SUPPORT},
        "window_size": [700, 800],
        "view_direction": _VIEW_DIRECTION_BELOW,
    },
    "string": {
        "assemblies": ARRAY_ASSEMBLIES,
        "strings": {1},
        "overrides": HIDE_CRYOSTAT,
        "window_size": [400, 900],
    },
    "string_fibers": {
        "assemblies": [*ARRAY_ASSEMBLIES, "fiber_curtain"],
        "strings": {1},
        "overrides": {
            **HIDE_CRYOSTAT,
            r"fiber_coating_tpb_.*": (0, 1, 0.165, 0.25),
        },
        "window_size": [400, 900],
    },
    "array_reentrance_tube": {
        "assemblies": ARRAY_ASSEMBLIES,
        "overrides": {
            "reentrance_tube_copper": TUBE,
            **{lv: HIDE for lv in CRYOSTAT_LVS if lv != "reentrance_tube_copper"},
        },
        "window_size": [500, 1000],
        "view_direction": _VIEW_DIRECTION_LEVEL,
    },
    "array_cryostat": {
        "assemblies": ARRAY_ASSEMBLIES,
        "overrides": {
            "reentrance_tube_copper": TUBE,
            "cryostat_outer_steel_316L": STEEL,
            "cryostat_inner_steel_316L": STEEL,
            "neutron_moderator_pmma": STEEL,
            "cryostat_skirt_steel_316L": STEEL,
            "cryostat_foot_steel_316L": STEEL,
        },
        "window_size": [500, 1000],
        "view_direction": _VIEW_DIRECTION_LEVEL,
    },
    "detector_unit_cosmogenic": {
        "detail": "cosmogenic",
        "assemblies": ["cryostat", "HPGe_dets", "PEN_plates"],
        "strings": {1},
        "positions": {1},
        "overrides": {**HIDE_CRYOSTAT, **HIDE_STRING_SUPPORT},
        "window_size": [700, 800],
        "view_direction": _VIEW_DIRECTION_BELOW,
    },
    "watertank": {
        "detail": "cosmogenic",
        "assemblies": [
            "cryostat",
            "HPGe_dets",
            "PEN_plates",
            "watertank",
            "watertank_instrumentation",
        ],
        "overrides": {
            "watertank_steel_304L": STEEL,
            "watertank_water": WATER,
            "reentrance_tube_copper": TUBE,
            "cryostat_outer_steel_316L": STEEL,
            "cryostat_inner_steel_316L": STEEL,
            "neutron_moderator_pmma": STEEL,
            "cryostat_skirt_steel_316L": STEEL,
            "cryostat_foot_steel_316L": STEEL,
        },
        "window_size": [600, 600],
        "view_direction": _VIEW_DIRECTION_LEVEL,
    },
    "cavern": {
        "detail": "cosmogenic",
        "assemblies": [
            "cavern",
            "cryostat",
            "HPGe_dets",
            "PEN_plates",
            "watertank",
            "watertank_instrumentation",
        ],
        "overrides": {
            "rock": HIDE,
            "cavern_air": AIR,
            "watertank_steel_304L": STEEL,
            "watertank_water": WATER,
            "reentrance_tube_copper": TUBE,
            "cryostat_outer_steel_316L": STEEL,
            "cryostat_inner_steel_316L": STEEL,
            "neutron_moderator_pmma": STEEL,
            "cryostat_skirt_steel_316L": STEEL,
            "cryostat_foot_steel_316L": STEEL,
        },
        "window_size": [800, 800],
        "view_direction": _VIEW_DIRECTION_LEVEL,
    },
}


# ----------------------------------------------------------------------------
# metadata subsetting
# ----------------------------------------------------------------------------


def _subset_metadata(
    strings: set[int] | None, positions: set[int] | None, raw_config: dict | str = ""
) -> dict:
    """Build a config restricted to the given strings (and detector positions).

    There is no assembly for "one string" or "one detector unit", so the views
    showing those are built from a filtered channelmap and ``special_metadata``,
    the same way :doc:`runtime-cfg` describes removing detectors by hand.
    """
    if strings is None:
        return {}

    resolved = config.resolve_config({"raw_config": raw_config} if raw_config else {})
    channelmap = resolved["channelmap"]
    special_metadata = resolved["special_metadata"]

    def _keep_ged(ch: dict) -> bool:
        loc = ch["location"]
        return loc["string"] in strings and (positions is None or loc["position"] in positions)

    kept_geds = {k for k, v in channelmap.items() if v.get("system") == "geds" and _keep_ged(v)}
    kept_spms = {
        k for k, v in channelmap.items() if v.get("system") == "spms" and v["location"]["barrel"] in strings
    }

    channelmap = {
        k: v
        for k, v in channelmap.items()
        if v.get("system") not in ("geds", "spms") or k in kept_geds | kept_spms
    }

    special_metadata["hpges"] = {k: v for k, v in special_metadata["hpges"].items() if k in kept_geds}
    special_metadata["fibers"] = {
        k: v for k, v in special_metadata["fibers"].items() if _string_of(k) in strings
    }
    special_metadata["hpge_string"] = {
        k: v for k, v in special_metadata["hpge_string"].items() if int(k) in strings
    }

    return {"channelmap": channelmap, "special_metadata": special_metadata}


def _string_of(fiber_name: str) -> int:
    """Extract the string number from a fiber module name such as ``S0203``."""
    return int(fiber_name[1:-2])


# ----------------------------------------------------------------------------
# camera auto-framing
# ----------------------------------------------------------------------------


def _is_visible(lv: g4.LogicalVolume, overrides: dict) -> bool:
    """Decide whether a logical volume ends up being drawn, mirroring the viewer."""
    for pattern, color in overrides.items():
        if re.match(f"{pattern}$", lv.name):
            return color is not False and color[3] > 0

    color = getattr(lv, "pygeom_color_rgba", None)
    if color is None:
        return True
    return color is not False and color[3] > 0


def _local_bounds(lv: g4.LogicalVolume, cache: dict) -> tuple[np.ndarray, np.ndarray] | None:
    """Bounding box of a logical volume's own solid, in its local frame."""
    if lv.name not in cache:
        try:
            vertices = np.array(lv.solid.mesh().toVerticesAndPolygons()[0])
            cache[lv.name] = None if len(vertices) == 0 else (vertices.min(0), vertices.max(0))
        except Exception:  # noqa: BLE001
            log.debug("could not mesh %s for framing", lv.name)
            cache[lv.name] = None
    return cache[lv.name]


def _visible_bounds(lv: g4.LogicalVolume, overrides: dict) -> tuple[np.ndarray, np.ndarray] | None:
    """World-frame bounding box of everything that is visible in this geometry."""
    cache: dict = {}
    corners: list[np.ndarray] = []

    def walk(lv: g4.LogicalVolume, rotation: np.ndarray, translation: np.ndarray) -> None:
        if lv.name != "world" and _is_visible(lv, overrides):
            bounds = _local_bounds(lv, cache)
            if bounds is not None:
                low, high = bounds
                box = np.array(np.meshgrid(*zip(low, high, strict=True))).reshape(3, -1).T
                corners.append(box @ rotation.T + translation)

        for pv in lv.daughterVolumes:
            if pv.type != "placement":
                continue
            pv_rot = np.array(tbxyz2matrix([float(x) for x in pv.rotation.eval()]))
            pv_pos = np.array([float(x) for x in pv.position.eval()])
            walk(pv.logicalVolume, rotation @ pv_rot, rotation @ pv_pos + translation)

    walk(lv, np.eye(3), np.zeros(3))

    if not corners:
        return None
    stacked = np.concatenate(corners)
    return stacked.min(0), stacked.max(0)


def _auto_camera(
    registry: g4.Registry,
    overrides: dict,
    window_size: list[int],
    view_direction: tuple[float, float, float] = _VIEW_DIRECTION,
) -> dict | None:
    """Frame the camera around the visible volumes of the geometry."""
    bounds = _visible_bounds(registry.worldVolume, overrides)
    if bounds is None:
        log.warning("nothing visible to frame, leaving the camera to VTK")
        return None

    low, high = bounds
    focus = (low + high) / 2
    size = high - low

    half_vertical = math.radians(_VIEW_ANGLE_DEG) / 2
    aspect = window_size[0] / window_size[1]
    half_horizontal = math.atan(aspect * math.tan(half_vertical))

    width = max(size[0], size[1])
    distance = 1.25 * max(
        (size[2] / 2) / math.tan(half_vertical),
        (width / 2) / math.tan(half_horizontal),
    )

    direction = np.array(view_direction) / np.linalg.norm(view_direction)
    return {
        "focus": focus.tolist(),
        "up": [0, 0, 1],
        "camera": (focus + direction * distance).tolist(),
    }


# ----------------------------------------------------------------------------
# rendering
# ----------------------------------------------------------------------------


def export_image(name: str, spec: dict) -> None:
    """Build the geometry for one view and render it to ``docs/source/images``."""
    log.info("building geometry for %s", name)

    geom_config = _subset_metadata(spec.get("strings"), spec.get("positions"))
    geom_config["assemblies"] = list(spec["assemblies"])
    geom_config["detail"] = spec.get("detail", config.DEFAULT_DETAIL)
    registry = core.construct(geom_config)
    log.info("%s: %d physical volumes", name, len(registry.physicalVolumeDict))

    write_pygeom(registry, None)

    overrides = spec.get("overrides", {})
    window_size = spec.get("window_size", [500, 900])
    camera = spec.get("camera") or _auto_camera(
        registry, overrides, window_size, spec.get("view_direction", _VIEW_DIRECTION)
    )

    target = IMAGE_DIR / f"{name}.png"
    target.unlink(missing_ok=True)

    scene = {
        "window_size": window_size,
        "color_overrides": overrides,
        "export_scale": 1,
        "export_and_exit": str(target),
    }
    if camera is not None:
        scene["default"] = camera

    log.info("rendering %s", name)
    viewer.visualize(registry, scene)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "images",
        nargs="*",
        choices=list(IMAGES),
        help="names of the views to render (default: all of them)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="use the coarse default meshes, for quickly iterating on a view",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if not args.fast:
        meshconfig.setGlobalMeshSliceAndStack(100)

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    for name in args.images or IMAGES:
        export_image(name, IMAGES[name])


if __name__ == "__main__":
    main()
