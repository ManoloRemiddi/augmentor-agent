# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Safe Qt Markdown with language-aware code colours for both themes."""
from functools import lru_cache
import re
import uuid
from PySide6.QtGui import QColor, QFont, QTextCursor, QTextDocument, QTextFormat, QTextTable, QTextLength, QTextCharFormat
from pygments import lex
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.token import Comment, Keyword, String, Number, Name, Operator
from pygments.util import ClassNotFound

PALETTES = {
    'dark': ('#c4a7ff', '#a6da95', '#f5a97f', '#8bd5ef', '#a5adcb', '#ed8796', '#202733'),
    'light': ('#6639ba', '#236b35', '#9a4600', '#005c85', '#596579', '#a82c46', '#edf1f7'),
}


FORMAT_ROLES=('heading','link','emphasis','keyword','string','number','name','comment','operator')
FORMAT_LABELS=('Headings','Links','Bold text','Code keywords','Code strings','Code numbers','Code functions','Code comments','Code operators')

def format_defaults(theme='dark',accent='#a6d6c8'):
    return dict(zip(FORMAT_ROLES,(accent,accent,'#edf3f3' if theme=='dark' else '#152b2c',*PALETTES[theme][:6])))


def prepare_markup(text):
    """Keep code literal; recognize only colour-only span tags in prose."""
    prefix='AUGCOLOR'+uuid.uuid4().hex
    marks=[];lines=[];fence=None
    tag=re.compile(r'(`+)[^`]*?\1|<span\s+style=(["\'])\s*color\s*:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\s*;?\s*\2\s*>|</span\s*>',re.I)
    def replace(m):
        if m.group(1):return m.group(0)
        marker=prefix+str(len(marks))+'END'
        marks.append((marker,m.group(3)))
        return marker
    for line in text.splitlines(keepends=True):
        boundary=re.match(r'^ {0,3}(`{3,}|~{3,})',line)
        if boundary:
            chars=boundary.group(1)
            if fence is None:fence=chars
            elif chars[0]==fence[0] and len(chars)>=len(fence):fence=None
            lines.append(line);continue
        if fence or line.startswith(('    ','\t')):lines.append(line);continue
        line=tag.sub(replace,line)
        # Chat output uses intentional line breaks (e.g. a source below an item).
        if line.endswith('\n') and line.strip():line=line.rstrip('\r\n')+'  \n'
        lines.append(line)
    return ''.join(lines),marks


def apply_spans(doc,marks):
    stack=[];ranges=[];removals=[]
    for marker,color in marks:
        found=doc.find(marker)
        if found.isNull():continue
        start,end=found.selectionStart(),found.selectionEnd();removals.append((start,end))
        if color:stack.append((end,color))
        elif stack:
            begin,color=stack.pop();ranges.append((begin,start,color))
    # Unclosed streamed spans apply to the current end, then close on the next render.
    ranges.extend((begin,doc.characterCount()-1,color) for begin,color in stack)
    for start,end,color in sorted(ranges):
        cursor=QTextCursor(doc);cursor.setPosition(start);cursor.setPosition(end,QTextCursor.MoveMode.KeepAnchor)
        fmt=QTextCharFormat();fmt.setForeground(QColor(color));cursor.mergeCharFormat(fmt)
    for start,end in sorted(removals,reverse=True):
        cursor=QTextCursor(doc);cursor.setPosition(start);cursor.setPosition(end,QTextCursor.MoveMode.KeepAnchor);cursor.removeSelectedText()


def token_color(token, palette):
    if token in Comment:return palette[4]
    if token in Keyword:return palette[0]
    if token in String:return palette[1]
    if token in Number:return palette[2]
    if token in Name.Function or token in Name.Class or token in Name.Builtin:return palette[3]
    if token in Operator:return palette[5]
    return None


@lru_cache(maxsize=128)
def render_markdown(text, theme='dark', accent='#a6d6c8', colours=(), code_prefix=None, copied_block=None):
    doc=QTextDocument()
    font=QFont('DejaVu Sans');font.setPixelSize(13);doc.setDefaultFont(font)
    source_codes=code_blocks(text) if code_prefix is not None else []
    text,marks=prepare_markup(text)
    doc.setMarkdown(text, QTextDocument.MarkdownFeature.MarkdownDialectGitHub |
                    QTextDocument.MarkdownFeature.MarkdownNoHTML)
    colours={**format_defaults(theme,accent),**dict(colours)}
    palette=tuple(colours[key] for key in FORMAT_ROLES[3:])+ (PALETTES[theme][6],)
    block=doc.begin()
    code=[]
    while block.isValid():
        fmt=block.blockFormat()
        cursor=QTextCursor(block)
        is_code=fmt.nonBreakableLines() or fmt.hasProperty(QTextFormat.Property.BlockCodeFence)
        if is_code:
            if code and code[0].blockFormat().property(QTextFormat.Property.BlockCodeLanguage)!=fmt.property(QTextFormat.Property.BlockCodeLanguage):
                highlight(doc,code,palette);code=[]
            code.append(block)
            fmt.setBackground(QColor(palette[6]));fmt.setLeftMargin(10);fmt.setRightMargin(10)
            cursor.setBlockFormat(fmt)
        else:
            if code:highlight(doc,code,palette);code=[]
            fmt.setTopMargin(5);fmt.setBottomMargin(13);cursor.setBlockFormat(fmt)
            if fmt.property(QTextFormat.Property.BlockQuoteLevel):
                fmt.setLeftMargin(14);fmt.setTopMargin(7);fmt.setBottomMargin(7)
                cursor.setBlockFormat(fmt)
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                char=cursor.charFormat();char.setForeground(QColor(palette[4]));cursor.mergeCharFormat(char)
            heading=fmt.headingLevel()
            if heading:
                fmt.setTopMargin(12);fmt.setBottomMargin(7);cursor.setBlockFormat(fmt)
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                char=cursor.charFormat();char.setForeground(QColor(colours['heading']));cursor.mergeCharFormat(char)
        block=block.next()
    if code:highlight(doc,code,palette)
    def style_tables(frame):
        for child in frame.childFrames():
            if isinstance(child,QTextTable):
                fmt=child.format();fmt.setBorder(1);fmt.setBorderBrush(QColor(palette[4]))
                fmt.setCellPadding(4);fmt.setCellSpacing(0)
                fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength,100))
                fmt.setColumnWidthConstraints([QTextLength(QTextLength.Type.PercentageLength,100/child.columns())]*child.columns())
                child.setFormat(fmt)
            style_tables(child)
    style_tables(doc.rootFrame())
    # Markdown may create links/images but cannot inject HTML or UI actions.
    # Work backwards so replacing image objects preserves all earlier offsets.
    fragments=[];block=doc.begin()
    while block.isValid():
        iterator=block.begin()
        while not iterator.atEnd():
            fragment=iterator.fragment()
            if fragment.isValid():fragments.append(fragment)
            iterator+=1
        block=block.next()
    for fragment in reversed(fragments):
        fmt=fragment.charFormat();cursor=QTextCursor(doc)
        cursor.setPosition(fragment.position());cursor.setPosition(fragment.position()+fragment.length(),QTextCursor.MoveMode.KeepAnchor)
        if fmt.isImageFormat():
            alt=fmt.property(QTextFormat.Property.ImageAltText) or 'Image'
            cursor.insertText(str(alt))
        elif fmt.isAnchor():
            href=fmt.anchorHref()
            if not re.match(r'^(https?|mailto|tel|ftp|ssh|sftp):',re.sub(r'[\x00-\x20]','',href),re.I):
                fmt.setAnchor(False);fmt.setAnchorHref('')
            else:fmt.setForeground(QColor(colours['link']))
            cursor.setCharFormat(fmt)
        elif fmt.fontWeight()>=QFont.Weight.Bold and not fragment.charFormat().fontFixedPitch():
            # Code token colours take precedence over prose emphasis.
            if not cursor.block().blockFormat().headingLevel() and 'mono' not in ' '.join(fmt.fontFamilies() or []).lower():
                color=QTextCharFormat();color.setForeground(QColor(colours['emphasis']));cursor.mergeCharFormat(color)
    apply_spans(doc,marks)
    output=re.search(r'<body[^>]*>(.*)</body>',doc.toHtml(),re.S).group(1)
    starts={};line=0
    for index,source in enumerate(source_codes):
        starts[line]=index;line+=max(1,len(source.split('\n')))
    line_index=iter(range(output.count('<pre ')))
    def code_frame(match):
        frames=[];parts=[]
        def finish():
            if parts:frames.append(f'<table width="100%" border="0" cellspacing="0" cellpadding="12" bgcolor="{palette[6]}"><tr><td>'+''.join(parts)+'</td></tr></table>')
        for pre in re.findall(r'<pre\b.*?</pre>',match.group(0),re.S):
            index=starts.get(next(line_index))
            if index is not None:
                finish();parts=[]
                label='✓ Copied' if index==copied_block else '▣ Copy'
                parts.append(f'<p align="right" style="margin:0 0 8px 0"><a href="augmentor-code:{code_prefix}:{index}" style="color:{accent};text-decoration:none">{label}</a></p>')
            pre=pre.replace('<pre style="','<p style="white-space:pre-wrap; ').replace('</pre>','</p>')
            parts.append(pre)
        finish();return ''.join(frames)
    return re.sub(r'(?:<pre\b.*?</pre>\s*)+',code_frame,output,flags=re.S)


def highlight(doc, blocks, palette):
    language=blocks[0].blockFormat().property(QTextFormat.Property.BlockCodeLanguage) or 'text'
    try:lexer=get_lexer_by_name((str(language).split() or ['text'])[0],stripnl=False,ensurenl=False)
    except ClassNotFound:lexer=TextLexer(stripnl=False,ensurenl=False)
    text='\n'.join(block.text() for block in blocks)
    if len(text)>100000:return
    cursor=QTextCursor(doc);position=blocks[0].position()
    for token,value in lex(text,lexer):
        # QTextCursor positions count UTF-16 units, including astral symbols.
        length=len(value.encode('utf-16-le'))//2
        color=token_color(token,palette)
        if color:
            cursor.setPosition(position);cursor.setPosition(position+length,QTextCursor.MoveMode.KeepAnchor)
            fmt=cursor.charFormat();fmt.setForeground(QColor(color));cursor.mergeCharFormat(fmt)
        position+=length


def code_blocks_original(doc):
    blocks=[];current=[];block=doc.begin()
    while block.isValid():
        fmt=block.blockFormat()
        if fmt.nonBreakableLines() or fmt.hasProperty(QTextFormat.Property.BlockCodeFence):
            current.append(block.text())
        elif current:blocks.append('\n'.join(current));current=[]
        block=block.next()
    if current:blocks.append('\n'.join(current))
    return blocks


def code_blocks(text):
    # Preserve fenced source exactly, including indentation and literal markup.
    result=[];fence=None;current=[]
    for line in text.splitlines():
        match=re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$',line)
        if fence:
            if match and match[1][0]==fence[0] and len(match[1])>=len(fence) and not match[2].strip():
                result.append('\n'.join(current));fence=None;current=[]
            else:current.append(line)
        elif match:fence=match[1]
    if fence:result.append('\n'.join(current))
    if result:return result
    doc=QTextDocument()
    doc.setMarkdown(text,QTextDocument.MarkdownFeature.MarkdownDialectGitHub|QTextDocument.MarkdownFeature.MarkdownNoHTML)
    return code_blocks_original(doc)
