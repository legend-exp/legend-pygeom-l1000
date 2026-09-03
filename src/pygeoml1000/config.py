"""The runtime config: how a geometry is described, and how that description is resolved.

A geometry is built from two compiled objects, ``channelmap`` and
``special_metadata``. Three input schemes supply them, and a config selects a
scheme by the keys it sets::

    pre-compiled config     `pre_compiled_config`, or nothing at all
        |                   the shape of the setup, in configs/*.yaml
        |  compilation.compile_pre_compiled_config
        v
    compiled config         `channelmap` + `special_metadata`
        |                   every channel, one by one
        |  metadata.build_metadata_tree
        v
    generated metadata      `metadata`
                            a legend-metadata tree, which holds both objects

:func:`resolve_config` accepts all three and always returns the middle one, with
the defaults filled in. The more explicit scheme wins, and the generator warns
about every key it drops.
"""

from __future__ import annotations

import copy
import logging
from collections.abc import Collection
from importlib import resources
from pathlib import Path
from typing import Any

import jsonschema
from dbetto import utils
from pygeomtools.utils import load_dict_from_config

from . import compilation, metadata
from .utils import convert_to_plain_types, deep_merge, normalize_records

log = logging.getLogger(__name__)

DEFAULT_DETAIL = "radiogenic"
DEFAULT_ENABLE_OPTICAL = True
"""Optical properties are registered for every material unless the config says otherwise."""
_PRE_COMPILED_SUFFIXES = (".yaml", ".json")
#: substring marking a file in the configs folder that is not a pre-compiled config.
_NOT_PRE_COMPILED = "_schema"
#: keys consumed by :func:`resolve_config` itself, and hence absent from a resolved config.
_RESOLVED_KEYS = ("pre_compiled_config", "metadata")
#: keys accepted for interoperability with other generators, but without effect here.
_IGNORED_KEYS = ("public_geom", "metadata_timestamp", "executable")


def pre_compiled_config_dir() -> Path:
    """Directory holding the pre-compiled config files shipped with this package."""
    return Path(str(resources.files("pygeoml1000") / "configs"))


def schema_file() -> Path:
    """The JSON schema the config files are validated against."""
    return pre_compiled_config_dir() / "runtime_config_schema.yaml"


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
    """Resolve a config of any input scheme into a compiled one.

    The returned dict is itself a valid config file: it has ``channelmap`` and
    ``special_metadata`` filled in, ``assemblies`` expanded into an absolute list, and no
    ``pre_compiled_config`` left to compile. Resolving it again is a no-op.

    The module docstring shows the three schemes. This function reads them in
    order, most explicit first: :func:`_read_generated_metadata`, then the
    compiled objects the config gives, then :func:`_compile`.

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

    if "metadata" in config:
        config = _read_generated_metadata(config)

    pre_compiled, compiled = _compile(config)
    channelmap = load_dict_from_config(config, "channelmap", lambda: compiled[0])
    special_metadata = load_dict_from_config(config, "special_metadata", lambda: compiled[1])

    resolved = {k: v for k, v in config.items() if k not in _RESOLVED_KEYS}
    resolved["channelmap"] = convert_to_plain_types(channelmap)
    resolved["special_metadata"] = convert_to_plain_types(special_metadata)
    resolved["crystals"] = convert_to_plain_types(
        normalize_records(_catalog(config, pre_compiled, "crystals", "crystal"))
    )
    resolved["runs"] = convert_to_plain_types(_catalog(config, pre_compiled, "runs", "runs"))

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


def _read_generated_metadata(config: dict) -> dict:
    """The generated metadata scheme: read both compiled objects out of a tree.

    A tree holds everything a compiled config holds, so it wins over every other
    key. Returns a copy of ``config`` with the tree's contents merged in.
    """
    config = dict(config)

    for key in ("channelmap", "special_metadata", "pre_compiled_config"):
        if key in config:
            log.warning("'%s' is ignored because 'metadata' is given", key)
            del config[key]

    config.update(metadata.metadata_to_config(config["metadata"]))
    return config


def _compile(config: dict) -> tuple[dict | None, tuple[dict, dict]]:
    """The pre-compiled scheme: compile the configs into the two objects.

    Compiling is skipped when the config already gives both compiled objects.
    Returns ``(pre_compiled_configs, (channelmap, special_metadata))``, where the
    first element is ``None`` for a config that skipped the step.
    """
    if "channelmap" in config and "special_metadata" in config:
        if "pre_compiled_config" in config:
            log.warning(
                "'pre_compiled_config' is ignored because both 'channelmap' and 'special_metadata' are given"
            )
        return None, ({}, {})

    pre_compiled = load_pre_compiled_config(config.get("pre_compiled_config"))
    return pre_compiled, compilation.compile_pre_compiled_config(pre_compiled)


def _catalog(config: dict, pre_compiled: dict | None, key: str, pre_compiled_key: str) -> Any:
    """A catalog that travels in a resolved config, such as the crystals or the runs.

    A catalog does not describe the geometry, so a compiled config carries it
    unchanged. Only a config that has none falls back to the pre-compiled one.
    """
    if config.get(key) is not None:
        return config[key]

    if pre_compiled is None:
        # the geometry came compiled, so nothing was loaded yet
        pre_compiled = load_pre_compiled_config()
    return pre_compiled.get(pre_compiled_key)


def load_pre_compiled_config(pre_compiled_config: dict | str | None = None) -> dict:
    """Load the packaged pre-compiled configs, deep-merged with the user's overrides.

    ``pre_compiled_config`` is either an inline mapping (keyed by file name without its
    extension) or the path to a folder of such files. In both cases the packaged configs
    are used as the base, so only the values that actually change have to be given.
    """
    configs = _load_pre_compiled_config_dir(pre_compiled_config_dir())

    if isinstance(pre_compiled_config, str):
        pre_compiled_config = _load_pre_compiled_config_dir(Path(pre_compiled_config))
    if pre_compiled_config:
        configs = deep_merge(configs, pre_compiled_config)

    return configs


def _load_pre_compiled_config_dir(path: Path) -> dict:
    """Load every pre-compiled config file in ``path``, keyed by file name without the extension."""
    if not path.is_dir():
        msg = f"pre-compiled config folder {path} does not exist"
        raise FileNotFoundError(msg)

    return {f.stem: utils.load_dict(str(f)) for f in sorted(path.iterdir()) if _is_pre_compiled_config(f)}


def _is_pre_compiled_config(path: Path) -> bool:
    """Whether ``path`` is a pre-compiled config, and not e.g. the JSON schema next to them."""
    return path.is_file() and path.suffix in _PRE_COMPILED_SUFFIXES and _NOT_PRE_COMPILED not in path.stem


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


def write_metadata(config: dict, filename: str | Path) -> Path:
    """Write a stand-in ``legend-metadata`` tree for the geometry ``config`` describes.

    ``filename`` is a directory, or a ``.tar.gz`` archive if it ends in one. The
    archive is what a workflow unpacks into its metadata folder, and what
    ``metadata:`` in a geometry config points back at.

    Everything the tree is built from travels in the resolved config, including
    the crystal catalog and the runs. A config that came from a metadata tree
    therefore re-packs from that tree, and never falls back to the packaged
    catalogs.

    See :mod:`pygeoml1000.metadata` for the layout of the result.
    """
    return metadata.write_metadata(metadata.build_metadata_tree(resolve_config(config)), filename)


def copy_pre_compiled_configs(destination: str | Path) -> Path:
    """Copy the packaged pre-compiled configs into a ``configs`` folder below ``destination``.

    Returns the folder the files were written to.
    """
    destination = Path(destination) / "configs"
    destination.mkdir(parents=True, exist_ok=True)

    for item in sorted(pre_compiled_config_dir().iterdir()):
        if _is_pre_compiled_config(item):
            (destination / item.name).write_bytes(item.read_bytes())

    return destination
