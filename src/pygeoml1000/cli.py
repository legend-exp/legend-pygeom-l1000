# ruff: noqa: PLC0415

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import dbetto
from pyg4ometry import config as meshconfig
from pygeomoptics.store import load_user_material_code
from pygeomtools import detectors, visualization, write_pygeom

from . import _version, config_compilation, core

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

    config_opts = parser.add_argument_group("config options")
    config_opts.add_argument(
        "--copy-raw-configs-into-cwd-folder",
        action="store_true",
        help="""Copy the raw config files to the cwd folder. This is useful for creating a custom config file based on the default raw configs. The default raw configs are located in the 'configs' folder of this package.""",
    )
    config_opts.add_argument(
        "--generate-compiled-config",
        action="store_true",
        help="""Generate the compiled config file containing the special_metadata and channelmap.""",
    )
    config_opts.add_argument(
        "--output-compiled-config",
        action="store",
        default="",
        help="""Output file for the compiled config file (default is [cwd]/config.yaml).""",
    )
    config_opts.add_argument(
        "--compiled-config",
        help="""Use a compiled config file containing the special_metadata and channelmap instead of generating a new geometry. Overrides using the raw config files.""",
    )
    config_opts.add_argument(
        "--input-raw-config-folder",
        action="store",
        default="",
        help="""Folder location of raw input config files (defaults to Path(__file__).parent/configs/).""",
    )
    parser.add_argument(
        "filename",
        default=None,
        nargs="?",
        help="""File name for the output GDML geometry.""",
    )

    args = parser.parse_args()

    if (
        not args.visualize
        and args.filename is None
        and not args.generate_compiled_config
        and not args.copy_raw_configs_into_cwd_folder
    ):
        parser.error("no output file, no visualization, and no metadata generation specified")
    if (args.vis_macro_file or args.det_macro_file) and args.filename is None:
        parser.error("writing macro file(s) without gdml file is not possible")

    if args.verbose:
        logging.getLogger("pygeoml1000").setLevel(logging.DEBUG)
    if args.debug:
        logging.root.setLevel(logging.DEBUG)

    if args.copy_raw_configs_into_cwd_folder:
        log.info("copying raw config files to %s", Path.cwd())
        folder = Path.cwd()
        try:
            config_compilation.copy_raw_configs(destination_folder=folder)
            log.info("raw config files copied successfully")
        except Exception as e:
            log.error("failed to copy raw config files: %s", e)
            return

    if args.generate_compiled_config:
        log.info("generating default config file")
        try:
            config_compilation.setup_config_file(
                input_config_folder=args.input_raw_config_folder, output_config=args.output_compiled_config
            )
            log.info("config file generated successfully")
        except Exception as e:
            log.error("failed to generate config file: %s", e)
            return

    if args.compiled_config and args.input_raw_config_folder:
        log.warning("input_raw_config_folder is ignored when using a compiled config file")

    config = {}
    if args.compiled_config:
        config = dbetto.utils.load_dict(args.compiled_config)

    if (
        (args.generate_compiled_config or args.copy_raw_configs_into_cwd_folder)
        and args.filename is None
        and not args.visualize
    ):
        return

    vis_scene = {}
    if isinstance(args.visualize, str):
        vis_scene = dbetto.utils.load_dict(args.visualize)

    if vis_scene.get("fine_mesh", False) or args.check_overlaps:
        meshconfig.setGlobalMeshSliceAndStack(100)

    # load custom module to change material properties.
    if args.pygeom_optics_plugin:
        load_user_material_code(args.pygeom_optics_plugin)

    registry = core.construct(
        assemblies=args.assemblies.split(",") if args.assemblies else None,
        detail_level=args.detail,
        config=config,
        input_config_folder=args.input_raw_config_folder,
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
