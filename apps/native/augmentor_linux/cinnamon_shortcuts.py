# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Qt shortcut rows backed by native Cinnamon settings through a bounded worker."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
from .shortcut_key_codec import encode as encode_key,decode as decode_key

def encode(sequence):return encode_key(sequence,"Cinnamon")
def decode(value):return decode_key(value,"Cinnamon")


def active():
    return sys.platform=='linux' and 'X-CINNAMON' in os.environ.get('XDG_CURRENT_DESKTOP','').upper().split(':')


def request(action,instance,**values):
    payload={'schema':1,'action':action,'instance':instance,**values}
    result=subprocess.run([sys.executable,'-B',str(ROOT/'services/desktop/cinnamon_shortcuts.py')],
        input=json.dumps(payload),capture_output=True,text=True,timeout=25)
    try:
        if len(result.stdout)>4096:raise ValueError()
        reply=json.loads(result.stdout)
        if not isinstance(reply,dict) or type(reply.get('schema')) is not int or reply['schema']!=1:raise ValueError()
    except ValueError:raise RuntimeError('Cinnamon shortcut service returned an invalid response.') from None
    if reply.get('error') is not None and not isinstance(reply['error'],str):
        raise RuntimeError('Cinnamon shortcut service returned an invalid response.')
    if result.returncode or reply.get('error'):
        exception=ValueError if reply.get('kind')=='invalid' else RuntimeError
        raise exception(reply.get('error') or 'Cinnamon shortcut service is unavailable.')
    if type(reply.get('configured')) is not bool or reply.get('functionalTested') is not False:
        raise RuntimeError('Cinnamon shortcut service returned an invalid binding status.')
    return reply


def current_keys(instance):
    reply=request('read',instance)
    return [decode(reply['key'])] if reply['configured'] else []


def save_shortcut(sequence,instance):
    reply=request('save',instance,**encode(sequence))
    if not reply['configured']:raise RuntimeError('Cinnamon did not retain the shortcut assignment.')
    return decode(reply['key'])
