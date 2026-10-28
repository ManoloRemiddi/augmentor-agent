#!/usr/bin/python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Generate authored rich Office fixtures with the existing isolated native exporter.

No personal document, profile, model, network or installed application is used.
The native exporter is a fixture producer; previews still use the Wasm provider.
"""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
from xml.sax.saxutils import escape
import zlib

spec = importlib.util.spec_from_file_location('fixture_native_office',
    Path(__file__).with_name('native-sandbox-probe.py'))
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
MARKER = 'AUGMENTOR_AUTHORED_NATIVE'


def authored_png():
    """A deterministic colour-bar test image; no external media or font input."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = []
    for y in range(48):
        rows.append(b'\0' + b''.join(bytes((220, 40, 60) if x < 16 else
            (35, 160, 100) if x < 32 else (40, 90, 210)) for x in range(48)))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 48, 48, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))


def picture(name, anchor='paragraph', x=0, y=0):
    image = base64.b64encode(authored_png()).decode()
    return (f'<draw:frame draw:name="{name}" text:anchor-type="{anchor}" '
            f'svg:x="{x}cm" svg:y="{y}cm" svg:width="2cm" svg:height="2cm">'
            '<draw:image draw:mime-type="image/png"><office:binary-data>' + image +
            '</office:binary-data></draw:image></draw:frame>')


def paragraph(text, style='Body'):
    return '<text:p text:style-name="' + style + '">' + escape(text) + '</text:p>'


def document(flat):
    namespaces = {
        'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
        'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
        'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
        'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
        'draw': 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
        'presentation': 'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',
        'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
        'svg': 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
        'number': 'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0',
        'of': 'urn:oasis:names:tc:opendocument:xmlns:of:1.2',
    }
    kind = {'fodt': 'text', 'fods': 'spreadsheet', 'fodp': 'presentation'}[flat]
    header = '<office:document ' + ' '.join(f'xmlns:{k}="{v}"' for k, v in namespaces.items())
    header += f' office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.{kind}">'
    fonts = ''.join(f'<style:font-face style:name="{name}" svg:font-family="{name}"/>'
                    for name in ['Liberation Sans', 'Liberation Serif', 'Liberation Mono', native.MISSING_FONT])
    styles = '<office:font-face-decls>' + fonts + '</office:font-face-decls><office:styles>'
    styles += '<style:default-style style:family="paragraph"><style:text-properties style:font-name="Liberation Sans" fo:font-size="12pt"/></style:default-style>'
    styles += '</office:styles><office:automatic-styles>'
    for name, family, size in [('Body', 'Liberation Sans', 12), ('Serif', 'Liberation Serif', 12),
                               ('Code', 'Liberation Mono', 10), ('Title', 'Liberation Sans', 18),
                               ('Missing', native.MISSING_FONT, 12)]:
        styles += f'<style:style style:name="{name}" style:family="paragraph"><style:text-properties style:font-name="{family}" fo:font-size="{size}pt"/></style:style>'
    styles += '<style:style style:name="Next" style:family="paragraph"><style:paragraph-properties fo:break-before="page"/></style:style>'
    styles += '<style:style style:name="Cell" style:family="table-cell" style:data-style-name="TwoDecimals"><style:table-cell-properties fo:padding="0.12cm" fo:border="0.02cm solid #445566"/></style:style>'
    styles += '<number:number-style style:name="TwoDecimals"><number:number number:decimal-places="2" number:min-integer-digits="1"/></number:number-style>'
    styles += '<style:style style:name="Column" style:family="table-column"><style:table-column-properties style:column-width="4cm"/></style:style>'
    styles += '<style:style style:name="Sheet" style:family="table" style:master-page-name="Standard"><style:table-properties table:display="true"/></style:style>'
    styles += '<style:style style:name="Slide" style:family="drawing-page"><style:drawing-page-properties presentation:background-visible="true"/></style:style>'
    dimensions = ('28cm', '15.75cm') if flat == 'fodp' else ('21cm', '29.7cm')
    styles += f'<style:page-layout style:name="Page"><style:page-layout-properties fo:page-width="{dimensions[0]}" fo:page-height="{dimensions[1]}" fo:margin="1.5cm" style:scale-to-pages-x="1" style:scale-to-pages-y="1"/></style:page-layout>'
    styles += '</office:automatic-styles><office:master-styles><style:master-page style:name="Standard" style:page-layout-name="Page">'
    if flat == 'fodt':
        styles += '<style:header>' + paragraph('RICH_HEADER_PRESERVED', 'Code') + '</style:header>'
        styles += '<style:footer>' + paragraph('RICH_FOOTER_PRESERVED', 'Code') + '</style:footer>'
    styles += '</style:master-page></office:master-styles>'
    if flat == 'fodt':
        body = '<office:text>'
        for page in range(1, 4):
            if page != 1:
                body += '<text:p text:style-name="Next"/>'
            body += paragraph(MARKER + '_WRITER', 'Title')
            body += paragraph(f'RICH_WRITER_PAGE_{page}', 'Serif')
            body += paragraph('Italian text: caffè, più, città; Greek: Ω; euro: €.', 'Body')
            body += paragraph('CODE_SAMPLE: total = units * price', 'Code')
            body += '<table:table table:name="AuthoredTable' + str(page) + '"><table:table-column table:style-name="Column" table:number-columns-repeated="3"/>'
            for row in range(1, 5):
                body += '<table:table-row>' + ''.join('<table:table-cell table:style-name="Cell" office:value-type="string">' +
                    paragraph(f'ROW_{page}_{row}_{column}') + '</table:table-cell>' for column in range(1, 4)) + '</table:table-row>'
            body += '</table:table><text:p>' + picture(f'WriterImage{page}') + '</text:p>'
            body += paragraph('RICH_FONT_FALLBACK', 'Missing')
        body += '</office:text>'
    elif flat == 'fods':
        def cell(value, formula=None):
            attributes = ' office:value-type="string"' if isinstance(value, str) else f' office:value-type="float" office:value="{value}"'
            if formula:
                attributes += ' table:formula="' + escape(formula, {'"': '&quot;'}) + '"'
            return '<table:table-cell table:style-name="Cell"' + attributes + '>' + paragraph(str(value)) + '</table:table-cell>'
        def row(values):
            return '<table:table-row>' + ''.join(values) + '</table:table-row>'
        body = '<office:spreadsheet><table:table table:name="Numbers" table:style-name="Sheet">'
        body += '<table:table-column table:style-name="Column" table:number-columns-repeated="4"/>'
        body += '<table:table-row><table:table-cell table:style-name="Cell" table:number-columns-spanned="4" office:value-type="string">' + paragraph(MARKER + '_CALC') + '</table:table-cell><table:covered-table-cell table:number-columns-repeated="3"/></table:table-row>'
        body += row([cell('Item'), cell('Units'), cell('Price'), cell('Amount')])
        body += row([cell('RICH_ITEM_ALPHA'), cell(3), cell(19.5), cell(58.5, 'of:=[.B3]*[.C3]')])
        body += row([cell('RICH_ITEM_BETA'), cell(2), cell(12.25), cell(24.5, 'of:=[.B4]*[.C4]')])
        body += row([cell('RICH_TOTAL'), cell(''), cell(''), cell(83, 'of:=SUM([.D3:.D4])')])
        body += '<table:table-row table:visibility="collapse">' + cell('RICH_HIDDEN_SHOULD_NOT_RENDER') + '</table:table-row>'
        body += '</table:table><table:table table:name="Review" table:style-name="Sheet">'
        body += '<table:table-column table:style-name="Column" table:number-columns-repeated="2"/>'
        body += row([cell('RICH_SECOND_SHEET'), cell(41.5, 'of:=[Numbers.D5]/2')])
        body += row([cell('RICH_LITERAL_TEXT'), cell('=2+2 is literal text')])
        body += '</table:table></office:spreadsheet>'
    else:
        body = '<office:presentation>'
        for page in range(1, 4):
            body += f'<draw:page draw:name="Authored{page}" draw:style-name="Slide" draw:master-page-name="Standard">'
            for x, y, width, height, text, style in [
                (1, 1, 26, 2, MARKER + '_DECK', 'Title'),
                (1, 3, 12, 4, f'RICH_DECK_PAGE_{page}', 'Serif'),
                (14, 3, 12, 4, 'RICH_RIGHT_COLUMN', 'Body'),
                (1, 12, 26, 1, f'RICH_SLIDE_FOOTER_{page}', 'Code')]:
                body += f'<draw:frame svg:x="{x}cm" svg:y="{y}cm" svg:width="{width}cm" svg:height="{height}cm"><draw:text-box>' + paragraph(text, style) + '</draw:text-box></draw:frame>'
            body += picture(f'SlideImage{page}', 'page', 23, 8)
            body += '<presentation:notes><draw:frame svg:x="1cm" svg:y="1cm" svg:width="10cm" svg:height="2cm"><draw:text-box>' + paragraph('RICH_NOTES_SHOULD_NOT_RENDER') + '</draw:text-box></draw:frame></presentation:notes>'
            body += '</draw:page>'
        body += '</office:presentation>'
    return ('<?xml version="1.0" encoding="UTF-8"?>' + header + styles + '<office:body>' + body + '</office:body></office:document>').encode()


def generate(root):
    if not root.is_dir() or root.is_symlink() or list(root.iterdir()):
        raise ValueError('Use a fresh private fixture directory.')
    rows = []
    for extension, (flat, office_filter, _) in native.FORMATS.items():
        seed = root / ('seed-' + extension + '.' + flat)
        seed.write_bytes(document(flat))
        scratch = root / ('create-' + extension)
        native.run(scratch, native.office_command(scratch, seed, extension + ':' + office_filter))
        output = root / ('authored.' + extension)
        output.write_bytes((scratch / 'work/out' / ('source.' + extension)).read_bytes())
        kind = 'writer' if flat == 'fodt' else 'calc' if flat == 'fods' else 'deck'
        required = {'writer': ['RICH_WRITER_PAGE_1', 'RICH_WRITER_PAGE_3', 'RICH_HEADER_PRESERVED',
                               'RICH_FOOTER_PRESERVED', 'ROW_2_4_3', 'RICH_FONT_FALLBACK'],
                    'calc': ['RICH_ITEM_ALPHA', 'RICH_TOTAL', '83.00', 'RICH_SECOND_SHEET', '41.50', '=2+2 is literal text'],
                    'deck': ['RICH_DECK_PAGE_1', 'RICH_DECK_PAGE_3', 'RICH_RIGHT_COLUMN', 'RICH_SLIDE_FOOTER_3']}[kind]
        absent = {'writer': [], 'calc': ['RICH_HIDDEN_SHOULD_NOT_RENDER'],
                  'deck': ['RICH_NOTES_SHOULD_NOT_RENDER']}[kind]
        rows.append({'extension': extension, 'kind': kind, 'file': output.name,
                     'bytes': output.stat().st_size, 'sha256': native.digest(output),
                     'requiredText': [MARKER, *required], 'absentText': absent,
                     'minimumPages': 2 if kind == 'calc' else 3,
                     'minimumImages': 0 if kind == 'calc' else 3})
    result = {'schema': 'augmentor-rich-office-fixtures/1', 'fixtures': rows,
              'scope': 'Six authored rich documents exported through isolated native LibreOffice; no owner inputs.'}
    (root / 'fixtures.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    os.umask(0o077)
    result = generate(Path(sys.argv[1]).absolute())
    print(json.dumps({'fixtures': len(result['fixtures']), 'ownerDataUsed': False}))
