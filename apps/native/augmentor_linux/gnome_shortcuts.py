# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Qt shortcut rows backed by native GNOME settings through a bounded worker."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
from .shortcut_key_codec import encode,decode


def active():
    return sys.platform=='linux' and 'GNOME' in os.environ.get('XDG_CURRENT_DESKTOP','').upper().split(':')


def request(action,instance,**values):
    payload={'schema':1,'action':action,'instance':instance,**values}
    result=subprocess.run([sys.executable,'-B',str(ROOT/'services/desktop/gnome_shortcuts.py')],
        input=json.dumps(payload),capture_output=True,text=True,timeout=5)
    try:
        if len(result.stdout)>4096:raise ValueError()
        reply=json.loads(result.stdout)
        if not isinstance(reply,dict) or type(reply.get('schema')) is not int or reply['schema']!=1:raise ValueError()
    except ValueError:raise RuntimeError('GNOME shortcut service returned an invalid response.') from None
    if reply.get('error') is not None and not isinstance(reply['error'],str):
        raise RuntimeError('Gnome shortcut service returned an invalid response.')
    if result.returncode or reply.get('error'):
        exception=ValueError if reply.get('kind')=='invalid' else RuntimeError
        raise exception(reply.get('error') or 'GNOME shortcut service is unavailable.')
    if type(reply.get('configured')) is not bool or reply.get('functionalTested') is not False:
        raise RuntimeError('GNOME shortcut service returned an invalid binding status.')
    return reply


def current_keys(instance):
    reply=request('read',instance)
    return [decode(reply['key'])] if reply['configured'] else []


def save_shortcut(sequence,instance):
    reply=request('save',instance,**encode(sequence))
    if not reply['configured']:raise RuntimeError('GNOME did not retain the shortcut assignment.')
    return decode(reply['key'])
