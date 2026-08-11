"""Generation of a stand-in ``legend-metadata`` tree from a compiled geometry.

A LEGEND-1000 production has no metadata database, so this module writes one.
The tree uses the same layout as the real ``legend-metadata``.
:class:`legendmeta.LegendMetadata` and the
`legend-simflow <https://legend-simflow.readthedocs.io>`_ workflow therefore
read it in the usual way.

The tree goes into one tarball next to the geometry config.
:func:`metadata_to_config` rebuilds the geometry from that tarball alone. Two
files thus make a production reproducible.

This module does not write ``simprod/config/``. That folder holds the production
settings, and the user writes those.

Layout
------

The template supplies the two ``validity.yaml`` files, ``runinfo.yaml`` and
``runlists.yaml``. It is the single source of truth for run and validity naming.
This module derives all other files from the compiled channel map::

    datasets/runinfo.yaml
    datasets/runlists.yaml
    datasets/statuses/validity.yaml
    datasets/statuses/<name>.yaml                        one entry per channel
    hardware/configuration/channelmaps/validity.yaml
    hardware/configuration/channelmaps/<name>.yaml       all but the detector keys
    hardware/detectors/germanium/diodes/<DET>.yaml       one per `geds` channel
    hardware/detectors/germanium/crystals/<XTAL>.yaml    one per distinct crystal
    special_metadata.yaml                                the compiled special metadata

The ``apply:`` entries of the matching ``validity.yaml`` set ``<name>``. Nothing
reads these names. A workflow selects a file by comparing its ``valid_from``
with the start key of a run, so the names can say anything.

The real ``legend-metadata`` has no ``special_metadata.yaml``. This file makes
the tarball sufficient to rebuild the geometry. It sits at the root of the tree,
where it reads back as ``metadata.special_metadata``.

One channel in three files
--------------------------

:meth:`legendmeta.LegendMetadata.channelmap` builds a channel in three steps. It
reads ``hardware/configuration/channelmaps`` first. It then merges
``hardware/detectors/germanium/diodes/<DET>.yaml`` over the channel with ``|=``.
Last, it attaches ``datasets/statuses`` as ``analysis``.

The diode file wins this merge. It therefore carries none of ``system``, ``daq``
or ``location``. Any of these keys would replace the raw ID and the position of
the channel. :func:`split_channel` keeps the parts disjoint.
"""

from __future__ import annotations

import copy
import gzip
import io
import logging
import tarfile
import tempfile
from importlib import resources
from pathlib import Path
from typing import Any

from dbetto import utils

log = logging.getLogger(__name__)

SPECIAL_METADATA_FILE = "special_metadata.yaml"
TEMPLATE_NAME = "template_metadata.tar.gz"

STATUSES_DIR = "datasets/statuses"
CHANNELMAPS_DIR = "hardware/configuration/channelmaps"
DIODES_DIR = "hardware/detectors/germanium/diodes"
CRYSTALS_DIR = "hardware/detectors/germanium/crystals"
VALIDITY_FILE = "validity.yaml"

TYPE_IDS = {"icpc": "V"}

DIODE_KEYS = ("name", "type", "production", "geometry", "characterization")

DEFAULT_STATUS = {"reason": "", "usability": "on", "processable": True}
DEFAULT_PSD_STATUS = {"psd": {"status": {"low_aoe": "valid"}}}
DEFAULT_SLICE_STATUS = "valid"

_SUFFIXES = tuple(e for exts in utils.__file_extensions__.values() for e in exts)


# ----------------------------------------------------------------------------
# reading and writing trees
# ----------------------------------------------------------------------------


def load_tree(path: str | Path) -> dict[str, Any]:
    """Read a metadata tree into ``{relative path: contents}``.

    ``path`` is a directory or a ``.tar.gz`` archive. Every file goes through
    :func:`dbetto.utils.load_dict`, the reader that legend-simflow also uses. An
    archive first goes into a temporary directory, because that reader takes a
    path.
    """
    path = Path(path)

    if path.is_file():
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(path, "r:*") as tar:
                tar.extractall(tmp, filter="data")
            return load_tree(tmp)

    return {
        str(f.relative_to(path)): utils.load_dict(str(f))
        for f in sorted(path.rglob("*"))
        if f.is_file() and f.suffix in _SUFFIXES
    }


def load_template(path: str | Path | None = None) -> dict[str, Any]:
    """Read the metadata template, defaulting to the one shipped with the package."""
    if path is None:
        path = Path(str(resources.files("pygeoml1000") / "configs" / TEMPLATE_NAME))
    return load_tree(path)


def write_metadata(tree: dict[str, Any], dest: str | Path) -> Path:
    """Write a generated tree to a directory, or to a ``.tar.gz`` archive.

    Every file goes through :func:`dbetto.utils.write_dict`.
    Two runs on the same tree give the same archive. A regeneration of an
    unchanged tarball thus leaves the committed file alone.
    """
    dest = Path(dest)

    if not str(dest).endswith((".tar.gz", ".tgz")):
        _write_dir(tree, dest)
        return dest

    with tempfile.TemporaryDirectory() as tmp:
        _write_dir(tree, Path(tmp))

        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            for name in sorted(tree):
                data = (Path(tmp) / name).read_bytes()
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(gzip.compress(buffer.getvalue(), mtime=0))
    return dest


def _write_dir(tree: dict[str, Any], root: Path) -> None:
    for name in sorted(tree):
        out = root / name
        out.parent.mkdir(parents=True, exist_ok=True)
        utils.write_dict(tree[name], str(out))


# ----------------------------------------------------------------------------
# building the tree
# ----------------------------------------------------------------------------


def crystal_name(diode: dict) -> str:
    """Name of the crystal that a diode comes from.

    This mirrors ``legendsimflow.metadata.get_crystal_name``. A workflow looks
    for a file with this name under ``hardware/detectors/germanium/crystals``.
    """
    return (
        TYPE_IDS[diode["type"]]
        + format(diode["production"]["order"], "02d")
        + str(diode["production"]["crystal"])
    )


def split_channel(entry: dict) -> tuple[dict, dict | None]:
    """Split one channel map entry into a channel part and a detector part.

    Returns ``(channel, diode)``. ``diode`` is ``None`` for a channel that is not
    a germanium detector. The two parts share only ``name``.

    The diode takes a fixed set of keys, because it must not carry ``system``,
    ``daq`` or ``location``. The channel takes everything else, and not a fixed
    set of its own. A raw config can add a key to a detector template, such as
    the ``voltage`` and ``electronics`` blocks of a real channel map, and that
    key must reach the tree instead of disappearing here.
    """
    if entry.get("system") != "geds":
        return copy.deepcopy(entry), None

    diode = {key: copy.deepcopy(entry[key]) for key in DIODE_KEYS}
    channel = {k: copy.deepcopy(v) for k, v in entry.items() if k == "name" or k not in DIODE_KEYS}
    return channel, diode


def build_channelmap(channelmap: dict) -> dict:
    """The channel map for ``hardware/configuration/channelmaps``."""
    return {name: split_channel(entry)[0] for name, entry in channelmap.items()}


def build_diodes(channelmap: dict) -> dict[str, dict]:
    """One detector database entry for each germanium channel, keyed by name."""
    diodes = {}
    for name, entry in channelmap.items():
        diode = split_channel(entry)[1]
        if diode is not None:
            diodes[name] = diode
    return diodes


def build_statuses(channelmap: dict) -> dict:
    """The analysis status of each channel.

    Each channel gets an entry. ``legendsimflow.aggregate.gen_hpge_modeling_status``
    reads ``analysis.usability`` when it builds the DAG.

    Every channel gets the same status. To turn one channel off, edit the
    generated file. See :data:`DEFAULT_STATUS`.
    """
    out = {}
    for name, entry in channelmap.items():
        out[name] = copy.deepcopy(DEFAULT_STATUS)
        if entry.get("system") == "geds":
            out[name] |= copy.deepcopy(DEFAULT_PSD_STATUS)

    return out


def build_crystals(channelmap: dict, crystals: list[dict]) -> dict[str, dict]:
    """One crystal database entry for each crystal that the channel map uses."""
    catalog = {str(record["name"]): record for record in crystals}

    out: dict[str, dict] = {}
    for diode in build_diodes(channelmap).values():
        production = diode["production"]
        key = crystal_name(diode)

        if key not in out:
            out[key] = copy.deepcopy(catalog[str(production["crystal"])])
            out[key]["name"] = str(production["crystal"])
            out[key]["order"] = production["order"]

        slices = out[key].setdefault("slices", {})
        slices[production["slice"]].setdefault("status", DEFAULT_SLICE_STATUS)

    return out


def crystals_from_tree(tree: dict[str, Any]) -> list[dict]:
    """The crystal catalog of an existing tree, in the shape that :func:`build_crystals` takes.

    A re-pack of a tree thus uses the crystals of that tree, and not the catalog
    of this package.
    """
    prefix = f"{CRYSTALS_DIR}/"
    return [content for name, content in sorted(tree.items()) if name.startswith(prefix)]


def build_metadata_tree(config: dict, template: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a complete metadata tree from a compiled geometry.

    Parameters
    ----------
    config
        a resolved config, as :func:`pygeoml1000.config.resolve_config` returns.
        Only ``channelmap``, ``special_metadata`` and ``crystals`` are read.
    template
        everything that is not derived from the geometry. Defaults to the
        template shipped with the package.
    """
    channelmap = config["channelmap"]
    tree = dict(load_template() if template is None else template)

    for directory, content in (
        (CHANNELMAPS_DIR, build_channelmap(channelmap)),
        (STATUSES_DIR, build_statuses(channelmap)),
    ):
        for name in _applied_names(tree, directory):
            tree[f"{directory}/{name}"] = content

    for name, diode in build_diodes(channelmap).items():
        tree[f"{DIODES_DIR}/{name}.yaml"] = diode

    for name, crystal in build_crystals(channelmap, config["crystals"]).items():
        tree[f"{CRYSTALS_DIR}/{name}.yaml"] = crystal

    tree[SPECIAL_METADATA_FILE] = config["special_metadata"]

    return tree


def _applied_names(tree: dict[str, Any], directory: str) -> list[str]:
    """The file names in the ``apply`` entries of the validity file of a directory."""
    path = f"{directory}/{VALIDITY_FILE}"

    names: list[str] = []
    for entry in tree[path] or []:
        applied = entry.get("apply", [])
        for name in [applied] if isinstance(applied, str) else applied:
            if name not in names:
                names.append(name)

    return names


# ----------------------------------------------------------------------------
# reading a tree back into a geometry config
# ----------------------------------------------------------------------------


def metadata_to_config(path: str | Path) -> dict:
    """Rebuild the compiled geometry inputs from a generated metadata tree.

    This is the inverse of :func:`build_metadata_tree`: it merges the channel map
    back together from the three files it was split over, so that a geometry can
    be rebuilt from the tarball alone.

    This module reads the tree with plain file access, and not through
    :class:`legendmeta.LegendMetadata`. That class clones ``legend-metadata``
    over SSH for a path that does not exist yet. It also refuses to resolve
    validity on a tree that is not a Git repository.

    Returns the three keys that :func:`build_metadata_tree` reads back, so a
    tree re-packs from its own contents and never falls back to the catalog of
    this package. The channel map is the hardware one. It has no ``analysis``
    block, unlike the map that :meth:`legendmeta.LegendMetadata.channelmap`
    returns.
    """
    tree = load_tree(path)

    channelmap: dict[str, dict] = {}
    for name in _applied_names(tree, CHANNELMAPS_DIR):
        key = f"{CHANNELMAPS_DIR}/{name}"
        # a later file patches an earlier one, as the `append` validity mode of
        # dbetto does
        channelmap.update(tree[key] or {})

    for name, entry in channelmap.items():
        diode = tree.get(f"{DIODES_DIR}/{name}.yaml")
        if diode is not None:
            # the diode wins, exactly as LegendMetadata.channelmap merges it
            entry.update(diode or {})

    return {
        "channelmap": channelmap,
        "special_metadata": tree[SPECIAL_METADATA_FILE],
        "crystals": crystals_from_tree(tree),
    }
