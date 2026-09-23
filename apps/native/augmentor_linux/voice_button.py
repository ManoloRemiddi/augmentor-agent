# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One voice control: press to silence, hold to record, release to send."""
import math
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer, Signal, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QPushButton


class VoiceButton(QPushButton):
    hands_free_requested = Signal()
    hold_started = Signal()
    cancelled = Signal()
    HOLD_MS = 230
    LOCK_DISTANCE = 24
    TIPS = {
        'off': 'Hold to talk · ← Lock · → Hands-free',
        'connecting': 'Preparing voice…',
        'ready': 'Hold to talk · ← Lock · → Hands-free',
        'speaking': 'Click to stop speech · Hold to reply',
        'listening': 'Release to send · ← Lock · → Hands-free',
        'recognizing': 'Recognizing…',
        'thinking': 'Thinking… · Hold to follow up',
        'error': 'Voice unavailable · Click to retry',
        'disconnected': 'Voice disconnected · Click to reconnect',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoRepeat(False)
        self.accent = QColor('#b79de5')
        self.animated = True
        self.phase = 0.
        self.hovered = False
        self.hold_elapsed = False
        self.hands_free = False
        self.recording_available = False
        self.locked = False
        self.lock_release_pending = False
        self.hands_free_release_pending = False
        self.press_position = None
        self.drag_origin=None
        self.drag_offset=0.
        self.snap=QVariantAnimation(self);self.snap.setDuration(150)
        self.snap.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.snap.valueChanged.connect(self.move_drag)
        self.snap.finished.connect(self.finish_snap)
        self.elapsed = 0.
        self.max_seconds = 600.
        self.levels = [0.] * 11
        self.hold_timer = QTimer(self)
        self.hold_timer.setSingleShot(True)
        self.hold_timer.setInterval(self.HOLD_MS)
        self.hold_timer.timeout.connect(self.start_hold)
        self.motion = QTimer(self)
        self.motion.setInterval(33)
        self.motion.timeout.connect(self.advance)
        self.pressed.connect(self.arm)
        self.released.connect(self.disarm)
        self.set_state('off')

    @property
    def holding(self):
        return self.isDown() and self.hold_elapsed

    def arm(self):
        if self.hands_free:return
        self.hold_elapsed = False
        self.hold_timer.start()

    def disarm(self):
        self.hold_timer.stop()
        self.hold_elapsed = False

    def start_hold(self):
        if self.isDown() and self.isEnabled():
            self.hold_elapsed = True
            self.hold_started.emit()

    def move_drag(self,offset):
        self.drag_offset=float(offset)
        if self.drag_origin is not None:self.move(self.drag_origin+QPoint(round(self.drag_offset),0))

    def finish_snap(self):
        if self.drag_origin is not None:self.move(self.drag_origin)
        self.drag_origin=None;self.drag_offset=0.

    def snap_back(self):
        self.snap.stop()
        if self.drag_origin is None:return
        if not self.animated or not self.isVisible():self.finish_snap();return
        self.snap.setStartValue(self.drag_offset);self.snap.setEndValue(0.);self.snap.start()

    def cancel_hold(self):
        self.locked=False
        self.lock_release_pending=False
        self.hands_free_release_pending=False
        self.disarm()
        self.setDown(False)
        self.snap_back()
        self.cancelled.emit()

    def set_state(self, state, detail=''):
        previous=getattr(self,'state',None)
        self.state = state
        if state!='listening':
            self.locked=False
            self.levels=[0.] * 11
        elif previous!='listening':
            self.elapsed=0.
        self.refresh_tip()
        self.setAccessibleDescription(detail or self.TIPS[state])
        self.sync_motion()
        self.update()

    def refresh_tip(self):
        tip=self.TIPS[self.state]
        if self.hands_free:
            tip='Tap to start conversation' if self.state=='off' else ('Hands-free unavailable · Tap to retry' if self.state in ('error','disconnected') else 'Hands-free · Tap or Esc to stop')
        if self.state=='listening' and not self.hands_free:
            tip=('Locked · Click to send · Esc to cancel' if self.locked else tip)
            remaining=max(0,math.ceil(self.max_seconds-self.elapsed))
            tip+=f' · {int(self.elapsed)//60}:{int(self.elapsed)%60:02d}'
            if remaining<=120:tip+=f' · {remaining//60}:{remaining%60:02d} left'
        if self.hands_free and self.state not in ('off','error','disconnected'):
            tip=('Listening · Tap or Esc to stop' if self.recording_available else 'Please wait · Microphone not ready')
        self.setToolTip(tip)
        self.setAccessibleName('Resonant Voice · '+tip)

    def set_recording_progress(self, elapsed, maximum, levels):
        self.elapsed=elapsed;self.max_seconds=maximum
        self.levels=list(levels)
        self.refresh_tip();self.update()

    def recording_colour(self):
        if self.state=='listening':
            remaining=self.max_seconds-self.elapsed
            if remaining<=60:return QColor('#ff5964')
            if remaining<=120:return QColor('#ffae42')
        if self.state in ('connecting','recognizing') or (self.hands_free and self.state not in ('off','error','disconnected')):
            return QColor('#52d68a' if self.recording_available else '#ffae42')
        if self.state=='listening':return QColor('#52d68a' if self.recording_available else '#ffae42')
        return QColor(self.accent)

    def request_hands_free(self):
        self.disarm();self.setDown(False)
        self.hands_free_release_pending=True
        self.snap_back()
        self.hands_free_requested.emit()

    def lock_recording(self):
        if self.hands_free or self.state!='listening':return
        self.locked=True;self.lock_release_pending=True
        self.disarm();self.setDown(False)
        self.snap_back()
        self.refresh_tip();self.update()

    def configure(self, accent, animated=True):
        self.accent = QColor(accent)
        self.animated = animated
        self.sync_motion()
        self.update()

    def sync_motion(self):
        if self.animated and self.isVisible() and (self.hovered or self.state in ('listening', 'speaking', 'connecting', 'recognizing', 'thinking')):
            self.motion.start()
        else:
            self.motion.stop()
            self.phase = 0.

    def advance(self):
        self.phase += .033
        self.update()

    def enterEvent(self, event):
        self.hovered = True
        self.sync_motion()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.sync_motion()
        self.update()
        super().leaveEvent(event)

    def showEvent(self, event):
        self.sync_motion()
        super().showEvent(event)

    def hideEvent(self, event):
        self.cancel_hold()
        self.motion.stop()
        super().hideEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self.cancel_hold()
        super().changeEvent(event)

    def mousePressEvent(self, event):
        self.snap.stop();self.finish_snap()
        self.drag_origin=QPoint(self.pos())
        self.press_position=event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.hands_free_release_pending:
            event.accept();return
        if self.hands_free:
            super().mouseMoveEvent(event);return
        if self.locked or self.lock_release_pending:
            event.accept();return
        if self.isDown() and self.press_position is not None:
            delta=event.position()-self.press_position+QPointF(self.pos()-self.drag_origin if self.drag_origin is not None else QPoint())
            if abs(delta.y())<=24:self.move_drag(max(-12.,min(12.,delta.x()*.5)))
            if delta.x()>=self.LOCK_DISTANCE and abs(delta.y())<=24:
                self.request_hands_free();event.accept();return
            if self.holding and self.state=='listening' and delta.x()<=-self.LOCK_DISTANCE and abs(delta.y())<=24:
                self.lock_recording();event.accept();return
            # Keep the pointer captured while sliding horizontally towards the lock.
            if delta.x()!=0 and abs(delta.y())<=24:
                event.accept();return
            if not self.rect().contains(event.position().toPoint()):
                self.cancel_hold()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.snap_back()
        if self.hands_free_release_pending:
            self.hands_free_release_pending=False
            self.setDown(False);event.accept();return
        if self.lock_release_pending:
            self.lock_release_pending=False
            self.setDown(False);event.accept();return
        if not self.hands_free and not self.rect().contains(event.position().toPoint()):
            self.cancel_hold()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            event.accept(); return
        if event.key()==Qt.Key.Key_L and self.state=='listening':
            self.lock_recording();self.lock_release_pending=False;event.accept();return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click(); event.accept(); return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            event.accept(); return
        super().keyReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width()/2, self.height()/2)
        accent = self.recording_colour()
        if not self.isEnabled():painter.setOpacity(.35)
        phase = self.phase
        radius = 8.8 + (.5 * math.sin(phase*2) if phase else 0)
        path = QPainterPath()
        for i in range(97):
            angle = i*math.tau/96
            r = radius*(1 + .065*math.sin(3*angle+phase*.85) + .035*math.cos(2*angle-phase))
            point = QPointF(math.cos(angle)*r, math.sin(angle)*r)
            if i == 0:path.moveTo(point)
            else:path.lineTo(point)
        path.closeSubpath()
        glow = QRadialGradient(QPointF(-2, -2), 14)
        soft = QColor(accent);soft.setAlpha(100 if self.hovered or self.state=='listening' else 55)
        clear = QColor(accent);clear.setAlpha(0)
        glow.setColorAt(0, soft);glow.setColorAt(1, clear)
        painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(glow)
        painter.drawEllipse(QPointF(0,0),14,14)
        fill = QColor(accent);fill.setAlpha(75 if self.state=='listening' else 24)
        painter.setBrush(fill);painter.setPen(QPen(accent,1.3));painter.drawPath(path)
        painter.setBrush(accent);painter.setPen(Qt.PenStyle.NoPen)
        if self.state=='listening':
            # The waveform is microphone data, not a decorative animation.
            painter.setPen(QPen(accent,1.,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
            for i,level in enumerate(self.levels):
                x=(i-5)*1.15;height=max(.25,min(1.,level)*5.5)
                painter.drawLine(QPointF(x,-height),QPointF(x,height))
            if self.locked:
                painter.setBrush(accent);painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(6.,6.,5.,4.,1.,1.)
                painter.setPen(QPen(accent,1.));painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawArc(7,3,3,5,0,180*16)
        elif self.state=='speaking':painter.drawRoundedRect(-2.5,-2.5,5,5,1,1)
        elif self.state in ('connecting','recognizing','thinking'):
            for x in (-3.5,0,3.5):painter.drawEllipse(QPointF(x,0),.9,.9)
        elif self.state in ('error','disconnected'):
            painter.drawRoundedRect(-.7,-4,1.4,5,.5,.5);painter.drawEllipse(QPointF(0,3),.9,.9)
        if self.hands_free and self.state not in ('off','error','disconnected'):
            painter.setBrush(Qt.BrushStyle.NoBrush);painter.setPen(QPen(accent,1.2))
            painter.drawArc(-11,-11,22,22,20*16,110*16)
            painter.drawArc(-11,-11,22,22,200*16,110*16)
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush);painter.setPen(QPen(accent,1,Qt.PenStyle.DotLine))
            painter.drawEllipse(QPointF(0,0),12,12)
