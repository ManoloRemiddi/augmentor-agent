# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Portal streams use compositor coordinates; frames use their own pixel size."""
class TopologyError(RuntimeError):
    """The selected streams can no longer identify the connected outputs."""

def match_screen(properties,screens):
    position,size=properties.get('position'),properties.get('size')
    if properties.get('source_type',1)!=1:raise TopologyError('Share monitor streams for desktop control.')
    if position is None and size is None:
        if len(screens)==1:return screens[0]
        raise TopologyError('The portal did not identify its selected screen. No coordinates were guessed.')
    if size is None:raise TopologyError('The portal omitted the shared monitor size. Reconnect before input.')
    if position is None and properties.get('source_type')!=1:
        raise TopologyError('The portal did not identify a monitor stream. Reconnect before input.')
    matches=[screen for screen in screens if tuple(size)==(screen['geometry']['width'],screen['geometry']['height']) and (position is None or tuple(position)==(screen['geometry']['x'],screen['geometry']['y']))]
    if position is None and len(matches)>1:raise TopologyError('Shared monitors have identical logical sizes and the portal omitted their positions. Reconnect with an identifiable monitor.')
    if len(matches)!=1:raise TopologyError('The shared screen no longer matches the desktop topology. Reconnect before input.')
    return matches[0]

def topology(screens):
    names=[screen.get('name') for screen in screens]
    if not screens or any(not isinstance(name,str) or not name for name in names) or len(set(names))!=len(names):
        raise TopologyError('The compositor did not identify distinct monitor outputs.')
    return tuple(sorted((screen['name'],*(screen['geometry'][key] for key in ('x','y','width','height')),screen.get('scale'),screen.get('transform')) for screen in screens))

def check_topology(screens,expected):
    if topology(screens)!=expected:raise TopologyError('Desktop topology changed. Reconnect before capture or input.')

def bind_streams(streams,screens):
    topology(screens)
    if not streams or len(streams)>len(screens):raise TopologyError('Shared streams do not identify distinct monitor outputs.')
    bindings={};used=set()
    for node,properties in streams:
        if type(node) is not int or node<=0 or node in bindings:raise TopologyError('The portal repeated or omitted a stream identity.')
        screen=match_screen(properties,screens)
        if screen['name'] in used:raise TopologyError('Multiple streams identify the same monitor. Reconnect before input.')
        bindings[node]=screen['name'];used.add(screen['name'])
    return bindings

def intersection(a,b):return max(0,min(a['x']+a['width'],b['x']+b['width'])-max(a['x'],b['x']))*max(0,min(a['y']+a['height'],b['y']+b['height'])-max(a['y'],b['y']))

def select_stream(streams,scene,bindings=None,expected_topology=None):
    window=scene.get('window')
    if not window:raise RuntimeError('Activate the application to inspect it.')
    if expected_topology is not None:check_topology(scene['screens'],expected_topology)
    if bindings is None:bindings=bind_streams(streams,scene['screens'])
    screens={screen['name']:screen for screen in scene['screens']}
    candidates=[]
    for node,properties in streams:
        screen=screens[bindings[node]];area=intersection(window['geometry'],screen['geometry'])
        if area:candidates.append((area,node,properties,screen))
    if not candidates:raise RuntimeError('The active application is outside the shared screens. Share its screen before controlling it.')
    _,node,properties,screen=max(candidates,key=lambda row:row[0])
    return node,properties,screen
