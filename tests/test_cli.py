# ruff: noqa: PLC0415

from __future__ import annotations

import pytest
from dbetto import utils


def test_no_output_requested_errors():
    from pygeoml1000 import cli

    with pytest.raises(SystemExit):
        cli.dump_gdml_cli([])


def test_write_config_only(tmp_path):
    """Writing the config must not build the geometry."""
    from pygeoml1000 import cli, config

    out = tmp_path / "resolved.yaml"
    cli.dump_gdml_cli(["--write-config", str(out)])

    assert config.load_config(out) == config.resolve_config({})


def test_dump_raw_configs(tmp_path):
    from pygeoml1000 import cli, config

    cli.dump_gdml_cli(["--dump-raw-configs", str(tmp_path)])

    assert (tmp_path / "configs" / "string.yaml").exists()
    assert utils.load_dict(str(tmp_path / "configs" / "string.yaml")) == config.load_raw_config()["string"]


def test_cli_args_override_the_config_file(tmp_path):
    from pygeoml1000 import cli

    config_file = tmp_path / "geom-config.yaml"
    utils.write_dict({"detail": "radiogenic", "assemblies": ["cryostat"]}, str(config_file))

    args = cli._parse_cli_args(
        ["--config", str(config_file), "--detail", "cosmogenic", "--assemblies", "watertank", "out.gdml"]
    )
    config = cli.load_geometry_config(args)

    assert config["detail"] == "cosmogenic"
    assert config["assemblies"] == ["watertank"]


def test_build_from_config_file(tmp_path):
    """The contract legend-simflow relies on: config file in, GDML out."""
    from pyg4ometry import gdml

    from pygeoml1000 import cli

    config_file = tmp_path / "geom-config.yaml"
    gdml_file = tmp_path / "l1000.gdml"
    utils.write_dict(
        {"assemblies": ["cryostat", "HPGe_dets"], "raw_config": {"string": {"units": {"n": 1}}}},
        str(config_file),
    )

    cli.dump_gdml_cli(["--config", str(config_file), str(gdml_file)])

    assert gdml_file.exists()
    registry = gdml.Reader(gdml_file).getRegistry()
    assert len(registry.physicalVolumeDict) > 0
