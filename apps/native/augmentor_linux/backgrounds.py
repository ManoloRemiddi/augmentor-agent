# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Local raster uploads, bounded portable image data, and deterministic palettes."""
import base64
import binascii
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize, Qt
from PySide6.QtGui import QImage, QImageReader, QPainter, QColor

MAX_IMAGE_BYTES = 4 * 1024 * 1024


@lru_cache(maxsize=4)
def decode_background(encoded):
    if not isinstance(encoded,str) or len(encoded)>MAX_IMAGE_BYTES*4//3+4:
        raise ValueError('Background image is too large.')
    try:raw=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error) as error:raise ValueError('Invalid background image data.') from error
    if not raw or len(raw)>MAX_IMAGE_BYTES:raise ValueError('Invalid background image size.')
    buffer=QBuffer();buffer.setData(QByteArray(raw));buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader=QImageReader(buffer)
    size=reader.size()
    if bytes(reader.format()).lower() not in (b'jpeg',b'jpg',b'png',b'webp') or size.width()<=0 or size.height()<=0 or max(size.width(),size.height())>1600:
        raise ValueError('Shared backgrounds must be PNG, JPEG, or WebP up to 1600 pixels per side.')
    image=reader.read()
    if image.isNull():raise ValueError('Cannot decode the background image.')
    return image


def palette_from_image(image, dark=True):
    small=image.scaled(48,48,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
    buckets=defaultdict(lambda:[0.,0.,0.])
    for y in range(small.height()):
        for x in range(small.width()):
            colour=small.pixelColor(x,y);h,s,v,_=colour.getHsvF()
            if h<0 or s<.08 or v<.07:continue
            key=int(h*24)%24;weight=.25+s
            bucket=buckets[key];bucket[0]+=weight;bucket[1]+=s*weight;bucket[2]+=1
    if buckets:
        dominant=max(buckets,key=lambda k:buckets[k][0])
        def score(k):
            distance=min(abs(k-dominant),24-abs(k-dominant))/12
            return buckets[k][0]*(.35+distance)*(.5+buckets[k][1]/buckets[k][0])
        accent=max(buckets,key=score)
        hue=round((dominant+.5)*15)%360;accent_hue=round((accent+.5)*15)%360
        saturation=round(max(20,min(72,buckets[accent][1]/buckets[accent][0]*100)))
    else:hue,accent_hue,saturation=210,210,0
    tint=QColor.fromHslF(accent_hue/360,saturation/100,.75 if dark else .28).name()
    link=QColor.fromHslF(hue/360,saturation/100*.7,.8 if dark else .25).name()
    return dict(hue=hue,accent_hue=accent_hue,saturation=saturation,brightness=0,accent_brightness=0,
                opacity=100,format_colours={'heading':tint,'link':link,'emphasis':'#fff0e3' if dark else '#243840'})


def upload_background(path, dark=True):
    path=Path(path)
    if path.stat().st_size>20*1024*1024:raise ValueError('Choose an image smaller than 20 MiB.')
    reader=QImageReader(str(path));reader.setAutoTransform(True)
    size=reader.size()
    if bytes(reader.format()).lower() not in (b'jpeg',b'jpg',b'png',b'webp'):
        raise ValueError('Choose a PNG, JPEG, or WebP image.')
    if size.width()<=0 or size.height()<=0 or size.width()*size.height()>32_000_000:
        raise ValueError('Choose an image with no more than 32 megapixels.')
    if max(size.width(),size.height())>1600:
        reader.setScaledSize(size.scaled(QSize(1600,1600),Qt.AspectRatioMode.KeepAspectRatio))
    image=reader.read()
    if image.isNull():raise ValueError('This image could not be opened.')
    if max(image.width(),image.height())>1600:
        image=image.scaled(1600,1600,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
    opaque=QImage(image.size(),QImage.Format.Format_RGB32);opaque.fill(QColor('#223038'))
    painter=QPainter(opaque);painter.drawImage(0,0,image);painter.end()
    output=QByteArray();buffer=QBuffer(output);buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not opaque.save(buffer,'JPEG',88):raise ValueError('Could not prepare this background.')
    encoded=base64.b64encode(bytes(output)).decode('ascii')
    decode_background(encoded)
    return {**palette_from_image(opaque,dark),'background':'uploaded','background_image':encoded}


def butterfly_colours(image):
    """Representative image colours, lifted enough for tiny exterior wings."""
    small=image.scaled(48,48,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
    bins=defaultdict(lambda:[0,0,0,0])
    for y in range(small.height()):
        for x in range(small.width()):
            c=small.pixelColor(x,y);r,g,b=c.red(),c.green(),c.blue()
            bucket=bins[(r//40,g//40,b//40)]
            bucket[0]+=1;bucket[1]+=r;bucket[2]+=g;bucket[3]+=b
    result=[]
    for count,r,g,b in sorted(bins.values(),reverse=True)[:9]:
        c=QColor(round(r/count),round(g/count),round(b/count))
        h,s,l,_=c.getHslF()
        c=QColor.fromHslF(max(0.,h),s,max(.56,min(.78,l)))
        result.append(c.name())
    return tuple(result)


@lru_cache(maxsize=4)
def uploaded_butterfly_colours(encoded):
    return butterfly_colours(decode_background(encoded))
