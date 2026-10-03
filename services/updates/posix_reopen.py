# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bounded captured instance names shared by Unix reopening adapters."""
from copy import deepcopy
import re


def validate_plan(plan):
    if (not isinstance(plan,dict) or set(plan)!={'instances','hadBrowser'} or type(plan['hadBrowser']) is not bool
            or not isinstance(plan['instances'],list) or len(plan['instances'])>64
            or any(not isinstance(name,str) or not re.fullmatch('[a-z][a-z0-9-]{0,31}',name) for name in plan['instances'])
            or len(set(plan['instances']))!=len(plan['instances'])):
        raise ValueError('Use only the instance names captured from the original live graph.')
    return deepcopy(plan)
