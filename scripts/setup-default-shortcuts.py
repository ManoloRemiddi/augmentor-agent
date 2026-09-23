#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Assign available KDE defaults without replacing any existing shortcut."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/native'))
from PySide6.QtGui import QKeySequence
from augmentor_linux.shortcuts import current_keys,save_shortcut,display_key
result={}
for instance,keys in [('main','Meta+Alt+Space'),('secondary','Meta+Alt+Shift+Space')]:
    try:
        previous=current_keys(instance)
        result[instance]=[display_key(key) for key in previous] if previous else display_key(save_shortcut(QKeySequence(keys),instance))
    except (RuntimeError,ValueError,OSError) as error:result[instance]='Choose in Settings: '+str(error)
print(json.dumps(result))
