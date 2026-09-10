"""Helpers shared by more than one module of this package."""

from __future__ import annotations

# default RGBA colors of the logical volumes
COLORS = {
    "rock": (0.85, 0.9, 1, 0.05),
    "steel": (0.5, 0.5, 0.5, 0.05),
    "copper": (0.45, 0.55, 0.75, 0.1),
    "water": (0, 0, 1, 0.08),
    "air": (0.1, 0.1, 0.1, 0.025),
    "tyvek": (0.9, 0.9, 0.9, 0.05),
    "fiber_coating": (0, 1, 0.165, 0.25),  # 520 nm
    "pmt_window": (0.9, 0.8, 0.5, 0.05),
    "pmt_cathode": (0.545, 0.271, 0.074, 0.05),
}
