# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""The sidebar reads Desktop appearance and uses its prompt improvement operation."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'apps/native'))
from augmentor_linux.preferences import Preferences
from PySide6.QtGui import QColor

def appearance(settings=None):
    preferences=Preferences()
    if settings is not None:
        if not isinstance(settings,dict):raise ValueError('Invalid appearance')
        updates={}
        for external,internal,low,high in [('neutHue','hue',0,359),('neutBright','brightness',-15,15),('accentHue','accent_hue',0,359),('accentBright','accent_brightness',-15,15)]:
            value=settings.get(external)
            if type(value) not in (int,float) or not low<=value<=high+int(high==359):raise ValueError('Invalid appearance value')
            updates[internal]=min(high,int(value))
        if settings.get('theme') not in ('dark','light'):raise ValueError('Invalid theme')
        import re
        colours=settings.get('formatColours',{})
        if not isinstance(colours,dict) or any(not isinstance(v,str) or not re.fullmatch('#[0-9a-fA-F]{6}',v) for v in colours.values()):raise ValueError('Invalid formatting colour')
        updates.update(theme=settings['theme'],format_colours=colours)
        preferences.values.update(updates);preferences.save()
    v=preferences.values;dark=v['theme']=='dark'
    light=(.12 if dark else .92)+v['brightness']/150
    saturation=v.get('saturation',48)/100
    bg=QColor.fromHslF(v['hue']/360,saturation*.5625,max(.025,min(.99,light)))
    bubble=QColor.fromHslF(v['hue']/360,saturation*(.23/.48),min(.995,max(.025,light)+(.09 if dark else .045)))
    accent=QColor.fromHslF(v['accent_hue']/360,saturation,max(.15,min(.9,(.73 if dark else .30)+v['accent_brightness']/150)))
    field=bg.lighter(125) if dark else bg.darker(105)
    return {'theme':v['theme'],'animation':v['animation'],'values':{'theme':v['theme'],'neutHue':v['hue'],'neutBright':v['brightness'],'accentHue':v['accent_hue'],'accentBright':v['accent_brightness'],'formatColours':v['format_colours']},'tokens':{'--bg':bg.name(),'--field':field.name(),'--layer1':field.name(),'--layer2':field.name(),'--text':'#edf3f3' if dark else '#152b2c','--brand':accent.name(),'--accent':accent.name(),'--user-bubble':bubble.name(),'--format-heading':v['format_colours'].get('heading',accent.name()),'--format-link':v['format_colours'].get('link',accent.name())}}

def request(value):
    if value.get('action')=='appearance':return appearance(value.get('settings'))
    if value.get('action')=='improve':
        text=value.get('text');selection=value.get('selection')
        if not isinstance(text,str) or not text.strip() or len(text)>8192:raise ValueError('Invalid prompt draft')
        if not isinstance(selection,dict) or not all(isinstance(selection.get(k),str) and selection[k] for k in ('provider','model')):raise ValueError('Choose a model first')
        from augmentor_linux.adapters.dsh import DshAdapter
        from augmentor_linux.prompt_client import PromptClient
        settings=PromptClient().call('prompts.list').get('improvement')
        if not settings:raise ValueError('Prompt improvement settings are unavailable')
        return DshAdapter().improve_prompt(text,settings['content'],selection)
    raise ValueError('Unsupported surface operation')

if __name__=='__main__':
    try:
        raw=sys.stdin.read(16385)
        if len(raw)>16384:raise ValueError('Surface request too large')
        print(json.dumps(request(json.loads(raw))))
    except Exception as e:print(json.dumps({'error':str(e)}));sys.exit(1)
