# ruff: noqa: PLC0415

from __future__ import annotations

import jsonschema
import pytest
from dbetto import utils


@pytest.fixture(scope="module")
def default_config():
    from pygeoml1000 import config

    return config.resolve_config({})


def test_default_is_fully_resolved(default_config):
    """Resolving an empty config compiles the packaged raw configs and fills in the defaults."""
    assert set(default_config) == {"channelmap", "special_metadata", "detail", "enable_optical"}
    assert default_config["detail"] == "radiogenic"
    assert default_config["enable_optical"] is True
    assert len(default_config["channelmap"]) > 0
    assert set(default_config["special_metadata"]) >= {"hpge_string", "hpges", "fibers", "detail"}
    geds = [name for name, det in default_config["channelmap"].items() if det["system"] == "geds"]
    assert {default_config["channelmap"][name]["production"]["crystal"] for name in geds} == {"1"}


def test_resolve_is_unchanged(default_config):
    """A resolved config must survive being fed back in unchanged."""
    from pygeoml1000 import config

    assert config.resolve_config(default_config) == default_config


def test_round_trip_through_file(tmp_path, default_config):
    from pygeoml1000 import config

    out = tmp_path / "resolved.yaml"
    config.write_config({}, out)

    assert config.load_config(out) == default_config


def test_cli_arguments_take_precedence():
    from pygeoml1000 import config

    resolved = config.resolve_config({"detail": "radiogenic"}, detail="cosmogenic")
    assert resolved["detail"] == "cosmogenic"

    # ``None`` means "not specified on the command line", so the config file wins.
    resolved = config.resolve_config({"detail": "cosmogenic"}, detail=None)
    assert resolved["detail"] == "cosmogenic"


def test_raw_config_is_layered_over_the_defaults():
    """An inline raw config overrides single values, it does not replace whole files."""
    from pygeoml1000 import config

    raw = config.load_raw_config({"string": {"units": {"n": 4}}})

    assert raw["string"]["units"]["n"] == 4
    # everything else in string.yaml survives ...
    assert raw["string"]["units"]["l"] == 140.1
    assert raw["string"]["n_sipm_modules_per_string"] == 3
    # ... and so do the other raw config files.
    assert raw["array"]["radius_in_mm"] == 213.5


def test_raw_config_changes_the_compiled_output():
    from pygeoml1000 import config

    resolved = config.resolve_config({"raw_config": {"string": {"units": {"n": 4}}}})
    geds = [ch for ch in resolved["channelmap"].values() if ch["system"] == "geds"]

    assert len(geds) == 4 * len(resolved["special_metadata"]["hpge_string"])


def test_raw_config_from_folder(tmp_path):
    from pygeoml1000 import config

    folder = config.copy_raw_configs(tmp_path)
    utils.write_dict({"units": {"n": 4}, "n_sipm_modules_per_string": 3}, str(folder / "string.yaml"))

    resolved = config.resolve_config({"raw_config": str(folder)})
    geds = [ch for ch in resolved["channelmap"].values() if ch["system"] == "geds"]
    first_hpge = next(iter(resolved["special_metadata"]["hpges"]))

    assert len(geds) == 4 * len(resolved["special_metadata"]["hpge_string"])
    assert resolved["special_metadata"]["hpges"][first_hpge]["rodlength_in_mm"] == 140.1


def test_crystal_records_are_assigned_deterministically():
    from pygeoml1000 import config

    resolved = config.resolve_config(
        {
            "raw_config": {
                "string": {"units": {"n": 2}},
                "crystal": [{"name": "c1"}, {"name": "c2"}],
            }
        }
    )

    geds = sorted(name for name, det in resolved["channelmap"].items() if det["system"] == "geds")
    assigned = [resolved["channelmap"][name]["production"]["crystal"] for name in geds[:4]]

    assert assigned == ["c1", "c2", "c1", "c2"]


def test_hpge_records_are_assigned_deterministically():
    from pygeoml1000 import config

    resolved = config.resolve_config(
        {
            "raw_config": {
                "string": {"units": {"n": 2}},
                "hpge": [
                    {
                        "system": "geds",
                        "daq": {},
                        "location": {},
                        "production": {},
                        "additional_id": "c1",
                    },
                    {
                        "system": "geds",
                        "daq": {},
                        "location": {},
                        "production": {},
                        "additional_id": "c2",
                    },
                ],
            }
        }
    )

    geds = sorted(name for name, det in resolved["channelmap"].items() if det["system"] == "geds")
    assigned = [resolved["channelmap"][name]["additional_id"] for name in geds[:4]]

    assert assigned == ["c1", "c2", "c1", "c2"]


def test_missing_raw_config_folder_raises():
    from pygeoml1000 import config

    with pytest.raises(FileNotFoundError):
        config.resolve_config({"raw_config": "/nonexistent"})


@pytest.mark.parametrize(
    "bad_config",
    [
        {"detail": 3},
        {"sipm_efficiencies": {"S0101T": "not a number"}},
        {"metadata_timestamp": "yesterday"},
        {"assemblies": [1, 2]},
    ],
)
def test_schema_rejects(bad_config):
    from pygeoml1000 import config

    with pytest.raises(jsonschema.ValidationError):
        config.validate_config(bad_config)


def test_workflow_keys_are_accepted(default_config):
    """A legend-simflow geometry config must validate and build the same geometry.

    ``public_geom``/``metadata_timestamp`` come from the l200 vocabulary, ``executable`` is what
    simflow uses to pick the generator. None of them mean anything here.
    """
    from pygeoml1000 import config

    resolved = config.resolve_config(
        {
            "public_geom": True,
            "metadata_timestamp": "20230311T235840Z",
            "executable": "legend-pygeom-l1000",
        }
    )

    assert resolved == default_config


@pytest.mark.parametrize("enable_optical", [False, ["liquidargon"]])
def test_enable_optical_is_kept(enable_optical):
    """A non-default optical selection must survive resolution, so it round-trips."""
    from pygeoml1000 import config

    resolved = config.resolve_config({"enable_optical": enable_optical})

    assert resolved["enable_optical"] == enable_optical
    assert config.resolve_config(resolved) == resolved


@pytest.mark.parametrize(
    ("enable_optical", "expect_lar_optics"),
    [(None, True), (True, True), (False, False), (["liquidargon"], True), (["pen"], False)],
)
def test_construct_honours_enable_optical(enable_optical, expect_lar_optics):
    """Only the selected materials get their optical properties registered."""
    from pygeoml1000 import core

    config = {"assemblies": ["cryostat"]}
    if enable_optical is not None:
        config["enable_optical"] = enable_optical

    registry = core.construct(config)

    assert ("liquidargon_RINDEX" in registry.defineDict) == expect_lar_optics


def test_schema_is_not_loaded_as_raw_config():
    """The schema sits next to the raw configs, but is not one of them."""
    from pygeoml1000 import config

    assert config.schema_file().parent == config.raw_config_dir()
    assert "runtime_config_schema" not in config.load_raw_config()


@pytest.mark.parametrize("empty", [[], ""])
def test_empty_assembly_selection_keeps_the_preset(default_config, empty):
    """An empty selection must not be read as "build nothing"."""
    from pygeoml1000 import config

    resolved = config.resolve_config({"assemblies": empty})

    assert "assemblies" not in resolved
    assert config.effective_detail(resolved) == default_config["special_metadata"]["detail"]["radiogenic"]


def test_assemblies_set_operators(default_config):
    from pygeoml1000 import config

    detail = default_config["special_metadata"]["detail"]["radiogenic"]
    enabled = {system for system, level in detail.items() if level != "omit"}

    assert config.parse_assemblies(None, detail) is None
    assert config.parse_assemblies("cryostat,HPGe_dets", detail) == {"cryostat", "HPGe_dets"}
    assert config.parse_assemblies("+watertank", detail) == enabled | {"watertank"}
    assert config.parse_assemblies(["-fiber_curtain"], detail) == enabled - {"fiber_curtain"}


@pytest.mark.parametrize(
    "assemblies",
    [
        "+watertank,cryostat",  # mixing operators and plain names
        "not_an_assembly",
        "HPGe_dets",  # HPGe detectors need the cryostat
    ],
)
def test_invalid_assemblies_raise(default_config, assemblies):
    from pygeoml1000 import config

    with pytest.raises(ValueError, match="assemb"):
        config.parse_assemblies(assemblies, default_config["special_metadata"]["detail"]["radiogenic"])


def test_invalid_detail_level_raises():
    from pygeoml1000 import config

    with pytest.raises(ValueError, match="invalid detail level"):
        config.resolve_config({"detail": "not_a_preset"})


def test_effective_detail_applies_the_assembly_selection(default_config):
    from pygeoml1000 import config

    resolved = config.resolve_config(default_config, assemblies="cryostat,HPGe_dets")
    detail = config.effective_detail(resolved)

    assert detail["cryostat"] != "omit"
    assert detail["HPGe_dets"] != "omit"
    assert detail["fiber_curtain"] == "omit"

    # the selection must not leak back into the config it was derived from.
    assert resolved["special_metadata"]["detail"]["radiogenic"]["fiber_curtain"] != "omit"


def test_construct_does_not_mutate_its_config(default_config):
    """``construct`` used to switch assemblies to 'omit' in the caller's dict."""
    import copy

    from pygeoml1000 import core

    config_in = {**copy.deepcopy(default_config), "assemblies": ["cryostat"]}
    before = copy.deepcopy(config_in)

    core.construct(config_in)

    assert config_in == before


def test_copy_raw_configs(tmp_path):
    from pygeoml1000 import config

    folder = config.copy_raw_configs(tmp_path)

    assert folder == tmp_path / "configs"
    # every raw config is copied, and nothing else - notably not the schema.
    assert {f.stem for f in folder.iterdir()} == set(config.load_raw_config())
    assert not (folder / config.schema_file().name).exists()
