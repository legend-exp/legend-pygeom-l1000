# ruff: noqa: PLC0415

from __future__ import annotations

import pytest

TYPE_IDS = {"icpc": "V"}


def crystal_name(diode: dict) -> str:
    """Name of the crystal a diode was cut from.

    Mirrors ``legendsimflow.metadata.get_crystal_name`` exactly. Changing this
    changes which file the workflow looks for under
    ``hardware/detectors/germanium/crystals``.
    """
    production = diode["production"]
    return TYPE_IDS[diode["type"]] + format(production["order"], "02d") + production["crystal"]


@pytest.fixture(scope="module")
def default_channelmap():
    from pygeoml1000 import config

    return config.resolve_config({})["channelmap"]


@pytest.fixture(scope="module")
def default_geds(default_channelmap):
    return {name: det for name, det in default_channelmap.items() if det["system"] == "geds"}


@pytest.fixture(scope="module")
def default_crystals():
    from pygeoml1000 import config

    return config.load_raw_config()["crystal"]


# ----------------------------------------------------------------------------
# contract with legend-simflow
#
# Every assertion below stands for a field legend-simflow reads out of the
# generated metadata. They fail here, loudly, instead of degrading silently in
# a production: a missing FCCD only warns, a missing slice status only flags
# every simulated hit invalid, and a renamed `l200_site` only makes every
# detector non-modelable.
# ----------------------------------------------------------------------------


def test_diodes_carry_the_fccd_simflow_reads(default_geds):
    """``legendsimflow.metadata.get_sanitized_fccd`` falls back to 1 mm without this."""
    for name, det in default_geds.items():
        fccd = det["characterization"]["combined_0vbb_analysis"]["fccd_in_mm"]
        assert isinstance(fccd["value"], float), name
        assert set(fccd["uncertainty"]) == {"pos", "neg"}, name


def test_diodes_carry_the_l200_site_voltages(default_geds):
    """``legendsimflow.aggregate._hpge_is_modelable`` and the Julia SSD helpers read these."""
    for name, det in default_geds.items():
        site = det["characterization"]["l200_site"]
        assert isinstance(site["depletion_voltage_in_V"], (int, float)), name
        assert isinstance(site["recommended_voltage_in_V"], (int, float)), name
        assert site["recommended_voltage_in_V"] >= site["depletion_voltage_in_V"], name


def test_production_field_types(default_geds):
    """``get_crystal_name`` does ``format(order, "02d")``, which raises on a string."""
    for name, det in default_geds.items():
        assert det["type"] in TYPE_IDS, name
        assert isinstance(det["production"]["order"], int), name
        assert isinstance(det["production"]["crystal"], str), name
        assert isinstance(det["production"]["slice"], str), name
        assert "geometry" in det, name


def test_every_diode_maps_onto_a_crystal_with_a_slice_status(default_geds, default_crystals):
    """``get_hpge_crystal_metadata_usability`` reads ``slices[production.slice].status``.

    Without it every simulated hit is silently flagged ``is_valid_sim = False``.
    """
    crystals = {TYPE_IDS["icpc"] + format(c["order"], "02d") + c["name"]: c for c in default_crystals}

    for name, det in default_geds.items():
        crystal = crystals[crystal_name(det)]
        assert crystal["slices"][det["production"]["slice"]]["status"] == "valid", name


def test_crystals_carry_an_impurity_curve(default_crystals):
    """No ``impurity_curve.parameters`` means no detector is valid for drift-time modeling."""
    for crystal in default_crystals:
        assert crystal["impurity_curve"]["parameters"]


def test_detector_names_match_the_legend_metadata_templates(default_geds):
    """``^V\\w{6}$`` (icpc-detector) and ``^[VBP]\\d{5}[A-Z]$`` (geds-channel)."""
    import re

    for name in default_geds:
        assert re.fullmatch(r"[VBP]\d{5}[A-Z]", name), name


# ----------------------------------------------------------------------------
# generation
# ----------------------------------------------------------------------------


@pytest.fixture
def channelmap():
    """A channel map with the minimum variety: two geds, a spms and a pmts channel."""

    def diode(name, string, position, rawid, crystal="1", slice_="A"):
        return {
            "name": name,
            "system": "geds",
            "type": "icpc",
            "location": {"string": string, "position": position},
            "daq": {"rawid": rawid},
            "production": {"order": 1, "crystal": crystal, "slice": slice_},
            "geometry": {"height_in_mm": 90},
            "characterization": {"l200_site": {"depletion_voltage_in_V": 3026}},
        }

    return {
        "V00101A": diode("V00101A", 1, 1, 101),
        "V00102A": diode("V00102A", 1, 2, 102),
        "S0101T": {
            "name": "S0101T",
            "system": "spms",
            "location": {"barrel": 1, "fiber": "S0101", "position": "top"},
            "daq": {"rawid": 5000},
        },
        "PMT001": {"name": "PMT001", "system": "pmts", "location": "floor", "daq": {"rawid": 6000}},
    }


@pytest.fixture
def crystals():
    return [
        {
            "name": "1",
            "order": 1,
            "impurity_curve": {"parameters": {"a": 5.0}},
            "slices": {"A": {"detector_offset_in_mm": 112, "status": "valid"}},
        }
    ]


@pytest.fixture
def tree(channelmap, crystals):
    from pygeoml1000 import metadata

    return metadata.build_metadata_tree(
        {"channelmap": channelmap, "special_metadata": {"detail": {}}, "crystals": crystals}
    )


def test_generated_paths(tree):
    assert set(tree) == {
        "datasets/runinfo.yaml",
        "datasets/runlists.yaml",
        "datasets/statuses/validity.yaml",
        "datasets/statuses/l1000-p01-r%-T%-all-config.yaml",
        "hardware/configuration/channelmaps/validity.yaml",
        "hardware/configuration/channelmaps/l1000-p01-r%-T%-all-config.yaml",
        "hardware/detectors/germanium/diodes/V00101A.yaml",
        "hardware/detectors/germanium/diodes/V00102A.yaml",
        "hardware/detectors/germanium/crystals/V011.yaml",
        "special_metadata.yaml",
    }


def test_the_diode_file_cannot_override_the_channel_map(channelmap):
    """``LegendMetadata.channelmap`` merges the diode over the channel with ``|=``.

    A diode carrying ``daq``, ``location`` or ``system`` would silently replace
    the channel's raw ID and position.
    """
    from pygeoml1000 import metadata

    for entry in channelmap.values():
        channel, diode = metadata.split_channel(entry)

        if entry["system"] != "geds":
            assert diode is None
            assert channel == entry
            continue

        assert set(diode) == set(metadata.DIODE_KEYS)
        assert set(channel) & set(diode) == {"name"}
        assert not {"system", "daq", "location"} & set(diode)
        assert set(channel) | set(diode) == set(entry)


def test_a_key_added_to_a_template_reaches_the_tree(channelmap):
    """The channel half takes whatever the diode half does not claim.

    A raw config may add keys to a detector template, and a real channel map
    carries `voltage` and `electronics`. A fixed allow-list on the channel half
    would drop them, and the geometry rebuilt from the tarball would differ.
    """
    from pygeoml1000 import metadata

    channelmap["V00101A"]["voltage"] = {"card": {"id": 7}}
    channel, diode = metadata.split_channel(channelmap["V00101A"])

    assert channel["voltage"] == {"card": {"id": 7}}
    assert "voltage" not in diode


def test_every_channel_has_a_status_and_only_geds_have_psd(channelmap):
    """``gen_hpge_modeling_status`` reads ``analysis.usability`` unguarded at DAG-build time."""
    from pygeoml1000 import metadata

    statuses = metadata.build_statuses(channelmap)

    assert set(statuses) == set(channelmap)
    for name, status in statuses.items():
        assert status["usability"] == "on"
        assert status["processable"] is True
        assert ("psd" in status) == (channelmap[name]["system"] == "geds")


def test_statuses_do_not_share_state(channelmap):
    """Each entry is its own copy, so editing one generated status cannot move another."""
    from pygeoml1000 import metadata

    statuses = metadata.build_statuses(channelmap)
    statuses["V00101A"]["usability"] = "off"
    statuses["V00101A"]["psd"]["status"]["low_aoe"] = "missing"

    assert statuses["V00102A"]["usability"] == "on"
    assert statuses["V00102A"]["psd"]["status"]["low_aoe"] == "valid"
    assert metadata.DEFAULT_STATUS["usability"] == "on"


def test_crystals_are_grouped_and_carry_a_slice_status(channelmap, crystals):
    from pygeoml1000 import metadata

    built = metadata.build_crystals(channelmap, crystals)

    assert set(built) == {"V011"}
    assert built["V011"]["slices"]["A"]["status"] == "valid"
    assert built["V011"]["name"] == "1"
    assert built["V011"]["order"] == 1


def test_crystal_slice_status_is_filled_in_when_the_catalog_omits_it(channelmap, crystals):
    from pygeoml1000 import metadata

    del crystals[0]["slices"]["A"]["status"]
    built = metadata.build_crystals(channelmap, crystals)

    assert built["V011"]["slices"]["A"]["status"] == metadata.DEFAULT_SLICE_STATUS


def test_generated_file_names_follow_the_template(channelmap, crystals):
    """The template's ``apply:`` entries name the generated files, in both accepted forms."""
    from pygeoml1000 import metadata

    template = dict(metadata.load_template())
    template["datasets/statuses/validity.yaml"] = [
        {"valid_from": "20000101T000000Z", "apply": "scalar-form.yaml"}
    ]
    template["hardware/configuration/channelmaps/validity.yaml"] = [
        {"valid_from": "20000101T000000Z", "apply": ["first.yaml", "second.yaml"]}
    ]

    tree = metadata.build_metadata_tree(
        {"channelmap": channelmap, "special_metadata": {}, "crystals": crystals},
        template=template,
    )

    assert "datasets/statuses/scalar-form.yaml" in tree
    assert "hardware/configuration/channelmaps/first.yaml" in tree
    assert "hardware/configuration/channelmaps/second.yaml" in tree


def test_directory_and_archive_hold_the_same_tree(tmp_path, tree):
    from pygeoml1000 import metadata

    metadata.write_metadata(tree, tmp_path / "dir")
    metadata.write_metadata(tree, tmp_path / "tree.tar.gz")

    assert metadata.load_tree(tmp_path / "dir") == tree
    assert metadata.load_tree(tmp_path / "tree.tar.gz") == tree


def test_packing_the_same_tree_twice_gives_the_same_bytes(tmp_path, tree):
    """Otherwise every regeneration churns the committed tarball."""
    from pygeoml1000 import metadata

    first = metadata.write_metadata(tree, tmp_path / "a.tar.gz").read_bytes()
    second = metadata.write_metadata(tree, tmp_path / "b.tar.gz").read_bytes()

    assert first == second


def test_runlists_keep_range_expressions(tree):
    """A bare ``r000`` is never given an experiment prefix by legend-simflow."""
    import re

    runlists = tree["datasets/runlists.yaml"]
    for datatypes in runlists.values():
        for periods in datatypes.values():
            for runs in periods.values():
                for run in runs if isinstance(runs, list) else [runs]:
                    assert re.fullmatch(r"r\d+\.\.r\d+", run), run


def test_runinfo_phy_runs_have_a_livetime(tree):
    """``make_simstat_partition_file`` splits simulated events in proportion to it."""
    runinfo = tree["datasets/runinfo.yaml"]
    for runs in runinfo.values():
        for run in runs.values():
            assert "livetime_in_s" in run["phy"]


# ----------------------------------------------------------------------------
# round trip: the geometry must be rebuildable from the tarball alone
# ----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def small_config():
    """A single cluster of six strings with two units each, to keep compilation cheap."""
    return {
        "raw_config": {
            "array": {"center": {"x_in_mm": [0.0], "y_in_mm": [0.0]}},
            "string": {"units": {"n": 2}},
        }
    }


@pytest.fixture(scope="module")
def small_tarball(tmp_path_factory, small_config):
    from pygeoml1000 import config

    return config.write_metadata(
        small_config, tmp_path_factory.mktemp("meta") / "l1000dsg01-geom-metadata.tar.gz"
    )


def test_geometry_inputs_survive_the_round_trip(small_config, small_tarball):
    """compile -> metadata tree -> tarball -> compiled inputs, with nothing lost."""
    from pygeoml1000 import config

    original = config.resolve_config(small_config)
    rebuilt = config.resolve_config({"metadata": str(small_tarball)})

    assert rebuilt["channelmap"] == original["channelmap"]
    assert rebuilt["special_metadata"] == original["special_metadata"]


def test_a_resolved_metadata_config_no_longer_refers_to_the_tarball(small_tarball):
    """'metadata' is consumed by resolving, like 'raw_config', so a resolved config stands alone."""
    from pygeoml1000 import config

    resolved = config.resolve_config({"metadata": str(small_tarball)})

    assert "metadata" not in resolved
    assert config.resolve_config(resolved) == resolved


def test_metadata_wins_over_the_other_geometry_inputs(small_tarball, caplog):
    from pygeoml1000 import config

    with caplog.at_level("WARNING"):
        resolved = config.resolve_config(
            {"metadata": str(small_tarball), "channelmap": {"nonsense": {}}}
        )

    assert "nonsense" not in resolved["channelmap"]
    assert "'channelmap' is ignored because 'metadata' is given" in caplog.text


def test_repacking_a_tarball_is_a_no_op(tmp_path, small_tarball):
    """Re-packing must use the tree's own crystals, not fall back to the packaged catalog."""
    from pygeoml1000 import config, metadata

    again = config.write_metadata({"metadata": str(small_tarball)}, tmp_path / "again.tar.gz")

    assert metadata.load_tree(again) == metadata.load_tree(small_tarball)


def test_geometry_builds_from_the_tarball_alone(small_tarball):
    from pygeoml1000 import config, core

    registry = core.construct(config.resolve_config({"metadata": str(small_tarball)}))

    assert len(registry.physicalVolumeDict) > 0


# ----------------------------------------------------------------------------
# the generated tree, read back through the real legend-metadata machinery
# ----------------------------------------------------------------------------


def test_legendmetadata_reads_the_generated_tree(tmp_path, small_config):
    """The three-way split has to survive `LegendMetadata.channelmap`.

    That method merges the diode file over the channel with ``|=`` and attaches
    the statuses as ``analysis``. This is the merge the whole layout is built
    around, so exercise the real implementation rather than imitating it.
    """
    legendmeta = pytest.importorskip("legendmeta")

    from pygeoml1000 import config, metadata

    compiled = config.resolve_config(small_config)["channelmap"]
    config.write_metadata(small_config, tmp_path)

    db = legendmeta.LegendMetadata(tmp_path, lazy=True)
    # a timestamp after `valid_from` of both validity files
    chmap = db.channelmap("20000102T000000Z", skip_version_check=True)

    assert set(chmap) == set(compiled)
    geds = {name: det for name, det in chmap.items() if det.system == "geds"}
    assert geds

    for name, det in geds.items():
        # from datasets/statuses
        assert det.analysis.usability == "on", name
        assert det.analysis.psd.status.low_aoe == "valid", name
        # from hardware/configuration/channelmaps: the diode merge must not have
        # replaced these with whatever the detector template happened to carry
        assert det.daq.rawid == compiled[name]["daq"]["rawid"], name
        assert det.location.string == compiled[name]["location"]["string"], name
        assert det.location.position == compiled[name]["location"]["position"], name
        # from hardware/detectors/germanium/diodes
        assert det.characterization.combined_0vbb_analysis.fccd_in_mm.value > 0, name
        assert det.characterization.l200_site.depletion_voltage_in_V > 0, name

    # and the crystal every diode points at is actually there
    crystals = db.hardware.detectors.germanium.crystals
    for name, det in geds.items():
        crystal = crystals[metadata.crystal_name(dict(det))]
        assert crystal.slices[det.production.slice].status == "valid", name
