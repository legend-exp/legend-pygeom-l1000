# pygeoml1000

```{warning}
This is a still-in-development version of the LEGEND-1000 geometry implemented with the
python-based simulation stack. It is not a drop-in replacement for MaGe, and
still under development!
```

Python package containing the Monte Carlo geometry implementation of the
LEGEND-1000 experiment.

This geometry can be used as an input to the
[remage](https://remage.readthedocs.io/en/stable/) simulation software.

This package is based on {doc}`pyg4ometry <pyg4ometry:index>`,
{doc}`legend-pygeom-hpges <pygeomhpges:index>` (implementation of HPGe
detectors), {doc}`legend-pygeom-optics <pygeomoptics:index>` (optical properties
of materials) and {doc}`legend-pygeom-tools <pygeomtools:index>`.

## Installation

Following a git checkout, the package and its other python dependencies can be
installed with:

```console
pip install -e .
```

If you do not intend to edit the python code in this geometry package, you can
omit the `-e` option.

## Usage as CLI tool

After installation, the CLI utility `legend-pygeom-l1000` is provided on your
PATH. This CLI utility is the primary way to interact with this package.

In the simplest case, you can create a usable geometry file with:

```console
legend-pygeom-l1000 l1000.gdml
```

The generated geometry can be customized with a large number of options. Some
geometry options can both be set on the CLI utility and in the config file.
Those are described in {doc}`runtime-cfg`, and the descriptions similarly apply
to the CLI options.

### Quick start examples

Generate a basic geometry:

```console
legend-pygeom-l1000 l1000.gdml
```

Generate and visualize:

```console
legend-pygeom-l1000 --visualize l1000.gdml
```

Generate with specific detail level:

```console
legend-pygeom-l1000 --detail full l1000.gdml
```

For detailed usage information, see the {doc}`cli_usage`.

## Documentation

```{toctree}
:maxdepth: 2
:caption: User Guide

cli_usage
runtime-cfg
visualization
description
coordinate_systems
```

```{toctree}
:maxdepth: 1
:caption: Reference

geometry_components
metadata
naming
```

```{toctree}
:maxdepth: 1
:caption: Development

geom-dev
Package API reference <api/modules>
```
