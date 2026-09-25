# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Browser settings use the same primary voice profile and native preferences."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'apps/native'))
from augmentor_linux.voice_settings import voice_request
from augmentor_linux.preferences import Preferences

def request(value):
    action=value.get('action','get')
    if action not in ('get','save'):raise ValueError('Unsupported voice settings action')
    preferences=Preferences()
    if action=='save':
        settings=value['settings']
        if settings.get('mode') not in ('manual','hands-free'):raise ValueError('Choose a conversation mode')
        if type(settings.get('pauseMs')) is not int or not 400<=settings['pauseMs']<=2000:raise ValueError('Invalid pause duration')
        if type(settings.get('enabled')) is not bool:raise ValueError('Invalid voice setting')
        # The speech service validates voice ID, speed and volume before saving.
        result=voice_request('preferences',{'values':{k:settings[k] for k in ('voiceId','speed','volume')}})
        preferences.values.update(voice_mode=settings['mode'],voice_pause_ms=settings['pauseMs'],resonant_voice=settings['enabled'])
        preferences.save()
    else:result=voice_request('preferences')
    return {**result,'mode':preferences.values['voice_mode'],'pauseMs':preferences.values['voice_pause_ms'],'enabled':preferences.values['resonant_voice']}

if __name__=='__main__':
    try:
        raw=sys.stdin.read(16385)
        if len(raw)>16384:raise ValueError('Voice settings request is too large')
        print(json.dumps(request(json.loads(raw))))
    except Exception as error:
        print(json.dumps({'error':str(error)}));sys.exit(1)
