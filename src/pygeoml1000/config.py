from __future__ import annotations

import copy
import logging
from collections.abc import Collection
from importlib import resources
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np
from dbetto import utils
from pygeomtools.utils import load_dict_from_config

log = logging.getLogger(__name__)

DEFAULT_DETAIL = "radiogenic"
DEFAULT_ENABLE_OPTICAL = True
"""Optical properties are registered for every material unless the config says otherwise."""
_RAW_CONFIG_SUFFIXES = (".yaml", ".json")
#: substring marking a file in the configs folder that is not raw configuration.
_NOT_RAW_CONFIG = "_schema"
#: keys consumed by :func:`resolve_config` itself, and hence absent from a resolved config.
_RESOLVED_KEYS = ("raw_config",)
#: keys accepted for interoperability with other generators, but without effect here.
_IGNORED_KEYS = ("public_geom", "metadata_timestamp", "executable")


def raw_config_dir() -> Path:
    """Directory holding the raw config files shipped with this package."""
    return Path(str(resources.files("pygeoml1000") / "configs"))


def schema_file() -> Path:
    """The JSON schema the config files are validated against."""
    return raw_config_dir() / "runtime_config_schema.yaml"


def load_config(filename: str | Path | None) -> dict:
    """Load a config file (YAML or JSON) and validate it against the schema."""
    if filename is None:
        return {}

    config = utils.load_dict(str(filename))
    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    """Validate a config against the packaged JSON schema.

    The schema does not set ``additionalProperties: false``, so unknown keys pass through
    unchecked. Only the values of the keys it knows about are validated.

    Raises
    ------
    jsonschema.ValidationError
        if a known key holds a value of the wrong type or shape.
    """
    jsonschema.validate(instance=config, schema=utils.load_dict(str(schema_file())))


def resolve_config(config: dict | None = None, **cli_overrides: Any) -> dict:
    """Resolve a config into one that explicitly contains the compiled geometry inputs.

    The returned dict is itself a valid config file: it has ``channelmap`` and
    ``special_metadata`` filled in, ``assemblies`` expanded into an absolute list, and no
    ``raw_config`` left to compile. Resolving it again is a no-op.

    Parameters
    ----------
    config
        the config as read from file (or constructed programmatically).
    cli_overrides
        values that take precedence over the config file, e.g. ``detail=...`` or
        ``assemblies=...``. ``None`` means "not specified on the command line".
    """
    config = dict(config or {})
    validate_config(config)

    for key, value in cli_overrides.items():
        if value is not None:
            config[key] = value

    for key in _IGNORED_KEYS:
        if key in config:
            log.warning("'%s' has no effect on the LEGEND-1000 geometry, ignoring it", key)
            del config[key]

    is_compiled = "channelmap" in config and "special_metadata" in config
    if is_compiled and "raw_config" in config:
        log.warning("'raw_config' is ignored because both 'channelmap' and 'special_metadata' are given")

    # compiling is only needed for the objects that are not given already.
    compiled = ({}, {}) if is_compiled else generate_dummy_metadata(load_raw_config(config.get("raw_config")))
    channelmap = load_dict_from_config(config, "channelmap", lambda: compiled[0])
    special_metadata = load_dict_from_config(config, "special_metadata", lambda: compiled[1])

    resolved = {k: v for k, v in config.items() if k not in _RESOLVED_KEYS}
    resolved["channelmap"] = convert_to_plain_types(channelmap)
    resolved["special_metadata"] = convert_to_plain_types(special_metadata)

    detail_level = config.get("detail", DEFAULT_DETAIL)
    if detail_level not in special_metadata.get("detail", {}):
        msg = (
            f"invalid detail level '{detail_level}', "
            f"available: {', '.join(sorted(special_metadata.get('detail', {})))}"
        )
        raise ValueError(msg)
    resolved["detail"] = detail_level

    resolved["enable_optical"] = config.get("enable_optical", DEFAULT_ENABLE_OPTICAL)

    assemblies = parse_assemblies(config.get("assemblies"), special_metadata["detail"][detail_level])
    if assemblies is None:
        resolved.pop("assemblies", None)
    else:
        resolved["assemblies"] = sorted(assemblies)

    return resolved


def load_raw_config(raw_config: dict | str | None = None) -> dict:
    """Load the packaged raw configs, deep-merged with the user's overrides.

    ``raw_config`` is either an inline mapping (keyed by raw config file name without its
    extension) or the path to a folder of raw config files. In both cases the packaged configs
    are used as the base, so only the values that actually change have to be given.
    """
    configs = _load_raw_config_dir(raw_config_dir())

    if isinstance(raw_config, str):
        raw_config = _load_raw_config_dir(Path(raw_config))
    if raw_config:
        configs = _deep_merge(configs, raw_config)

    return configs


def _load_raw_config_dir(path: Path) -> dict:
    """Load every raw config file in ``path``, keyed by file name without the extension."""
    if not path.is_dir():
        msg = f"raw config folder {path} does not exist"
        raise FileNotFoundError(msg)

    return {f.stem: utils.load_dict(str(f)) for f in sorted(path.iterdir()) if _is_raw_config(f)}


def _is_raw_config(path: Path) -> bool:
    """Whether ``path`` is a raw config file, and not e.g. the JSON schema next to them."""
    return path.is_file() and path.suffix in _RAW_CONFIG_SUFFIXES and _NOT_RAW_CONFIG not in path.stem


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` into a copy of ``base``."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def parse_assemblies(arg: str | Collection[str] | None, detail: dict) -> set[str] | None:
    """Parse the assembly selection into an absolute set of assembly names.

    Parameters
    ----------
    arg
        a comma-separated string or a collection of assembly names. Entries can be prefixed by
        the set operators ``+`` or ``-`` to add to/remove from the set of assemblies enabled by
        the detail preset, but either all entries carry an operator or none do. ``None`` (or an
        empty selection) leaves the detail preset untouched.
    detail
        the selected detail preset, i.e. a mapping of assembly name to detail level.
    """
    if arg is None:
        return None

    parts = [a.strip() for a in arg.split(",")] if isinstance(arg, str) else list(arg)
    parts = [a for a in parts if a != ""]
    if not parts:
        return None

    with_no_op = [a[0] not in ("+", "-") for a in parts]
    if any(with_no_op) and not all(with_no_op):
        msg = "either all or no assemblies can be prefixed by the operators '+' or '-'"
        raise ValueError(msg)

    if not any(with_no_op):  # all have operators
        assemblies = {system for system, level in detail.items() if level != "omit"}
        for part in parts:
            if part[0] == "-":
                assemblies -= {part[1:]}
            else:
                assemblies |= {part[1:]}
    else:
        assemblies = set(parts)

    unknown = assemblies - set(detail)
    if unknown != set():
        msg = f"invalid geometrical assembly specified: {', '.join(sorted(unknown))}"
        raise ValueError(msg)

    if "cryostat" not in assemblies and {"HPGe_dets", "fiber_curtain"} & assemblies:
        msg = (
            "invalid geometrical assembly specified. Cryostat must be included if HPGe_dets or "
            "fiber_curtain are included"
        )
        raise ValueError(msg)

    return assemblies


def effective_detail(config: dict) -> dict:
    """The detail level of each assembly, after applying the assembly selection.

    Assemblies that are not selected are switched to ``omit``. Selected assemblies that the
    preset omits are switched to ``simple``.
    """
    detail = copy.deepcopy(config["special_metadata"]["detail"][config["detail"]])

    assemblies = config.get("assemblies")
    if assemblies is None:
        return detail

    for system in detail:
        if system not in assemblies:
            detail[system] = "omit"
    for system in assemblies:
        if detail[system] == "omit":
            detail[system] = "simple"

    return detail


def write_config(config: dict, filename: str | Path) -> None:
    """Write a resolved config to a YAML/JSON file that can be fed back in via ``--config``."""
    utils.write_dict(resolve_config(config), str(filename))


def copy_raw_configs(destination: str | Path) -> Path:
    """Copy the packaged raw config files into a ``configs`` folder below ``destination``.

    Returns the folder the files were written to.
    """
    destination = Path(destination) / "configs"
    destination.mkdir(parents=True, exist_ok=True)

    for item in sorted(raw_config_dir().iterdir()):
        if _is_raw_config(item):
            (destination / item.name).write_bytes(item.read_bytes())

    return destination


# ----------------------------------------------------------------------------
# compilation of the raw configuration into channelmap and special_metadata, previously in config_compilation.py
# ----------------------------------------------------------------------------


def calculate_and_place_pmts(channelmap: dict, configs: dict, rawid_start: int = 6000) -> None:
    from . import watertank  # noqa: PLC0415

    # Floor PMTs are pretty trivial to place
    rawid = rawid_start
    for row in configs["pmts_pos"]["floor"].values():
        row_index = row["id"]
        pmts_in_row = row["n"]
        radius = row["r"]

        for i in range(pmts_in_row):
            name = f"PMT0{row_index}{i + 1:02d}"
            x = radius * np.cos(np.radians(360 / pmts_in_row * i))
            y = radius * np.sin(np.radians(360 / pmts_in_row * i))
            z = 0.0

            # If the PMT is outside of the pit move it up.
            if radius > watertank.tank_pit_radius:
                z = watertank.tank_pit_height

            channelmap[name] = copy.deepcopy(configs["pmts"])
            channelmap[name]["daq"]["rawid"] = rawid
            rawid += 1
            channelmap[name]["name"] = name
            channelmap[name]["location"] = {"name": "floor", "x": x, "y": y, "z": z}
            channelmap[name]["location"]["direction"] = {"nx": 0, "ny": 0, "nz": 1}

    # The wall PMTs require some polygon math
    faces = configs["pmts_pos"]["tyvek"]["faces"]
    # Geant4 uses r as inscribe radius, but we need the circumradius
    radius = configs["pmts_pos"]["tyvek"]["r"] / np.cos(np.pi / faces)

    # Compute vertices of the polygon
    vertices = [
        (radius * np.cos(2 * np.pi * i / faces), radius * np.sin(2 * np.pi * i / faces)) for i in range(faces)
    ]
    for row in configs["pmts_pos"]["wall"].values():
        row_index = row["id"]
        pmts_in_row = row["n"]
        z = row["z"]

        # Distribute detectors evenly across faces
        detectors_per_face = pmts_in_row // faces  # How many detectors per face (integer division)
        extra_detectors = pmts_in_row % faces  # Remaining detectors to distribute
        pmt_id = 0

        # Now some crazy algorithm to distribute the extra detectors homogeneously
        # Invented by Lorenz Gebler
        m = extra_detectors  # short variable names to make the code more readable
        n = faces
        # Try splitting the polygon faces in repetitive cells
        scl = n // m  # shortest cell length
        sc = [0] * scl  # shortest cell
        sc[0] = 1  # Set the first element to 1
        extra_detectors_per_face = sc * m
        # In case we cannot split the polygon in equal cells
        if n % m != 0:
            k = n - len(extra_detectors_per_face)
            sclk = m // k
            sck = sc * sclk + [0]
            extra_detectors_per_face = sck * k + sc * (m - k)
        # We need to truncate the list as somehow it creates too big cells
        extra_detectors_per_face = extra_detectors_per_face[:n]

        for i in range(faces):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % faces]  # Wrap around

            # Compute face normal for PMT orientation
            edge_x = x2 - x1
            edge_y = y2 - y1
            normal_x = edge_y
            normal_y = -edge_x

            # Normalize the normal vector
            norm_length = np.sqrt(normal_x**2 + normal_y**2)
            normal_x /= norm_length
            normal_y /= norm_length
            normal_z = 0

            # Compute the number of detectors on this face, permutate the extras by the row index
            num_detectors_this_face = detectors_per_face + extra_detectors_per_face[(i + row_index) % faces]

            for j in range(num_detectors_this_face):
                name = f"PMT{row_index + 10}{pmt_id + 1:02d}"
                pmt_id += 1
                # Interpolate position along the face
                t = (j + 1) / (num_detectors_this_face + 1)  # Normalized position (avoid exact endpoints)
                x = x1 * (1 - t) + x2 * t
                y = y1 * (1 - t) + y2 * t

                channelmap[name] = copy.deepcopy(configs["pmts"])
                channelmap[name]["daq"]["rawid"] = rawid
                rawid += 1
                channelmap[name]["name"] = name
                channelmap[name]["location"] = {"name": "wall", "x": x, "y": y, "z": z}
                channelmap[name]["location"]["direction"] = {"nx": normal_x, "ny": normal_y, "nz": normal_z}

        # Check that all PMTs are placed. We do not totally trust the distribution algorithm
        if pmt_id != pmts_in_row:
            msg = (
                "Not all PMTs were placed. Check the distribution algorithm. PMTs placed: "
                + str(pmt_id)
                + " PMTs to place: "
                + str(pmts_in_row)
            )
            raise ValueError(msg)


def generate_special_metadata(string_idx: list, hpge_names: list, configs: dict) -> dict:
    """Generate special_metadata.yaml file."""

    special_output = {}

    special_output["hpge_string"] = {
        f"{string_idx[i][j] + 1}": {
            "center": {
                "x_in_mm": configs["array"]["center"]["x_in_mm"][i],
                "y_in_mm": configs["array"]["center"]["y_in_mm"][i],
            },
            "angle_in_deg": configs["array"]["angle_in_deg"][j],
            "radius_in_mm": configs["array"]["radius_in_mm"],
            "rod_radius_in_mm": configs["string"]["copper_rods"]["r_offset_from_center"],
        }
        for i, j in np.ndindex(string_idx.shape)
    }

    special_output["hpges"] = {
        f"{name}": {"rodlength_in_mm": configs["string"]["units"]["l"], "baseplate": "xlarge"}
        for name in hpge_names
    }

    special_output["fibers"] = {
        f"S{string + 1:02d}{n + 1:02d}": {
            "name": f"S{string + 1:02d}{n + 1:02d}",
            "type": "single_string",
            "geometry": {"tpb": {"thickness_in_nm": 1093}},
            "location": {
                "x": float(
                    configs["array"]["center"]["x_in_mm"][string // len(configs["array"]["angle_in_deg"])]
                    + configs["array"]["radius_in_mm"]
                    * np.cos(
                        np.radians(
                            configs["array"]["angle_in_deg"][string % len(configs["array"]["angle_in_deg"])]
                        )
                    )
                ),
                "y": float(
                    configs["array"]["center"]["y_in_mm"][string // len(configs["array"]["angle_in_deg"])]
                    - configs["array"]["radius_in_mm"]
                    * np.sin(
                        np.radians(
                            configs["array"]["angle_in_deg"][string % len(configs["array"]["angle_in_deg"])]
                        )
                    )
                ),
                "module_num": n,
            },
        }
        for string in string_idx.flatten()
        for n in range(configs["string"]["n_sipm_modules_per_string"])
    }

    special_output["calibration"] = {}

    special_output["watertank_instrumentation"] = {
        "tyvek": {
            "r": configs["pmts_pos"]["tyvek"]["r"],
            "faces": configs["pmts_pos"]["tyvek"]["faces"],
        },
    }

    special_output["detail"] = configs["detail"]

    return special_output


def generate_channelmap(
    string_idx: list,
    hpge_names: list,
    hpge_rawid: list,
    configs: dict,
    unit_divisor: int = 100,
) -> dict:
    """Generate channelmap.json file."""

    channelmap = {}
    for name, rawid in zip(hpge_names, hpge_rawid, strict=True):
        channelmap[name] = copy.deepcopy(configs["hpge"])
        channelmap[name]["name"] = name
        channelmap[name]["daq"]["rawid"] = rawid
        channelmap[name]["location"]["string"] = rawid // unit_divisor
        channelmap[name]["location"]["position"] = rawid % unit_divisor

    max_hpge_rawid = int(max(hpge_rawid)) if len(hpge_rawid) > 0 else 0
    rawid = sipm_rawid_start = max(5000, _round_up(max_hpge_rawid + 1, 1000))
    for string in string_idx.flatten():
        for n in range(configs["string"]["n_sipm_modules_per_string"]):
            name = f"S{string + 1:02d}{n + 1:02d}T"
            channelmap[name] = copy.deepcopy(configs["sipm"])
            channelmap[name]["name"] = name
            channelmap[name]["location"]["fiber"] = name[:-1]
            channelmap[name]["location"]["position"] = "top"
            channelmap[name]["location"]["barrel"] = string + 1
            channelmap[name]["daq"]["rawid"] = rawid
            rawid += 1

        for n in range(configs["string"]["n_sipm_modules_per_string"]):
            name = f"S{string + 1:02d}{n + 1:02d}B"
            channelmap[name] = copy.deepcopy(configs["sipm"])
            channelmap[name]["name"] = name
            channelmap[name]["location"]["fiber"] = name[:-1]
            channelmap[name]["location"]["position"] = "bottom"
            channelmap[name]["location"]["barrel"] = string + 1
            channelmap[name]["daq"]["rawid"] = rawid
            rawid += 1

    pmt_rawid_start = max(6000, _round_up(rawid, 1000))
    if sipm_rawid_start != 5000 or pmt_rawid_start != 6000:
        log.info(
            "array too large for the default raw ID blocks, using %d for SiPMs and %d for PMTs",
            sipm_rawid_start,
            pmt_rawid_start,
        )
    calculate_and_place_pmts(channelmap, configs, rawid_start=pmt_rawid_start)

    return channelmap


def _round_up(value: int, multiple: int) -> int:
    """Round ``value`` up to the next integer multiple of ``multiple``."""
    return (value // multiple) * multiple


def convert_to_plain_types(obj):
    """Convert numpy types and dict subclasses to plain Python types, recursively."""
    if isinstance(obj, dict):
        return {str(key): convert_to_plain_types(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_to_plain_types(item) for item in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.str_):
        return str(obj)
    return obj


def generate_dummy_metadata(configs: dict) -> tuple[dict, dict]:
    """Compile the raw configuration into the two objects the geometry is built from.

    Parameters
    ----------
    configs
        the raw configuration, keyed by raw config file name without its extension. Use
        :func:`pygeoml1000.config.load_raw_config` to obtain it.

    Returns
    -------
    tuple
        ``(channelmap, special_metadata)``
    """
    string_idx = np.arange(
        len(configs["array"]["center"]["x_in_mm"]) * len(configs["array"]["angle_in_deg"])
    ).reshape(len(configs["array"]["center"]["x_in_mm"]), len(configs["array"]["angle_in_deg"]))

    n_units = configs["string"]["units"]["n"]

    string_width = max(2, len(str(string_idx.size)))
    unit_width = max(2, len(str(n_units)))

    hpge_names, hpge_rawid = [], []
    for i in range(string_idx.size):
        for j in range(n_units):
            hpge_names.append(f"V{i + 1:0{string_width}d}{j + 1:0{unit_width}d}")
            hpge_rawid.append((i + 1) * 10**unit_width + j + 1)
    hpge_names = np.array(hpge_names)
    hpge_rawid = np.array(hpge_rawid)

    special_metadata = generate_special_metadata(string_idx, hpge_names, configs)
    channelmap = generate_channelmap(string_idx, hpge_names, hpge_rawid, configs, unit_divisor=10**unit_width)

    return convert_to_plain_types(channelmap), convert_to_plain_types(special_metadata)
