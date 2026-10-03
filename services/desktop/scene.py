# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Compositor scene fences; covering windows remain blockers regardless of PID."""


def same_scene(first,second):
    def identity(scene):
        window=scene.get('window') or {}
        return {**scene,'window':{key:value for key,value in window.items() if key!='title'}}
    return identity(first)==identity(second)


def inside(rect,x,y):
    return rect['x']<=x<rect['x']+rect['width'] and rect['y']<=y<rect['y']+rect['height']


def covered(scene,x,y):
    return any(inside(window['geometry'],x,y) for window in scene.get('above',[]))
