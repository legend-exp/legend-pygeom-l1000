"""Efficiency for the KETEK SiPMs. This is not part of legendoptics."""

from __future__ import annotations

import logging

import numpy as np
import pint
from legendoptics import store
from pint import Quantity

log = logging.getLogger(__name__)
u = pint.get_application_registry()


@store.register_pluggable
def ketek_sipm_efficiency() -> tuple[Quantity, Quantity]:
    """Detection efficiency for the KETEK SiPM."""
    λ = np.array([100, 280, 310, 350, 400, 435, 505, 525, 595, 670][::-1]) * u.nm
    eff = np.array([0.0, 0.19, 0.30, 0.32, 0.33, 0.32, 0.27, 0.19, 0.12, 0.07][::-1])
    return λ, eff
