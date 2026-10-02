# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Convert Qt key identities without interpreting display labels."""
from PySide6.QtCore import Qt,QKeyCombination
from PySide6.QtGui import QKeySequence

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


def encode(sequence,desktop="GNOME"):
    from .shortcuts import shortcut_key
    shortcut_key(sequence)
    combination=sequence[0];code=int(combination.key());mods=combination.keyboardModifiers()
    supported=Qt.KeyboardModifier.NoModifier
    for value in MODIFIERS.values():supported|=value
    if mods&~supported:
        raise ValueError(f'{desktop} does not support that shortcut modifier. Choose another combination.')
    if code<0x1000000:
        character=chr(code).lower()
        if len(character)!=1:raise ValueError('Choose a shortcut with a single key.')
        key={'character':character}
    else:
        name=combination.key().name.removeprefix('Key_')
        if name not in SPECIAL:raise ValueError(f'That key is not supported by the {desktop} shortcut adapter.')
        key={'symbol':SPECIAL[name]}
    return {'key':key,'modifiers':[name for name,value in MODIFIERS.items() if mods&value]}


def decode(value,desktop="GNOME"):
    if (not isinstance(value,dict) or not isinstance(value.get('modifiers'),list) or
            any(not isinstance(name,str) for name in value['modifiers']) or
            len(value['modifiers'])!=len(set(value['modifiers'])) or
            (value.get('symbol') is not None and not isinstance(value['symbol'],str)) or
            (value.get('character') is not None and not isinstance(value['character'],str))):
        raise RuntimeError(f'{desktop} returned an invalid shortcut binding.')
    symbol=value.get('symbol');character=value.get('character')
    if symbol in SYMBOL_TO_QT:code=int(SYMBOL_TO_QT[symbol])
    elif isinstance(character,str) and len(character)==1 and len(character.upper())==1:code=ord(character.upper())
    else:raise ValueError(f'This {desktop} binding cannot be represented in the editor. Review Keyboard Settings.')
    mods=Qt.KeyboardModifier.NoModifier
    for name in value['modifiers']:
        if name not in MODIFIERS:raise ValueError(f'This {desktop} binding uses an unsupported modifier. Review Keyboard Settings.')
        mods|=MODIFIERS[name]
    return QKeySequence(QKeyCombination(mods,Qt.Key(code)))[0].toCombined()
