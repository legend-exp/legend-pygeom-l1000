# ruff: noqa: PLC0415

from __future__ import annotations

import argparse
import logging

import dbetto
from pyg4ometry import config as meshconfig
from pygeomoptics.store import load_user_material_code
from pygeomtools import detectors, visualization, write_pygeom

from . import _version, core, manifest
from .config import (
    DEFAULT_DETAIL,
    copy_raw_configs,
    load_config,
    resolve_config,
    write_config,
    write_metadata,
)

log = logging.getLogger(__name__)


def dump_gdml_cli(argv: list[str] | None = None) -> None:
    args = _parse_cli_args(argv)

    logging.basicConfig()
    if args.verbose:
        logging.getLogger("pygeoml1000").setLevel(logging.DEBUG)
    if args.debug:
        logging.root.setLevel(logging.DEBUG)

    config = None
    if (
        args.write_config
        or args.write_metadata
        or args.filename is not None
        or args.visualize
        or args.write_manifest
    ):
        config = load_geometry_config(args)

    if args.dump_raw_configs:
        folder = copy_raw_configs(args.dump_raw_configs)
        log.info("copied raw config files to %s", folder)

    if args.write_config:
        log.info("writing resolved config to %s", args.write_config)
        write_config(config, args.write_config)

    if args.write_metadata:
        log.info("writing generated metadata to %s", args.write_metadata)
        write_metadata(config, args.write_metadata)

    if config is None or (args.filename is None and not args.visualize and not args.write_manifest):
        return

    vis_scene = {}
    if isinstance(args.visualize, str):
        vis_scene = dbetto.utils.load_dict(args.visualize)

    if vis_scene.get("fine_mesh", False) or args.check_overlaps or args.write_manifest:
        meshconfig.setGlobalMeshSliceAndStack(100)

    if args.pygeom_optics_plugin:
        load_user_material_code(args.pygeom_optics_plugin)

    registry = core.construct(config)

    if args.write_manifest:
        log.info("writing parts manifest to %s", args.write_manifest)
        manifest.write_manifest(
            registry,
            args.write_manifest,
            detail_level=config["detail"],
            assemblies=config.get("assemblies"),
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


def load_geometry_config(args: argparse.Namespace) -> dict:
    """Resolve the geometry config selected on the command line.

    Command line arguments take precedence over the config file, which takes precedence over the
    defaults.
    """
    return resolve_config(load_config(args.config), assemblies=args.assemblies, detail=args.detail)


def _parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
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
        "--config",
        action="store",
        help="""Select a config file (YAML or JSON) to read the geometry configuration from""",
    )
    geom_opts.add_argument(
        "--assemblies",
        action="store",
        help="""Comma-separated list of assemblies to generate in the output. Each entry can be
        prefixed by '+' or '-' to add to/remove from the assemblies enabled by the detail level,
        but either all entries carry an operator or none do.""",
    )
    geom_opts.add_argument(
        "--detail",
        action="store",
        help=f"""Select the detail level for the setup. (default: {DEFAULT_DETAIL})""",
    )

    # output options.
    out_opts = parser.add_argument_group("output options")
    out_opts.add_argument(
        "--write-manifest",
        action="store",
        help="""Filename to write a YAML parts manifest to, listing the material, the number of placements and the total mass of each part in the geometry""",
    )
    out_opts.add_argument(
        "--write-config",
        action="store",
        help="""Filename to write the resolved config to, i.e. the config with the raw configuration
        compiled into an explicit channelmap and special_metadata. The result can be edited by hand
        and fed back in via --config.""",
    )
    out_opts.add_argument(
        "--write-metadata",
        action="store",
        help="""Filename to write the detectors of this geometry to, as the 'datasets' and
        'hardware' parts of a legend-metadata tree. A folder, or a '.tar.gz' archive if the name
        ends in one. Nothing under 'simprod', 'dataprod' or 'jldataprod' is written.""",
    )
    out_opts.add_argument(
        "--dump-raw-configs",
        action="store",
        help="""Write a copy of the raw config files shipped with this package into a 'configs'
        folder below the given directory, as a starting point for a custom configuration.""",
    )
    parser.add_argument(
        "filename",
        default=None,
        nargs="?",
        help="""File name for the output GDML geometry.""",
    )

    args = parser.parse_args(argv)

    if (
        not args.visualize
        and args.filename is None
        and not args.write_manifest
        and not args.write_config
        and not args.write_metadata
        and not args.dump_raw_configs
    ):
        parser.error("no output file, no visualization, and no config output specified")
    if (args.vis_macro_file or args.det_macro_file) and args.filename is None:
        parser.error("writing macro file(s) without gdml file is not possible")

    return args
