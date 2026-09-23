# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
from .instances import scoped_path, current_name
import json
import re
import os
from pathlib import Path
import tempfile

DEFAULTS = {'resonant_voice': True, 'voice_mode': 'manual', 'voice_pause_ms': 800, 'theme': 'dark', 'hue': 190, 'brightness': 0, 'accent_hue': 160,
            'accent_brightness': 0, 'saturation': 48, 'opacity': 85, 'animation': True, 'effect': 'plasma', 'background': 'none', 'background_image': '', 'skin_name': 'Custom', 'custom_skins': [], 'flares': True, 'pinned': True, 'placement': {}, 'harness':'dsh','format_colours':{}}


class Preferences:
    def __init__(self, persistent=True):
        self.path = Path(os.environ.get('AUGMENTOR_PI_CONFIG', Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'augmentor-pi')) / 'appearance.json'
        base_path = self.path
        self.path = scoped_path(self.path)
        fresh_secondary = current_name() != "main" and not self.path.exists()
        self.persistent = persistent
        from copy import deepcopy
        self.values = deepcopy(DEFAULTS)
        if persistent:
            try:
                data = json.loads((base_path if fresh_secondary else self.path).read_text())
                for key, default in DEFAULTS.items():
                    value = data.get(key, default)
                    if type(value) is type(default):
                        self.values[key] = value
            except (OSError, ValueError, TypeError):
                pass
        if fresh_secondary:
            self.values["placement"] = {}
        for key, lo, hi in [('hue',0,359),('accent_hue',0,359),('brightness',-15,15),('accent_brightness',-15,15),('saturation',0,100),('opacity',35,100)]:
            self.values[key] = max(lo, min(hi, self.values[key]))
        self.values['format_colours']={k:v for k,v in self.values['format_colours'].items() if isinstance(v,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',v)}
        from .skins import validate_skin
        skins=[]
        for entry in self.values['custom_skins'][:100]:
            try:skins.append(validate_skin(entry))
            except (ValueError, TypeError):pass
        self.values['custom_skins']=skins
        if self.values['effect'] not in ('plasma','butterflies','butterflies-large','none'):self.values['effect']='plasma'
        if self.values['background'] not in ('none','blossom-lake','uploaded'):self.values['background']='none'
        if self.values['background']=='uploaded':
            from .backgrounds import decode_background
            try:decode_background(self.values['background_image'])
            except ValueError:self.values['background']='none';self.values['background_image']=''
        else:self.values['background_image']=''
        if self.values['voice_mode'] not in ('manual','hands-free'):self.values['voice_mode']='manual'
        self.values['voice_pause_ms']=max(400,min(2000,self.values['voice_pause_ms']))
        self.retired_harness = self.values['harness'] == 'opencode'
        if self.values['harness'] not in ('pi','dsh'):self.values['harness']='dsh'
        if self.values['theme'] not in ('light', 'dark'):
            self.values['theme'] = 'dark'
        # Persist the first clone now, even if the user never opens Settings.
        # Future primary changes must not become secondary defaults.
        if fresh_secondary and persistent:self.save()

    def save(self):
        if not self.persistent:
            return
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=self.path.parent, delete=False) as f:
            json.dump(self.values, f)
            temp = f.name
        os.replace(temp, self.path)
