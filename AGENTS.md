# AGENTS.md

## Project overview

This repository holds `pygeoml1000`, the Monte Carlo geometry of the LEGEND-1000
experiment. The `legend-pygeom-l1000` CLI builds the Geant4 geometry with
pyg4ometry and writes it as GDML, which
[remage](https://github.com/legend-exp/remage) reads.

The package uses legend-pygeom-hpges (HPGe detectors), legend-pygeom-optics
(optical properties) and legend-pygeom-tools (materials and tools). The sister
package [legend-pygeom-l200](https://github.com/legend-exp/legend-pygeom-l200)
is more mature. When in doubt, use its conventions for names, colours and
surfaces.

`src/l1000geom/` is a deprecated alias of `pygeoml1000`. Do not add code there.

## Architecture

All code is in `src/pygeoml1000/`:

- `core.py`: `construct(config)` resolves the config, makes the world volume and
  calls each subsystem in this order: `cavern_and_labs` → `watertank` →
  `watertank_instrumentation` → `cryo` → `hpge_strings` → `fibers`. Each
  subsystem gets the `InstrumentationData` NamedTuple. It cannot be changed in
  place, so a subsystem that sets a new mother volume returns a copy made with
  `_replace`.
- `config.py`: loads and validates the runtime config against
  `configs/runtime_config_schema.yaml`. It also applies the detail levels and
  assemblies (`configs/detail.yaml`), reads the channel map from
  legend1000-metadata (`generate_channelmap`) and makes the special metadata.
- `cli.py`: the argparse CLI.
- `manifest.py`: the parts manifest (`--write-manifest`).
- `utils.py`: the central `COLORS` dictionary.
- `rt_profiles.py`, `wlsr.py`: geometry helpers.
- `configs/*.yaml`: the raw geometry config (array, string, PMT positions,
  detail levels).
- `models/*.stl`: CAD meshes. `models/README.md` records where each mesh comes
  from. Update it when you add a mesh.

## Metadata

The channel map and the HPGe detector records come from
[legend1000-metadata](https://github.com/legend-exp/legend1000-metadata),
through `Legend1000Metadata` in pylegendmeta. Set `$LEGEND1000_METADATA` to a
checkout of it (for example the sibling `../legend1000-metadata`). If the
variable is not set, pylegendmeta clones the repository into a temporary
directory.

- The channel names follow the patterns of the dummy records in
  legend1000-metadata: `V00101Z` (HPGe), `S0101T` (SiPM), `PMT0101`.
  `tests/test_config.py` checks that the metadata can derive a record for each
  name.
- A config that holds its own `channelmap` and `special_metadata` needs no
  checkout.
- `src/pygeoml1000/configs/channelmap.json` and `special_metadata.yaml` are
  generated files. They are in `.gitignore`. Do not commit them.

## Common commands

These commands are the same as in CI (`.github/workflows/ci.yml`):

- Install (dev): `pip install -e '.[all]'`
- Test: `pytest` (with `$LEGEND1000_METADATA` set). Single test:
  `pytest tests/test_core.py::test_construct`. Pytest has
  `filterwarnings = "error"`, so a new warning makes the tests fail.
- Lint/format: `pre-commit run --all-files`
- Build docs: `cd docs && make`. Sphinx runs with `-W`, so a warning is an
  error. Regenerate the documentation images with `make images`.
- Check a geometry: `legend-pygeom-l1000 --check-overlaps l1000.gdml`. Write the
  parts list with `--write-manifest parts.yaml`.

The nox sessions (`nox -s lint`, `nox -s tests`, `nox -s docs`) do the same in a
temporary environment.

## Conventions

- Names of solids, volumes, materials and surfaces follow
  `docs/source/naming.md`: `[<group>_]<component>[_<material>][_<extra>]`, and
  detector names as they are. Add a new group prefix to the table in that file.
- Identical parts must share one logical volume. Do not put a detector or string
  identifier in a logical volume name. `test_volume_caching` in
  `tests/test_core.py` checks this.
- Take colours from `COLORS` in `utils.py`. Do not write colour values in the
  subsystem modules.
- A new runtime config key goes into `configs/runtime_config_schema.yaml` and
  `docs/source/runtime-cfg.md`.
- Ruff configuration is in `pyproject.toml`: line length 110, and every file
  starts with `from __future__ import annotations`. Use `logging`, not `print`,
  in `src/`.

## Git workflow

- Commit style: Conventional Commits (https://www.conventionalcommits.org), for
  example `feat:`, `fix:`, `docs:`, `chore:`.
- Follow `AI_POLICY.md`. Do not add a `Co-authored-by:` trailer for an AI agent.
  Add the trailer `Assisted-by: Generative AI` instead. A pull request that an
  agent opens starts with the review checkbox from `AI_POLICY.md`.
- Give each pull request a short description and link the related issues and
  pull requests. CI must pass.

## Boundaries

- ALWAYS run `pre-commit run --all-files` and `pytest` before a commit, and read
  the output. Build the docs too when you change `docs/` or a docstring.
- Do not edit generated files by hand: `src/pygeoml1000/_version.py`
  (setuptools_scm), `docs/source/api/` (sphinx-apidoc).
- Do not commit `.claude/`, `.pixi/`, `build/`, `docs/build/`, or generated GDML
  and log files.
- Only change files within the scope of the task.
