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
        dpr = self.canvas.devicePixelRatioF()
        key = (self.canvas.width(), self.canvas.height(), dpr, *rect.getRect())
        if key == self.geometry_key:
            return
        self.geometry_key = key
        # Resolve thin strands independently of the coarser transport grid.
        # Modest supersampling on high-DPI screens improves their coverage;
        # cap it and the total area so animation cannot starve the GUI thread.
        scale = max(1. / min(dpr, 1.25), math.sqrt(self.canvas.width()*self.canvas.height()/1_000_000))
        self.image_width = math.ceil(self.canvas.width() / scale)
        self.image_height = math.ceil(self.canvas.height() / scale)
        self.flow_scale = max(4., (rect.width() + rect.height()) / 360)
        self.flow_width = math.ceil(self.canvas.width() / self.flow_scale)
        self.flow_height = math.ceil(self.canvas.height() / self.flow_scale)
        cx, cy = rect.center().x(), rect.center().y()
        radius = min(rect.width(), rect.height())/2 if self.window.compact else 20
        bx, by = rect.width()/2-radius, rect.height()/2-radius

        def distance(x, y):
            qx, qy = np.abs(x-cx)-bx, np.abs(y-cy)-by
            return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - radius

        y, x = np.mgrid[:self.image_height, :self.image_width].astype(np.float32)
        x = (x+.5)*(self.canvas.width()/self.image_width)
        y = (y+.5)*(self.canvas.height()/self.image_height)
        d = distance(x, y)
        indices = np.flatnonzero((d >= -scale) & (d < self.extent))
        x, y, d = x.ravel()[indices], y.ravel()[indices], d.ravel()[indices]
        fade = np.clip(np.minimum.reduce((x, y, self.canvas.width()-x, self.canvas.height()-y))/20, 0, 1)
        self.samples = (indices, x, y, np.maximum(0, d), fade)
        self.near_samples = np.flatnonzero(d < self.near_extent)
        self.outer_samples = [np.flatnonzero((d >= self.near_extent) & (normal > 0))
                              for normal in (rect.top()-y, x-rect.right(), y-rect.bottom(), rect.left()-x)]
        fy, fx = np.mgrid[:self.flow_height, :self.flow_width].astype(np.float32)
        self.distance_grid = np.maximum(0, distance((fx+.5)*self.canvas.width()/self.flow_width,
                                                  (fy+.5)*self.canvas.height()/self.flow_height))
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
               self.canvas.x(), self.canvas.y(), self.pointer.x(), self.pointer.y(),
               tuple(self.flare.values()) if self.flare else None)
        if key == self.frame_key:
            return
        self.frame_key = key
        data = np.zeros((self.image_height*self.image_width, 4), np.uint8)
        sample = self.noise.sample_array
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
                side = flare['side']
                along = (rect.left()+rect.width()*flare['position'] if side in (0, 2)
                         else rect.top()+rect.height()*flare['position'])
                eruption = (side, along, flare['width'], 2+flare.get('travel',43)*math.sin(progress*math.pi)**.8,
                            math.sin(math.pi*progress)**1.3)
        pixels = self.near_samples
        if eruption:
            side, along, width, crest, intensity = eruption
            far = self.outer_samples[side]
            tangent = self.samples[1 if side in (0, 2) else 2][far]-along
            pixels = np.concatenate((pixels, far[np.abs(tangent) < width*2.5]))
        indices, x, y, distance, fade = (column[pixels] for column in self.samples)
        alpha = np.zeros(len(pixels), np.float32)
        fine = np.full(len(pixels), .4, np.float32)
        ridge = np.zeros(len(pixels), np.float32)
        near = distance < self.near_extent
        # Vectorized evaluation retains the original field, colours and timing;
        # Python no longer runs the noise function six times for every pixel.
        px, py = x[near]*.075, y[near]*.075
        q = sample(px*.43+t*1.65, py*.43-t*.95)
        r = sample(px*.39-t*1.1+37, py*.39+t*1.45+71)
        u, v = px+16*q, py+16*r
        cloud = sample(u+t*1.7, v-t*2.1)
        fine[near] = sample(u*1.6-t*2.2+19, v*1.6+t*.85)
        ridge[near] = np.maximum(0, 1-np.abs(cloud+.16*fine[near]-.58)*6)**2
        local_breath = .7+.6*sample(px*.6+t*.8+81, py*.6-t*.5)
        reach = 5+29*q*local_breath
        envelope = np.exp(-(distance[near]/reach)**2*1.9)*fade[near]
        alpha[near] = envelope*(.025+.19*cloud+.55*ridge[near])*breathing_alpha*local_breath
        flare_light = np.zeros(len(pixels), np.float32)
        if eruption:
            side, along, width, crest, intensity = eruption
            tangent = (x if side in (0, 2) else y)-along
            normal = (rect.top()-y, x-rect.right(), y-rect.bottom(), rect.left()-x)[side]
            mask = (normal >= -2) & (np.abs(tangent) < width*2.5)
            n, tang = normal[mask], tangent[mask]
            height = max(1., crest)
            fraction = np.clip(n/height, 0, 1)
            bend = height*.13*np.sin(math.pi*fraction)*(np.sin(fraction*4.7+t*1.4)+.35*np.sin(fraction*9.1-t*2.1))
            radius = width*.65*np.sqrt(np.maximum(0, 1-fraction))
            strand_width = 1.6+4.8*(1-fraction)**1.5
            left, right = (tang-bend-radius)/strand_width, (tang-bend+radius*.82)/strand_width
            strands = np.exp(-left*left)+.8*np.exp(-right*right)
            cap = np.exp(-(np.maximum(0, n-height)/strand_width)**2)
            detail = .65+.35*sample(n*.18+t*1.7, tang*.08-t*1.1+23)
            density = (1-.72*fraction)*np.exp(-np.maximum(0, n)/160)
            root = np.exp(-(tang/(width*.7))**2-(n/12)**2)*.35
            flare_light[mask] = (strands*cap*density*detail+root)*intensity*fade[mask]
            alpha += flare_light*.75
        light = .66+.28*fine+.35*ridge+.4*flare_light
        desaturate = np.where(flare_light > 0, np.clip((distance-16)/self.extent, 0, .78), 0)
        grey = (red+green+blue)/3
        for channel, colour in enumerate((red, green, blue)):
            data[indices, channel] = np.clip((colour+(grey-colour)*desaturate)*light, 0, 255).astype(np.uint8)
        data[indices, 3] = np.minimum(200, 255*alpha).astype(np.uint8)
        data = data.reshape(self.image_height, self.image_width, 4)
        source = QImage(data.data, self.image_width, self.image_height, self.image_width*4,
                        QImage.Format.Format_RGBA8888)
        if self.animated:
            coarse = source.scaled(self.flow_width, self.flow_height, Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            rgba = image_array(coarse)
            origin = (self.canvas.x(), self.canvas.y())
            cell = (self.canvas.width()/self.flow_width, self.canvas.height()/self.flow_height)
            pointer = (self.pointer.x()+origin[0], self.pointer.y()+origin[1])
            dt = self.phase-self.fluid_phase if self.fluid_phase is not None else .04
            self.fluid_phase = self.phase
            rendered = self.fluid.step(rgba, origin, cell, dt, pointer, self.distance_grid)
            transported = QImage(rendered.data, self.flow_width, self.flow_height, self.flow_width*4,
                                 QImage.Format.Format_RGBA8888_Premultiplied)
            self.frame = restore_emission_detail(source, coarse, transported)
        else:
            self.fluid = FluidField(); self.fluid_phase = None
            self.frame = source.copy()

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


def image_array(image):
    """A borrowed RGBA view; callers retain the owning QImage."""
    return np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.bytesPerLine()//4, 4)[:, :image.width()]


def restore_emission_detail(source, coarse, transported):
    """Keep coarse smoke transport, restore the emission lost to its grid.

    This is a visual multiresolution field: the fluid transports broad wakes;
    the current analytic emission supplies fine strands. Work in premultiplied
    colour throughout so faint edges cannot acquire dark or coloured fringes.
    """
    fmt = QImage.Format.Format_RGBA8888_Premultiplied
    size = source.size()
    upsample = lambda image: image.scaled(size, Qt.AspectRatioMode.IgnoreAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
    fine = source.convertToFormat(fmt)
    base = upsample(transported)
    low = upsample(coarse.convertToFormat(fmt))
    result = image_array(base).astype(np.int16) + image_array(fine).astype(np.int16) - image_array(low).astype(np.int16)
    result = np.clip(result, 0, 255).astype(np.uint8)
    result[..., :3] = np.minimum(result[..., :3], result[..., 3, None])
    result[[0, -1], :] = 0; result[:, [0, -1]] = 0
    return QImage(result.data, size.width(), size.height(), size.width()*4, fmt).copy()


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

        self.array = np.asarray(self.values, np.float32)

    def sample_array(self, x, y):
        ix, iy = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32)
        fx, fy = x-ix.astype(np.float32), y-iy.astype(np.float32)
        ix, iy = ix & 127, iy & 127
        nx, ny = (ix+1) & 127, (iy+1) & 127
        a, b = self.array[iy*128+ix], self.array[iy*128+nx]
        c, d = self.array[ny*128+ix], self.array[ny*128+nx]
        return (a+(b-a)*fx)*(1-fy)+(c+(d-c)*fx)*fy

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
        # Keep the exterior surface managed and transient to its own agent.
        # Bypassing the WM makes it visible on other workspaces and above
        # unrelated windows; an independent keep-above hint breaks stacking.
        super().__init__(activity.window, Qt.WindowType.Tool |
                         Qt.WindowType.FramelessWindowHint |
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
