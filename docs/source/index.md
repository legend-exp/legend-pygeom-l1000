# Welcome to l1000geom’s documentation!

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

A separate package for the LEGEND-200 geometry is available at
{doc}`legend-pygeom-l200:index`. In comparison, it is more mature and also
includes detailed documentation on the geometry components and development
workflow.

This package can run entirely without access to the
[legend-metadata](https://legend-metadata.readthedocs.io/en/stable/).

## Installation

The latest tagged version and all its dependencies can be installed from PyPI:
`pip install legend-pygeom-l1000`.

Alternatively, one can clone the repository from GitHub for development
purposes:

```console
git clone https://github.com/legend-exp/legend-pygeom-l1000.git
```

Following a git clone, the package and its other python dependencies can be
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

The generated geometry can be customized with many options. Some geometry
options can both be set on the CLI utility and in the config file.

### Quick start examples

Generate a default geometry:

```console
legend-pygeom-l1000 l1000.gdml
```

Visualize only:

```console
legend-pygeom-l1000 --visualize
```

Generate with specific detail level:

```console
legend-pygeom-l1000 l1000.gdml --detail comsogenic
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
```

```{toctree}
:maxdepth: 2
:caption: Developer
metadata
Package API reference <api/modules>
```
