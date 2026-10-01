# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Qt shortcut rows backed by native GNOME settings through a bounded worker."""
import json
import os
from pathlib import Path
import subprocess
import sys
from PySide6.QtCore import Qt,QKeyCombination
from PySide6.QtGui import QKeySequence

ROOT=Path(__file__).resolve().parents[3]
SPECIAL={'Escape':'Escape','Tab':'Tab','Backtab':'ISO_Left_Tab','Backspace':'BackSpace',
         'Return':'Return','Enter':'KP_Enter','Insert':'Insert','Delete':'Delete','Pause':'Pause',
         'Print':'Print','SysReq':'Sys_Req','Clear':'Clear','Home':'Home','End':'End',
         'Left':'Left','Up':'Up','Right':'Right','Down':'Down','PageUp':'Page_Up',
         'PageDown':'Page_Down','CapsLock':'Caps_Lock','NumLock':'Num_Lock',
         'ScrollLock':'Scroll_Lock','Menu':'Menu','Help':'Help','Hangul':'Hangul',
         'Hangul_Hanja':'Hangul_Hanja',**{f'F{i}':f'F{i}' for i in range(1,36)}}
SYMBOL_TO_QT={symbol:getattr(Qt.Key,'Key_'+name) for name,symbol in SPECIAL.items()}
MODIFIERS={'Shift':Qt.KeyboardModifier.ShiftModifier,'Control':Qt.KeyboardModifier.ControlModifier,
           'Alt':Qt.KeyboardModifier.AltModifier,'Super':Qt.KeyboardModifier.MetaModifier}


def active():
    return sys.platform=='linux' and 'GNOME' in os.environ.get('XDG_CURRENT_DESKTOP','').upper().split(':')


def encode(sequence):
    from .shortcuts import shortcut_key
    shortcut_key(sequence)
    combination=sequence[0];code=int(combination.key());mods=combination.keyboardModifiers()
    supported=Qt.KeyboardModifier.NoModifier
    for value in MODIFIERS.values():supported|=value
    if mods&~supported:
        raise ValueError('GNOME does not support that shortcut modifier. Choose another combination.')
    if code<0x1000000:
        character=chr(code).lower()
        if len(character)!=1:raise ValueError('Choose a shortcut with a single key.')
        key={'character':character}
    else:
        name=combination.key().name.removeprefix('Key_')
        if name not in SPECIAL:raise ValueError('That key is not supported by the GNOME shortcut adapter.')
        key={'symbol':SPECIAL[name]}
    return {'key':key,'modifiers':[name for name,value in MODIFIERS.items() if mods&value]}


def decode(value):
    if not isinstance(value,dict) or not isinstance(value.get('modifiers'),list):
        raise RuntimeError('GNOME returned an invalid shortcut binding.')
    symbol=value.get('symbol');character=value.get('character')
    if symbol in SYMBOL_TO_QT:code=int(SYMBOL_TO_QT[symbol])
    elif isinstance(character,str) and len(character)==1 and len(character.upper())==1:code=ord(character.upper())
    else:raise ValueError('This GNOME binding cannot be represented in the editor. Review Keyboard Settings.')
    mods=Qt.KeyboardModifier.NoModifier
    for name in value['modifiers']:
        if name not in MODIFIERS:raise ValueError('This GNOME binding uses an unsupported modifier. Review Keyboard Settings.')
        mods|=MODIFIERS[name]
    return QKeySequence(QKeyCombination(mods,Qt.Key(code)))[0].toCombined()


def request(action,instance,**values):
    payload={'schema':1,'action':action,'instance':instance,**values}
    result=subprocess.run([sys.executable,'-B',str(ROOT/'services/desktop/gnome_shortcuts.py')],
        input=json.dumps(payload),capture_output=True,text=True,timeout=5)
    try:
        if len(result.stdout)>4096:raise ValueError()
        reply=json.loads(result.stdout)
        if not isinstance(reply,dict) or reply.get('schema')!=1:raise ValueError()
    except ValueError:raise RuntimeError('GNOME shortcut service returned an invalid response.') from None
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
