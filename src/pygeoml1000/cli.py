# ruff: noqa: PLC0415

from __future__ import annotations

import argparse
import logging

from pyg4ometry import config as meshconfig
from pygeomoptics.store import load_user_material_code
from pygeomtools import detectors, utils, visualization, write_pygeom

from . import _version, core, dummy_metadata_generator

log = logging.getLogger(__name__)


def dump_gdml_cli() -> None:
    parser = argparse.ArgumentParser(
        prog="legend-pygeom-l1000",
        description="%(prog)s command line interface",
    )

    # global options
    parser.add_argument(
        "--version",
        action="version",
        help="""Print %(prog)s version and exit""",
        version=_version.__version__,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="""Increase the program verbosity""",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="""Increase the program verbosity to maximum""",
    )
    parser.add_argument(
        "--visualize",
        "-V",
        nargs="?",
        const=True,
        help="""Open a VTK visualization of the generated geometry (with optional scene file)""",
    )
    parser.add_argument(
        "--vis-macro-file",
        action="store",
        help="""Filename to write a Geant4 macro file containing visualization attributes""",
    )
    parser.add_argument(
        "--det-macro-file",
        action="store",
        help="""Filename to write a Geant4 macro file containing active detectors (to be used with remage)""",
    )
    parser.add_argument(
        "--check-overlaps",
        action="store_true",
        help="""Check for overlaps with pyg4ometry (note: this might not be accurate)""",
    )
    parser.add_argument(
        "--pygeom-optics-plugin",
        action="store",
        help="""Execute the python module given by this path before constructing the geometry""",
    )

    # options for geometry generation.
    geom_opts = parser.add_argument_group("geometry options")
    geom_opts.add_argument(
        "--assemblies",
        action="store",
        default=None,
        help="""Select the assemblies to generate in the output. If specified, changes all unspecified assemblies to 'omit'.""",
    )
    geom_opts.add_argument(
        "--detail",
        action="store",
        default="radiogenic",
        help="""Select the detail level for the setup. (default: %(default)s)""",
    )
    geom_opts.add_argument(
        "--config",
        action="store",
        help="""Select a config file to read geometry config from.""",
    )

    # options for metadata generation
    meta_opts = parser.add_argument_group("metadata generation options")
    meta_opts.add_argument(
        "--generate-metadata",
        action="store_true",
        help="""Generate necessary dummy metadata files (special_metadata.yaml and channelmap.json)""",
    )
    meta_opts.add_argument(
        "--metadata-config",
        action="store",
        default="",
        help="""Config file for metadata generation (defaults to configs/config.json)""",
    )
    meta_opts.add_argument(
        "--output-special-metadata",
        action="store",
        default="",
        help="""Output file for special metadata (defaults to configs/special_metadata.yaml)""",
    )
    meta_opts.add_argument(
        "--output-channelmap",
        action="store",
        default="",
        help="""Output file for channelmap (defaults to configs/channelmap.json)""",
    )
    meta_opts.add_argument(
        "--dets-from-metadata",
        action="store",
        default="",
        help="""Use HPGe detector from metadata as dummy. Format: '{"hpge": "DETECTOR_NAME"}', e.g., '{"hpge": "V000000A"}'""",
    )

    parser.add_argument(
        "filename",
        default=None,
        nargs="?",
        help="""File name for the output GDML geometry.""",
    )

    args = parser.parse_args()

    if not args.visualize and args.filename is None and not args.generate_metadata:
        parser.error("no output file, no visualization, and no metadata generation specified")
    if (args.vis_macro_file or args.det_macro_file) and args.filename is None:
        parser.error("writing macro file(s) without gdml file is not possible")

    if args.verbose:
        logging.getLogger("pygeoml1000").setLevel(logging.DEBUG)
    if args.debug:
        logging.root.setLevel(logging.DEBUG)

    # Handle metadata generation
    if args.generate_metadata:
        log.info("generating dummy metadata files")
        try:
            dummy_metadata_generator.setup_dummy_metadata(
                input_config=args.metadata_config,
                output_special_metadata=args.output_special_metadata,
                output_channelmap=args.output_channelmap,
                dets_from_metadata=args.dets_from_metadata,
            )
            log.info("metadata files generated successfully")
        except Exception as e:
            log.error("failed to generate metadata files: %s", e)
            return

    config = {}
    if args.config:
        config = utils.load_dict(args.config)

    # Skip geometry generation if only generating metadata
    if args.generate_metadata and args.filename is None and not args.visualize:
        return

    vis_scene = {}
    if isinstance(args.visualize, str):
        vis_scene = utils.load_dict(args.visualize)

    if vis_scene.get("fine_mesh", False) or args.check_overlaps:
        meshconfig.setGlobalMeshSliceAndStack(100)

    # load custom module to change material properties.
    if args.pygeom_optics_plugin:
        load_user_material_code(args.pygeom_optics_plugin)

    registry = core.construct(
        assemblies=args.assemblies.split(",") if args.assemblies else None,
        detail_level=args.detail,
        config=config,
    )

    if args.check_overlaps:
        msg = "checking for overlaps"
        log.info(msg)
        registry.worldVolume.checkOverlaps(recursive=True)

    if args.filename is not None:
        log.info("exporting GDML geometry to %s", args.filename)
    write_pygeom(registry, args.filename)

    if args.det_macro_file:
        detectors.generate_detector_macro(registry, args.det_macro_file)

    if args.vis_macro_file:
        visualization.generate_color_macro(registry, args.vis_macro_file)

    if args.visualize:
        log.info("visualizing...")
        from pygeomtools import viewer

        viewer.visualize(registry, vis_scene)
