# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Portal streams use compositor coordinates; frames use their own pixel size."""
def match_screen(properties,screens):
    position,size=properties.get('position'),properties.get('size')
    if position is None or size is None:
        if len(screens)==1:return screens[0]
        raise RuntimeError('The portal did not identify its selected screen. No coordinates were guessed.')
    matches=[screen for screen in screens if tuple(position)==(screen['geometry']['x'],screen['geometry']['y']) and tuple(size)==(screen['geometry']['width'],screen['geometry']['height'])]
    if len(matches)!=1:raise RuntimeError('The shared screen no longer matches the desktop topology. Reconnect before input.')
    return matches[0]

def intersection(a,b):return max(0,min(a['x']+a['width'],b['x']+b['width'])-max(a['x'],b['x']))*max(0,min(a['y']+a['height'],b['y']+b['height'])-max(a['y'],b['y']))

def select_stream(streams,scene):
    window=scene.get('window')
    if not window:raise RuntimeError('Activate the application to inspect it.')
    candidates=[]
    for node,properties in streams:
        screen=match_screen(properties,scene['screens']);area=intersection(window['geometry'],screen['geometry'])
        if area:candidates.append((area,node,properties,screen))
    if not candidates:raise RuntimeError('The active application is outside the shared screens. Share its screen before controlling it.')
    _,node,properties,screen=max(candidates,key=lambda row:row[0])
    return node,properties,screen
