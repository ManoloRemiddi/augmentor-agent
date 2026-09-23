# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Selectable, streaming rich text with natively painted rounded bubbles."""
import math
import re
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QEvent, QBuffer, QIODevice, QSize, QUrl, QTimer, QSignalBlocker
from PySide6.QtGui import QColor, QFont, QImageReader, QPainter, QTextDocument, QTextTable, QTextFrameFormat, QTextOption
from PySide6.QtWidgets import QApplication, QTextBrowser, QWidget

from .design import ACTION_LABELS,ACTION_ICON_SIZE


class ActionToolTip(QWidget):
    """A compact popup with transparent corners, independent of desktop styling."""
    def __init__(self,parent):
        super().__init__(parent,Qt.WindowType.ToolTip|Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._text='';self.action=None
        font=QFont('DejaVu Sans');font.setPixelSize(11);self.setFont(font)
        self.expiry=QTimer(self);self.expiry.setSingleShot(True);self.expiry.timeout.connect(self.hide)

    def text(self):return self._text

    def show_action(self,action,position):
        self.action=action;self._text=ACTION_LABELS[action];self.setAccessibleName(self._text)
        self.resize(self.fontMetrics().horizontalAdvance(self._text)+16,self.fontMetrics().height()+10)
        screen=QApplication.screenAt(position) or self.screen();area=screen.availableGeometry()
        x=max(area.left(),min(position.x()+12,area.right()-self.width()+1))
        y=position.y()+18
        if y+self.height()>area.bottom():y=position.y()-self.height()-6
        self.move(x,max(area.top(),y));self.show();self.update();self.expiry.start(5000)

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor('#505050'));painter.setBrush(QColor('#363636'))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),6,6)
        painter.setFont(self.font());painter.setPen(QColor('#ffffff'))
        painter.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,self._text)


class Transcript(QTextBrowser):
    def __init__(self):
        super().__init__()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.bubble_color = QColor('#454550')
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips)
        self.action_tooltip=ActionToolTip(self)
        self.pressed_action=None

    def createStandardContextMenu(self, position=None):
        menu=super().createStandardContextMenu(position) if position is not None else super().createStandardContextMenu()
        menu.setStyleSheet(getattr(self,'menu_style','QMenu {background:#202b2c;color:#edf3f3;} QMenu::item:selected {background:#40665e;}'))
        menu.setWindowOpacity(1.0)
        if position is not None:
            href=self.anchorAt(position)
            if QUrl(href).scheme() in ('http','https','mailto','tel','ftp','ssh','sftp'):
                action=menu.addAction('Open link in default application')
                action.triggered.connect(lambda checked=False,url=QUrl(href):self.anchorClicked.emit(url))
        return menu

    def contextMenuEvent(self,event):
        menu=self.createStandardContextMenu(event.pos())
        menu.exec(event.globalPos());menu.deleteLater()

    def action_at(self,position):
        href=self.anchorAt(position)
        return href if re.fullmatch(r'augmentor-(?:(?:copy|branch|edit|think):[0-9]+|code:[0-9]+:[0-9]+)',href) else None

    def mousePressEvent(self,event):
        action=self.action_at(event.position().toPoint())
        if event.button()==Qt.MouseButton.LeftButton and action:
            # QTextBrowser otherwise selects the linked image, painting a
            # selection rectangle over both the icon and its confirmation tick.
            self.pressed_action=action
            cursor=self.textCursor()
            if cursor.hasSelection():
                # setTextCursor scrolls to the old cursor, which may be far
                # outside the viewport. Clear selection without moving the
                # clicked icon or triggering history pagination/follow-tail.
                vertical=self.verticalScrollBar();horizontal=self.horizontalScrollBar()
                y,x=vertical.value(),horizontal.value()
                with QSignalBlocker(vertical),QSignalBlocker(horizontal):
                    cursor.clearSelection();self.setTextCursor(cursor)
                    vertical.setValue(y);horizontal.setValue(x)
            event.accept();return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self.pressed_action:
            event.accept();return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            pressed=self.pressed_action;self.pressed_action=None
            action=self.action_at(event.position().toPoint())
            if pressed:
                if action==pressed:self.anchorClicked.emit(QUrl(action))
                event.accept();return
            if action:
                event.accept();return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.action_at(event.position().toPoint()):
            self.mousePressEvent(event);return
        super().mouseDoubleClickEvent(event)

    def action_link(self,action,index,color,icon=None):
        label=ACTION_LABELS[action]
        source=f'augmentor-icon:/{icon or action}/{color.lstrip("#")}/{self.devicePixelRatioF()}'
        hint=label
        if getattr(self,'touch_targets',False):
            return f'<a href="augmentor-{action}:{index}" title="{hint}"><img src="{source}" width="44" height="44" alt="{label}" /></a>'
        return f'<a href="augmentor-{action}:{index}" title="{hint}"><img src="{source}" width="{ACTION_ICON_SIZE}" height="{ACTION_ICON_SIZE}" alt="{label}" /></a>'

    def loadResource(self,kind,url):
        if kind==QTextDocument.ResourceType.ImageResource and url.scheme()=='augmentor-icon':
            match=re.fullmatch(r'/(copy|branch|edit|check)/([0-9a-fA-F]{6})/([0-9.]+)',url.path())
            if not match:return None
            action,color,scale=match.groups()
            ratio=max(1,min(4,float(scale)))
            svg=(Path(__file__).parent/'assets'/f'{action}.svg').read_bytes().replace(b'currentColor',('#'+color).encode())
            size=math.ceil(ACTION_ICON_SIZE*ratio)
            buffer=QBuffer();buffer.setData(svg);buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            reader=QImageReader(buffer,b'svg');reader.setScaledSize(QSize(size,size))
            image=reader.read();buffer.close()
            if getattr(self,'touch_targets',False):
                from PySide6.QtGui import QImage,QPainter
                target=QImage(round(44*ratio),round(44*ratio),QImage.Format.Format_ARGB32_Premultiplied);target.fill(Qt.GlobalColor.transparent)
                painter=QPainter(target);offset=round((44*ratio-size)/2);painter.drawImage(offset,offset,image);painter.end();image=target
            image.setDevicePixelRatio(ratio)
            return image
        return super().loadResource(kind,url)

    def viewportEvent(self,event):
        if event.type()==QEvent.Type.ToolTip:
            action=QUrl(self.anchorAt(event.pos())).scheme().removeprefix('augmentor-')
            if action in ACTION_LABELS:
                self.action_tooltip.show_action(action,event.globalPos())
                return True
        if event.type() in (QEvent.Type.Leave,QEvent.Type.MouseButtonPress,QEvent.Type.Wheel):self.action_tooltip.hide()
        if event.type()==QEvent.Type.MouseMove and self.action_tooltip.isVisible():
            action=QUrl(self.anchorAt(event.position().toPoint())).scheme().removeprefix('augmentor-')
            if action!=self.action_tooltip.action:self.action_tooltip.hide()
        return super().viewportEvent(event)

    def hideEvent(self,event):
        self.action_tooltip.hide()
        self.pressed_action=None
        super().hideEvent(event)

    def bubbles(self):
        return [frame for frame in self.document().rootFrame().childFrames()
                if isinstance(frame, QTextTable) and frame.format().border()==0
                and frame.format().cellPadding()==10]

    def setHtml(self, text):
        self.action_tooltip.hide()
        super().setHtml(text)
        for table in self.bubbles():
            fmt = table.format()
            fmt.setPosition(QTextFrameFormat.Position.InFlow)
            fmt.setAlignment(Qt.AlignmentFlag.AlignRight)
            fmt.setTopMargin(14)
            fmt.setBottomMargin(14)
            table.setFormat(fmt)
        # Formatting the bubbles after setHtml can leave Qt's following blocks
        # with zero width/height in long chats. Streaming hides this because it
        # inserts text incrementally; the final rebuild must lay out every block.
        document = self.document()
        document.markContentsDirty(0, document.characterCount())
        document.documentLayout().documentSize()

    def bubble_rects(self):
        layout = self.document().documentLayout()
        for table in self.bubbles():
            # cursorRect includes the actual viewport origin and scroll offset;
            # use the first line's document position to map the frame with it.
            cursor = table.firstCursorPosition()
            block = layout.blockBoundingRect(cursor.block())
            line = cursor.block().layout().lineAt(0)
            offset = self.cursorRect(cursor).top() - block.top() - line.y()
            # Qt's table frame rectangle includes margins but reports a shifted
            # origin. Bound the text blocks, then add the actual cell padding.
            rect = QRectF(block)
            current = cursor.block().next()
            while current.isValid() and current.position() <= table.lastPosition():
                rect = rect.united(layout.blockBoundingRect(current))
                current = current.next()
            padding = table.format().cellPadding()
            rect.adjust(-padding, -padding, padding, padding)
            rect.translate(-self.horizontalScrollBar().value(), offset)
            yield rect

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.bubble_color)
        for rect in self.bubble_rects():
            if rect.intersects(QRectF(event.rect())):
                painter.drawRoundedRect(rect, 13, 13)
        painter.end()
        super().paintEvent(event)
