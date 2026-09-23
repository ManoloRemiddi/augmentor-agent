# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Lightweight vector foliage and butterflies; no downloaded assets or code."""
import math
import random
from dataclasses import dataclass
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainterPath, QPen


def paint_foliage(painter, rect, accent):
    painter.save()
    clip=QPainterPath();clip.addRoundedRect(rect,20,20);painter.setClipPath(clip)
    painter.setOpacity(.10)
    painter.setPen(QPen(accent,1.2));painter.setBrush(accent)
    for mirrored in (False,True):
        painter.save()
        painter.translate(rect.right() if mirrored else rect.left(),rect.bottom())
        if mirrored:painter.scale(-1,1)
        stem=QPainterPath(QPointF(0,0));stem.cubicTo(65,-25,18,-125,95,-205)
        painter.drawPath(stem)
        for i in range(7):
            painter.save();painter.translate(18+i*8,-22-i*24);painter.rotate(-40 if i%2 else 20)
            leaf=QPainterPath(QPointF(0,0));leaf.cubicTo(5,-26,30,-28,38,-12);leaf.cubicTo(25,0,9,9,0,0)
            painter.drawPath(leaf);painter.restore()
        painter.restore()
    painter.restore()



@dataclass
class Butterfly:
    x: float
    y: float
    vx: float
    vy: float
    size: float
    colour: QColor
    phase: float
    frequency: float
    home: float
    steering: float = 0.


class ButterflySwarm:
    """Persistent, bounded flight with a soft perimeter attraction and cursor wake.

    Positions advance only on timer ticks, never during paint. The canvas remains
    input-transparent: movement comes from the global pointer, with no mouse grab.
    """
    palette = ('#ed9962', '#e8c655', '#82be75', '#69bdd2', '#9990dc',
               '#d68ac0', '#e87987', '#b9dbb0', '#91c7e9')

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.colours = self.palette
        self.butterflies = []
        self.rect = None
        self.compact = False
        self.pointer = None
        self.time = 0.
        self.wing = QPainterPath(QPointF(0,0))
        self.wing.cubicTo(7,-21,25,-16,13,-2)
        self.wing.cubicTo(24,10,5,18,0,2)

    def set_colours(self, colours):
        colours=tuple(colours) or self.palette
        if colours==self.colours:return
        self.colours=colours
        for i,butterfly in enumerate(self.butterflies):
            butterfly.colour=QColor(colours[i%len(colours)])

    def boundary(self, x, y):
        """Signed distance and outward normal from the panel."""
        rect=self.rect;cx,cy=rect.center().x(),rect.center().y()
        dx,dy=x-cx,y-cy
        if self.compact:
            length=math.hypot(dx,dy)
            return length-min(rect.width(),rect.height())/2, dx/max(length,.001), dy/max(length,.001)
        qx,qy=abs(dx)-rect.width()/2,abs(dy)-rect.height()/2
        sx,sy=1 if dx>=0 else -1,1 if dy>=0 else -1
        if qx>0 and qy>0:
            length=math.hypot(qx,qy)
            return length,sx*qx/length,sy*qy/length
        return (qx,sx,0.) if qx>qy else (qy,0.,sy)

    def prepare(self, rect, compact=False):
        from PySide6.QtCore import QRectF
        count=160 if compact else 420
        if self.rect == rect and self.compact == compact:return
        old=self.rect;self.rect=QRectF(rect);self.compact=compact;self.pointer=None
        if len(self.butterflies)==count and old is not None:
            # Preserve a swarm during a window resize, including its velocities.
            for b in self.butterflies:
                b.x=rect.center().x()+(b.x-old.center().x())*rect.width()/max(1.,old.width())
                b.y=rect.center().y()+(b.y-old.center().y())*rect.height()/max(1.,old.height())
            return
        self.butterflies=[]
        for _ in range(count):
            home=min(110.,7+self.rng.expovariate(1/22))
            if compact:
                angle=self.rng.uniform(0,math.tau);radius=rect.width()/2+home
                x,y=rect.center().x()+radius*math.cos(angle),rect.center().y()+radius*math.sin(angle)
            else:
                w,h=rect.width(),rect.height();along=self.rng.uniform(0,2*(w+h))
                if along<w:x,y=rect.left()+along,rect.top()-home
                elif along<w+h:x,y=rect.right()+home,rect.top()+along-w
                elif along<2*w+h:x,y=rect.right()-(along-w-h),rect.bottom()+home
                else:x,y=rect.left()-home,rect.bottom()-(along-2*w-h)
            self.butterflies.append(Butterfly(x,y,self.rng.uniform(-9,9),self.rng.uniform(-9,9),
                self.rng.uniform(.025,.095),QColor(self.rng.choice(self.colours)),
                self.rng.uniform(0,math.tau),self.rng.uniform(.7,1.8),home))

    def advance(self, dt, rect, pointer, compact=False):
        self.prepare(rect,compact)
        dt=max(0.,min(.1,dt))
        if not dt:return
        self.time+=dt
        px,py=pointer.x(),pointer.y()
        pvx=pvy=0.
        if self.pointer is not None:
            pvx=(px-self.pointer[0])/dt;pvy=(py-self.pointer[1])/dt
            speed=math.hypot(pvx,pvy)
            if speed>900:pvx*=900/speed;pvy*=900/speed
        self.pointer=(px,py)
        decay=math.exp(-2.1*dt)
        for b in self.butterflies:
            distance,nx,ny=self.boundary(b.x,b.y)
            # Independent slowly changing headings and gusts, not shared orbits.
            b.steering=b.steering*math.exp(-1.3*dt)+self.rng.gauss(0,32)*math.sqrt(dt)
            t=self.time*b.frequency+b.phase
            normal=-(distance-b.home)*1.5+22*math.sin(t*1.17)
            tangent=b.steering+24*math.sin(t*.73)+12*math.cos(t*1.61)
            ax,ay=nx*normal-ny*tangent,ny*normal+nx*tangent
            dx,dy=b.x-px,b.y-py;reach=math.hypot(dx,dy)
            if reach<105:
                weight=(1-reach/105)**2
                if reach<.01:dx,dy=math.cos(b.phase),math.sin(b.phase);reach=1.
                ax+=dx/reach*1100*weight+pvx*4*weight
                ay+=dy/reach*1100*weight+pvy*4*weight
            b.vx=(b.vx+ax*dt)*decay;b.vy=(b.vy+ay*dt)*decay
            speed=math.hypot(b.vx,b.vy)
            if speed>230:b.vx*=230/speed;b.vy*=230/speed
            b.x+=b.vx*dt;b.y+=b.vy*dt
            distance,nx,ny=self.boundary(b.x,b.y)
            # Reflect at the reading surface and the halo's outer safe boundary.
            if distance<3 or distance>170:
                target=3 if distance<3 else 170
                b.x+=nx*(target-distance);b.y+=ny*(target-distance)
                velocity=b.vx*nx+b.vy*ny
                if (distance<3 and velocity<0) or (distance>170 and velocity>0):
                    b.vx-=1.4*velocity*nx;b.vy-=1.4*velocity*ny

    def paint(self, painter, rect, strength, animated=True, compact=False, size_multiplier=1.):
        self.prepare(rect,compact)
        painter.save();painter.setOpacity(strength*.9)
        painter.setPen(Qt.PenStyle.NoPen)
        for b in self.butterflies:
            painter.save();painter.translate(b.x,b.y)
            painter.rotate(math.degrees(math.atan2(b.vy,b.vx))+90)
            painter.scale(b.size*size_multiplier,b.size*size_multiplier)
            phase=self.time if animated else 0.
            flutter=.35+.65*abs(math.cos(phase*(8+b.frequency*3)+b.phase))
            painter.setBrush(b.colour)
            for side in (-1,1):
                painter.save();painter.scale(side*flutter,1);painter.drawPath(self.wing);painter.restore()
            painter.restore()
        painter.restore()
