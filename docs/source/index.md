# l1000geom

```{warning}
This is an early version of the LEGEND-1000 geometry implemented with the
python-based simulation stack. It is not a drop-in replacement for MaGe, and
still under heavy development!
```

## Installation and usage

Following a git checkout, the package and its other python dependencies can be
installed with:

```
pip install -e .
```

If you do not intend to edit the python code in this geometry package, you can
omit the `-e` option.

After installation, the CLI utility `legend-pygeom-l1000` is provided on your
PATH. This CLI utility is the primary way to interact with this package. For
now, you can find usage docs by running `legend-pygeom-l1000 -h`.

```{toctree}
:maxdepth: 2

metadata.md
```

```{toctree}
:maxdepth: 1
:caption: Development

Package API reference <api/modules>
```
