# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Versioned, data-only desktop skins. Never serialize unrelated preferences."""
from copy import deepcopy
import json
import re

LIMIT = 6 * 1024 * 1024
RANGES = {'hue': (0,359), 'accent_hue': (0,359), 'brightness': (-15,15),
          'accent_brightness': (-15,15), 'saturation': (0,100), 'opacity': (35,100)}
BASE = dict(theme='dark', hue=190, brightness=0, accent_hue=160,
            accent_brightness=0, saturation=48, opacity=85, animation=True,
            flares=True, effect='plasma', background='none', background_image='', format_colours={})
BUILTINS = {
    'Futuristic': BASE,
    'Blossom lake': {**BASE, 'hue':205, 'accent_hue':20, 'saturation':48,
                     'opacity':100, 'effect':'butterflies-large', 'background':'blossom-lake',
                     'format_colours':{'heading':'#f0b69b','link':'#a9cbd4','emphasis':'#fff0e3'}},

}


def skin_document(name, values):
    return validate_skin({'format':'augmentor-skin', 'version':2 if values.get('background')=='uploaded' else 1, 'name':name,
                          'appearance':{key:deepcopy(values.get(key, default)) for key,default in BASE.items()}})


def validate_skin(data):
    if not isinstance(data,dict) or set(data) != {'format','version','name','appearance'}:
        raise ValueError('This is not an Augmentor skin file.')
    if data['format'] != 'augmentor-skin' or type(data['version']) is not int or data['version'] not in (1,2):
        raise ValueError('Unsupported skin format or version.')
    name=data['name']
    if not isinstance(name,str) or not name.strip() or len(name)>80 or any(ord(c)<32 for c in name):
        raise ValueError('Use a skin name of 1–80 characters.')
    values=data['appearance']
    if isinstance(values,dict) and 'background' not in values:
        values={**values,'background':'none'}
    if isinstance(values,dict) and 'background_image' not in values:
        values={**values,'background_image':''}
    if not isinstance(values,dict) or set(values) != set(BASE):
        raise ValueError('The skin has missing or unsupported appearance settings.')
    for key,(lo,hi) in RANGES.items():
        if type(values[key]) is not int or not lo<=values[key]<=hi:
            raise ValueError(f'{key} must be a whole number from {lo} to {hi}.')
    for key in ('animation','flares'):
        if type(values[key]) is not bool:raise ValueError(f'{key} must be true or false.')
    if values['theme'] not in ('light','dark') or values['effect'] not in ('plasma','butterflies','butterflies-large','none'):
        raise ValueError('Unsupported theme or activity effect.')
    if values['background'] not in ('none','blossom-lake','uploaded'):
        raise ValueError('Unsupported background image.')
    if not isinstance(values['background_image'],str):raise ValueError('Invalid background image data.')
    if values['background']=='uploaded':
        if data['version']!=2:raise ValueError('Uploaded backgrounds require skin version 2.')
        from .backgrounds import decode_background
        decode_background(values['background_image'])
    elif values['background_image']:
        raise ValueError('Unexpected background image data.')
    colours=values['format_colours']
    roles={'heading','link','emphasis','keyword','string','number','name','comment','operator'}
    if not isinstance(colours,dict) or not set(colours)<=roles or any(not isinstance(v,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',v) for v in colours.values()):
        raise ValueError('Formatting colours must be supported roles with #RRGGBB values.')
    return {**deepcopy(data),'name':name.strip(),'appearance':deepcopy(values)}


def read_skin(path):
    with open(path,'rb') as source:raw=source.read(LIMIT+1)
    if len(raw)>LIMIT:raise ValueError('Skin files must be smaller than 6 MiB.')
    try:return validate_skin(json.loads(raw))
    except (UnicodeError,RecursionError) as error:raise ValueError('Invalid skin file.') from error


def write_skin(path,name,values):
    document=skin_document(name,values)
    from PySide6.QtCore import QSaveFile, QIODevice
    target=QSaveFile(str(path))
    raw=(json.dumps(document,indent=2)+'\n').encode()
    if not target.open(QIODevice.OpenModeFlag.WriteOnly):raise OSError(target.errorString())
    if target.write(raw)!=len(raw) or not target.commit():raise OSError(target.errorString())
