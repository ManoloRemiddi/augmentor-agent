# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Whole-interface scaling before Qt creates native windows, never bitmap zoom."""
from contextlib import contextmanager
import math
import os

MINIMUM = 75
MAXIMUM = 150
STEP = 5


def normalize(value):
    if type(value) is not int:
        return 100
    return max(MINIMUM, min(MAXIMUM, round(value / STEP) * STEP))


@contextmanager
def startup_scale(percent):
    """Multiply the caller's Qt scale; restore its environment for child apps.

    The resulting device pixel ratio includes the OS per-monitor scale. Qt
    handles painting, popups, input coordinates and GPU resolution together.
    Changes take effect on the next process start, preserving active work.
    """
    previous = os.environ.get('QT_SCALE_FACTOR')
    try:
        factor = float(previous or '1')
        if not math.isfinite(factor) or factor <= 0:
            factor = 1.
    except ValueError:
        factor = 1.
    os.environ['QT_SCALE_FACTOR'] = str(factor * normalize(percent) / 100)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('QT_SCALE_FACTOR', None)
        else:
            os.environ['QT_SCALE_FACTOR'] = previous
