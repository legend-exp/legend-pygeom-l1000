# Configuration file for the Sphinx documentation builder.
from __future__ import annotations

import importlib.metadata
import shutil
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, Path(__file__).parents[2].resolve().as_posix())

project = "pygeoml1000"
copyright = "The LEGEND Collaboration"
version = importlib.metadata.version("legend-pygeom-l1000")

extensions = [
    "sphinx.ext.githubpages",
    "sphinx.ext.autodoc",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "myst_parser",
    "sphinx_subfigure",
]
myst_enable_extensions = ["colon_fence"]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
exclude_patterns = [
    "_build",
    "_generated",
    "**.ipynb_checkpoints",
    "Thumbs.db",
    ".DS_Store",
    ".env",
    ".venv",
]

# The metadata template ships as a tarball, so `literalinclude` cannot reach its
# files. Unpack it next to the sources at build time. The documentation then
# shows the packaged template itself, and cannot drift away from it.
_TEMPLATE_ARCHIVE = Path(__file__).parents[2] / "src/pygeoml1000/configs/template_metadata.tar.gz"
_TEMPLATE_DIR = Path(__file__).parent / "_generated/template_metadata"

shutil.rmtree(_TEMPLATE_DIR, ignore_errors=True)
_TEMPLATE_DIR.mkdir(parents=True)
with tarfile.open(_TEMPLATE_ARCHIVE, "r:*") as _tar:
    _tar.extractall(_TEMPLATE_DIR, filter="data")

master_doc = "index"
language = "python"

# Furo theme
html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/legend-exp/legend-pygeom-l1000",
    "source_branch": "main",
    "source_directory": "docs/source",
}
html_title = f"{project} {version}"

autodoc_default_options = {
    "ignore-module-all": True,
    # ignore some common members from NamedTuples.
    "exclude-members": "_asdict, _fields, _field_defaults, _make, _replace",
}

# sphinx-napoleon
# enforce consistent usage of NumPy-style docstrings
napoleon_numpy_docstring = True
napoleon_google_docstring = False
napoleon_use_ivar = True

# intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "scipy": ("https://docs.scipy.org/doc/scipy", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
    "matplotlib": ("https://matplotlib.org/stable", None),
    "pint": ("https://pint.readthedocs.io/en/stable", None),
    "pyg4ometry": ("https://pyg4ometry.readthedocs.io/en/stable", None),
    "legendmeta": ("https://pylegendmeta.readthedocs.io/en/stable/", None),
    "dbetto": ("https://dbetto.readthedocs.io/en/stable/", None),
    "pygeomhpges": ("https://legend-pygeom-hpges.readthedocs.io/en/stable/", None),
    "pygeomoptics": ("https://legend-pygeom-optics.readthedocs.io/en/stable/", None),
    "pygeomtools": ("https://legend-pygeom-tools.readthedocs.io/en/stable/", None),
    "legend-pygeom-l200": ("https://legend-pygeom-l200.readthedocs.io/en/stable/", None),
}  # add new intersphinx mappings here

# sphinx-autodoc
# Include __init__() docstring in class docstring
autoclass_content = "both"
autodoc_typehints = "description"
autodoc_typehints_description_target = "all"
autodoc_typehints_format = "short"
