# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Soft exterior plasma and a morphing smoke reservoir beneath the translucent surface."""
import math
import random
import time
import numpy as np
from .fluid import FluidField
from .nature import ButterflySwarm
from .smoke_glow import paint_smoke_glow
from PySide6.QtCore import QObject, QTimer, QRectF, QEvent, Qt, QPoint, QRect, QPointF
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QPainter, QPainterPath, QImage, QFont, QCursor


class ActivityHalo(QObject):
    margin = 32
    extent = 192
    near_extent = 64

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.busy = False
        self.animated = True
        self.enabled = True
        self.effect = "plasma"
        self.strength = 0.0
        self.last_tick = time.monotonic()
        self.phase = 0.0
        self.noise = FlowNoise()
        self.rng = random.Random()
        self.breath_phase = self.rng.uniform(0, math.tau)
        self.breath_period = self.rng.uniform(4.5, 8.)
        self.flare = None
        self.geometry_key = None
        self.samples = []
        self.glyphs = []
        self.frame_key = None
        self.frame = QImage()
        self.butterflies=ButterflySwarm()
        self.fluid=FluidField();self.fluid_phase=None;self.pointer=QPointF(-10000,-10000)
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.tick)
        self.canvas = HaloCanvas(self)
        self.window.installEventFilter(self)

    def configure(self, busy=None, animated=None, enabled=None, effect=None, colours=None):
        if colours is not None:self.butterflies.set_colours(colours)
        if effect is not None and effect != self.effect:
            self.effect=effect;self.frame_key=None;self.flare=None
            self.fluid=FluidField();self.fluid_phase=None
        if busy is not None:
            if busy and not self.busy:self.flare = None
            self.busy = bool(busy)
        if animated is not None:
            self.animated = bool(animated)
        if enabled is not None:self.enabled=bool(enabled)
        self.sync()

    def position_canvas(self):
        extra=self.extent-self.margin
        target=QRect(self.window.mapToGlobal(QPoint(0,0)),self.window.size()).adjusted(-extra,-extra,extra,extra)
        if self.canvas.geometry()!=target:
            self.canvas.setGeometry(target);self.butterflies.pointer=None

    def eventFilter(self, watched, event):
        if watched is self.window:
            if event.type() in (QEvent.Type.Move,QEvent.Type.Resize):
                self.position_canvas();self.canvas.update()
                QTimer.singleShot(0,self.position_canvas)
            elif event.type()==QEvent.Type.Hide:
                self.canvas.hide();self.timer.stop()
        return False

    def sync(self):
        visible = self.window.isVisible() and not self.window.isMinimized() and not getattr(self.window,'morphing',False)
        if not visible or not self.enabled or self.effect == "none":
            self.timer.stop();self.canvas.hide();self.fluid=FluidField();self.fluid_phase=None;self.window.update()
            return
        if not self.animated:
            self.strength = float(self.busy)
            self.timer.stop()
        elif self.busy or self.strength > 0:
            if not self.timer.isActive():
                self.last_tick = time.monotonic()
                self.butterflies.pointer=None
                self.timer.start()
        self.position_canvas()
        self.canvas.setVisible(self.busy or self.strength > 0)
        self.canvas.update();self.window.update()

    def tick(self):
        self.position_canvas()
        now = time.monotonic()
        dt = min(now - self.last_tick, .1)
        self.last_tick = now
        self.update_interaction(dt)
        self.advance(dt)
        self.strength = min(1., self.strength + dt / .6) if self.busy else max(0., self.strength - dt / .8)
        if not self.busy and self.strength == 0:
            self.timer.stop()
        if self.strength==0 and not self.busy:self.canvas.hide()
        self.canvas.update()
        if not self.window.compact:self.window.update(self.window.surface_rect())

    def update_interaction(self,dt):
        self.pointer=QPointF(self.canvas.mapFromGlobal(QCursor.pos()))

    def canvas_surface_rect(self):
        origin=self.canvas.mapFromGlobal(self.window.mapToGlobal(QPoint(0,0)))
        return QRectF(self.window.surface_rect().translated(origin.x(),origin.y()).adjusted(1,1,-1,-1))

    def advance(self, dt):
        self.phase += dt
        if self.effect in ("butterflies", "butterflies-large"):
            self.butterflies.advance(dt,self.canvas_surface_rect(),self.pointer,self.window.compact)
            return
        if self.effect != "plasma":return
        self.breath_phase += math.tau * dt / self.breath_period
        if self.breath_phase >= math.tau:
            self.breath_phase %= math.tau
            self.breath_period = self.rng.uniform(4.5, 8.)
        if self.flare and self.phase-self.flare['start'] >= self.flare['duration']:
            self.flare = None
        # A 3% chance per active second, independent of timer frequency. Only
        # one eruption at a time; it ejects and dissipates rather than looping.
        if self.busy and not self.flare and self.rng.random() < -math.expm1(math.log(.97)*dt):
            distance_roll=self.rng.random()
            travel=self.rng.uniform(28.,43.) if distance_roll<.9 else 45+(self.extent*.86-45)*((distance_roll-.9)/.1)**2
            self.flare = {'start': self.phase, 'duration': self.rng.uniform(2.2, 4.),
                          'side': self.rng.randrange(4), 'position': self.rng.uniform(.12, .88),
                          'width': self.rng.uniform(35., 65.),
                          'travel':travel}

    def prepare_geometry(self, rect):
        key = (self.canvas.width(), self.canvas.height(), *rect.getRect())
        if key == self.geometry_key:
            return
        self.geometry_key = key
        # Only sample the narrow exterior band. Bound the CPU work for large
        # windows; Qt smoothly upsamples the texture, just like the web veil.
        scale = max(4., (rect.width() + rect.height()) / 360)
        self.image_width = math.ceil(self.canvas.width() / scale)
        self.image_height = math.ceil(self.canvas.height() / scale)
        sx = self.canvas.width() / self.image_width
        sy = self.canvas.height() / self.image_height
        cx, cy = rect.center().x(), rect.center().y()
        radius=min(rect.width(),rect.height())/2 if self.window.compact else 20
        bx, by = rect.width() / 2 - radius, rect.height() / 2 - radius

        def distance(x, y):
            qx, qy = abs(x - cx) - bx, abs(y - cy) - by
            return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - radius

        self.samples = [];self.outer_samples = [[],[],[],[]]
        self.distance_grid=np.zeros((self.image_height,self.image_width),np.float32)
        for row in range(self.image_height):
            y = (row + .5) * sy
            for col in range(self.image_width):
                x = (col + .5) * sx
                d = distance(x, y)
                self.distance_grid[row,col]=max(0.,d)
                if -scale <= d < self.extent:
                    # Fade at the outer window boundary as well as from the
                    # rounded panel, so no rectangular clipping edge appears.
                    fade = min(1., max(0., min(x, y, self.canvas.width()-x,
                                              self.canvas.height()-y) / 20))
                    pixel=((row*self.image_width+col)*4,x,y,max(0.,d),fade)
                    if d<self.near_extent:self.samples.append(pixel)
                    else:
                        for side,normal in enumerate((rect.top()-y,x-rect.right(),y-rect.bottom(),rect.left()-x)):
                            if normal>0:self.outer_samples[side].append(pixel)
        self.glyphs = []
        symbols = '0123456789ABCDEF+-*/<>=&|#%$!:.,'
        for y in range(3, self.canvas.height(), 8):
            for x in range(3, self.canvas.width(), 7):
                d = distance(x+3, y+4)
                if 1 < d < 23:
                    h = self.noise.sample(x*1.7, y*1.3)
                    self.glyphs.append((x, y, d, symbols[int(h*1000) % len(symbols)], h))
        self.frame_key = None

    def render_field(self, rect, accent):
        self.prepare_geometry(rect)
        t = self.phase if self.animated else 0.
        key = (self.geometry_key, t, self.breath_phase, accent.rgba(),
               self.canvas.x(),self.canvas.y(),self.pointer.x(),self.pointer.y(),
               tuple(self.flare.values()) if self.flare else None)
        if key == self.frame_key:
            return
        self.frame_key = key
        data = bytearray(self.image_width*self.image_height*4)
        sample = self.noise.sample
        breath = .5-.5*math.cos(self.breath_phase) if self.animated else .5
        hue, saturation, value, _ = accent.getHsvF()
        tint = QColor.fromHsvF(max(0., hue), min(1., saturation*(.8+.7*breath)),
                              min(1., value*(.86+.14*breath)))
        red, green, blue, _ = tint.getRgb()
        breathing_alpha = .65+.65*breath
        eruption = None
        if self.animated and self.flare:
            flare = self.flare
            progress = (t-flare['start'])/flare['duration']
            if 0 <= progress < 1:
                # Tangentially broad, with a crest travelling out of the band.
                side = flare['side']
                along = (rect.left()+rect.width()*flare['position'] if side in (0, 2)
                         else rect.top()+rect.height()*flare['position'])
                eruption = (side, along, flare['width'], 2+flare.get('travel',43)*math.sin(progress*math.pi)**.8,
                            math.sin(math.pi*progress)**1.3)
        # Independent evolving fields bend the broad texture in
        # different directions. There is no perimeter coordinate or orbit.
        pixels=self.samples
        if eruption:
            side,along,width,crest,intensity=eruption
            far=[pixel for pixel in self.outer_samples[side]
                 if abs((pixel[1] if side in (0,2) else pixel[2])-along)<width*2.5]
            pixels=self.samples+far
        for index, x, y, distance, fade in pixels:
            alpha=0.;fine=.4;ridge=0.
            if distance < self.near_extent:
                px, py = x*.075, y*.075
                q = sample(px*.43 + t*1.65, py*.43 - t*.95)
                r = sample(px*.39 - t*1.1 + 37, py*.39 + t*1.45 + 71)
                u, v = px + 16*q, py + 16*r
                cloud = sample(u + t*1.7, v - t*2.1)
                fine = sample(u*1.6 - t*2.2 + 19, v*1.6 + t*.85)
                # Filament crests echo the browser's refracting frost veins.
                ridge = max(0., 1-abs(cloud + .16*fine - .58)*6)**2
                local_breath = .7+.6*sample(px*.6 + t*.8 + 81, py*.6-t*.5)
                reach = 5 + 29*q*local_breath
                envelope = math.exp(-(distance/reach)**2*1.9)*fade
                alpha = envelope * (.025 + .19*cloud + .55*ridge) * breathing_alpha * local_breath
            flare_light = 0.
            if eruption:
                side, along, width, crest, intensity = eruption
                tangent = (x if side in (0, 2) else y)-along
                normal = (rect.top()-y, x-rect.right(), y-rect.bottom(), rect.left()-x)[side]
                if normal >= -2 and abs(tangent) < width*2.5:
                    # Two rooted, uneven strands form a solar arch, not a
                    # detached blob. Width and density fall with distance.
                    height=max(1.,crest)
                    fraction=max(0.,min(1.,normal/height))
                    bend=height*.13*math.sin(math.pi*fraction)*(math.sin(fraction*4.7+t*1.4)+.35*math.sin(fraction*9.1-t*2.1))
                    radius=width*.65*math.sqrt(max(0.,1-fraction))
                    strand_width=1.6+4.8*(1-fraction)**1.5
                    left=(tangent-bend-radius)/strand_width
                    right=(tangent-bend+radius*.82)/strand_width
                    strands=math.exp(-left*left)+.8*math.exp(-right*right)
                    cap=math.exp(-(max(0.,normal-height)/strand_width)**2)
                    detail=.65+.35*sample(normal*.18+t*1.7,tangent*.08-t*1.1+23)
                    density=(1-.72*fraction)*math.exp(-max(0.,normal)/160)
                    root=math.exp(-(tangent/(width*.7))**2-(normal/12)**2)*.35
                    flare_light=(strands*cap*density*detail+root)*intensity*fade
                    alpha += flare_light*.75
            if alpha<.002:continue
            light = .66 + .28*fine + .35*ridge + .4*flare_light
            # Distant plasma loses saturation as it becomes tenuous.
            desaturate=min(.78,max(0.,distance-16)/self.extent) if flare_light else 0.
            grey=(red+green+blue)/3
            data[index] = min(255,int((red+(grey-red)*desaturate)*light))
            data[index+1] = min(255,int((green+(grey-green)*desaturate)*light))
            data[index+2] = min(255,int((blue+(grey-blue)*desaturate)*light))
            data[index+3] = min(200, int(255*alpha))
        if self.animated:
            rgba=np.frombuffer(data,dtype=np.uint8).reshape(self.image_height,self.image_width,4)
            origin=(self.canvas.x(),self.canvas.y());cell=(self.canvas.width()/self.image_width,self.canvas.height()/self.image_height)
            pointer=(self.pointer.x()+origin[0],self.pointer.y()+origin[1])
            dt=self.phase-self.fluid_phase if self.fluid_phase is not None else .04
            self.fluid_phase=self.phase
            rendered=self.fluid.step(rgba,origin,cell,dt,pointer,self.distance_grid)
            self.frame=QImage(rendered.data,self.image_width,self.image_height,self.image_width*4,QImage.Format.Format_RGBA8888_Premultiplied).copy()
        else:
            self.fluid=FluidField();self.fluid_phase=None
            self.frame=QImage(bytes(data),self.image_width,self.image_height,self.image_width*4,QImage.Format.Format_RGBA8888).copy()

    def paint_backdrop(self,painter,rect,accent):
        if self.effect in ("butterflies", "butterflies-large"):return
        if self.effect == "none" or not self.enabled or self.strength<=0:return
        paint_smoke_glow(painter,rect,accent,self.phase if self.animated else 0.,self.breath_phase if self.animated else 1.,self.strength)

    def paint(self, painter, rect, accent):
        if not self.enabled or self.effect == "none" or self.strength <= 0:
            return
        rect = QRectF(rect)
        if self.effect in ("butterflies", "butterflies-large"):
            self.butterflies.paint(painter,rect,self.strength,self.animated,self.window.compact,
                                   size_multiplier=3. if self.effect == "butterflies-large" else 1.)
            return
        surface = QPainterPath()
        radius=min(rect.width(),rect.height())/2 if self.window.compact else 20
        surface.addRoundedRect(rect, radius, radius)
        outside = QPainterPath()
        outside.addRect(QRectF(self.canvas.rect()))
        painter.save()
        painter.setClipPath(outside.subtracted(surface))
        painter.setOpacity(self.strength)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.render_field(rect, accent)
        painter.drawImage(QRectF(self.canvas.rect()), self.frame)
        # Small fragments of the browser's glyph field emerge within the mist.
        # Keep each symbol stable; local noise controls its gradual appearance.
        font = QFont('DejaVu Sans Mono')
        font.setPixelSize(7)
        painter.setFont(font)
        t = self.phase if self.animated else 0.
        for x, y, distance, symbol, seed in self.glyphs:
            emergence = self.noise.sample(x*.035 + t*.8, y*.035 - t*1.1 + 53)
            alpha = max(0., emergence-.48)*.7 * (1-distance/25)
            if alpha < .015:
                continue
            color = QColor(accent).lighter(120)
            color.setAlphaF(min(.3, alpha))
            painter.setPen(color)
            # Subpixel local drift, independent of the neighbouring fragments.
            dx = 1.5*math.sin(t*(.23+seed*.3)+seed*31)
            dy = 1.2*math.sin(t*(.17+seed*.2)+seed*47)
            painter.drawText(QRectF(x+dx, y+dy, 8, 9), symbol)
        painter.restore()


class FlowNoise:
    """Smooth, seeded multiscale field, generated once without extra libraries.

    Like veil.js's domain-warped fbm, multiple spatial scales produce coherent
    turbulence. Randomness lives in the field, not in frame-to-frame flicker.
    """
    size = 128

    def __init__(self):
        rng = random.Random()
        self.values = [0.] * (self.size*self.size)
        for cells, weight in ((8, .64), (16, .28), (32, .08)):
            grid = [rng.random() for _ in range(cells*cells)]
            for y in range(self.size):
                gy = y*cells/self.size
                iy = int(gy); fy = gy-iy; fy = fy*fy*(3-2*fy)
                for x in range(self.size):
                    gx = x*cells/self.size
                    ix = int(gx); fx = gx-ix; fx = fx*fx*(3-2*fx)
                    a, b = grid[iy*cells+ix], grid[iy*cells+(ix+1)%cells]
                    c, d = grid[((iy+1)%cells)*cells+ix], grid[((iy+1)%cells)*cells+(ix+1)%cells]
                    self.values[y*self.size+x] += weight*((a+(b-a)*fx)*(1-fy)+(c+(d-c)*fx)*fy)

    def sample(self, x, y):
        ix, iy = math.floor(x), math.floor(y)
        fx, fy = x-ix, y-iy
        ix &= 127; iy &= 127
        nx, ny = (ix+1)&127, (iy+1)&127
        values = self.values
        a, b = values[iy*128+ix], values[iy*128+nx]
        c, d = values[ny*128+ix], values[ny*128+nx]
        return (a+(b-a)*fx)*(1-fy)+(c+(d-c)*fx)*fy


class HaloCanvas(QWidget):
    """A transient, input-transparent effect surface outside the app geometry."""
    def __init__(self, activity):
        super().__init__(activity.window, Qt.WindowType.Tool |
                         Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.X11BypassWindowManagerHint |
                         Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.WindowTransparentForInput |
                         Qt.WindowType.WindowDoesNotAcceptFocus)
        self.activity=activity
        self.setWindowTitle('Augmentor activity')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self,event):
        extra=self.activity.extent-self.activity.margin
        origin=self.mapFromGlobal(self.activity.window.mapToGlobal(QPoint(0,0)))
        rect=self.activity.window.surface_rect().translated(origin.x(),origin.y()).adjusted(1,1,-1,-1)
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.activity.paint(painter,rect,self.activity.window.accent)
