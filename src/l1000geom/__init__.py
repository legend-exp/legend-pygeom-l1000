from __future__ import annotations

import sys
import warnings

import pygeoml1000  # noqa: F401

sys.modules[__name__] = sys.modules["pygeoml1000"]

warnings.warn("Please use `pygeoml1000` instead of `l1000geom`.", FutureWarning, stacklevel=2)
