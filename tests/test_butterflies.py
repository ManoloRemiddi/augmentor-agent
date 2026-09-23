# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import math
import unittest
from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QImage,QPainter
from augmentor_linux.nature import ButterflySwarm


class ButterflyTests(unittest.TestCase):
    rect=QRectF(192,192,600,700)
    away=QPointF(-10000,-10000)

    def test_density_size_colour_and_long_running_bounds(self):
        swarm=ButterflySwarm(7);swarm.prepare(self.rect)
        self.assertEqual(len(swarm.butterflies),420)
        self.assertGreater(len({b.colour.name() for b in swarm.butterflies}),7)
        self.assertTrue(all(.025<=b.size<=.095 for b in swarm.butterflies))
        for _ in range(750):swarm.advance(.04,self.rect,self.away)
        distances=[swarm.boundary(b.x,b.y)[0] for b in swarm.butterflies]
        self.assertTrue(all(2.99<=d<=170.01 for d in distances))
        self.assertGreater(sum(d<65 for d in distances)/len(distances),.85)
        self.assertTrue(any(b.vx>5 for b in swarm.butterflies))
        self.assertTrue(any(b.vx<-5 for b in swarm.butterflies))

    def test_mouse_scatters_then_swarm_returns(self):
        calm=ButterflySwarm(3);scattered=ButterflySwarm(3)
        for swarm in (calm,scattered):swarm.prepare(self.rect)
        pointer=QPointF(480,168)
        near=[i for i,b in enumerate(calm.butterflies) if math.hypot(b.x-pointer.x(),b.y-pointer.y())<60]
        self.assertGreater(len(near),5)
        for _ in range(35):
            calm.advance(.04,self.rect,self.away);scattered.advance(.04,self.rect,pointer)
        def distance(swarm):return sum(math.hypot(swarm.butterflies[i].x-pointer.x(),swarm.butterflies[i].y-pointer.y()) for i in near)/len(near)
        self.assertGreater(distance(scattered),distance(calm)+20)
        peak=sum(scattered.boundary(scattered.butterflies[i].x,scattered.butterflies[i].y)[0] for i in near)/len(near)
        for _ in range(400):scattered.advance(.04,self.rect,self.away)
        settled=sum(scattered.boundary(scattered.butterflies[i].x,scattered.butterflies[i].y)[0] for i in near)/len(near)
        self.assertLess(settled,peak)

    def test_paint_does_not_advance_and_compact_resize_stays_bounded(self):
        swarm=ButterflySwarm(5);swarm.prepare(self.rect)
        snapshot=[(b.x,b.y,b.vx,b.vy) for b in swarm.butterflies]
        image=QImage(1000,1100,QImage.Format.Format_ARGB32_Premultiplied);image.fill(0)
        painter=QPainter(image)
        for _ in range(3):swarm.paint(painter,self.rect,1,False)
        painter.end()
        self.assertEqual(snapshot,[(b.x,b.y,b.vx,b.vy) for b in swarm.butterflies])
        self.assertTrue(any(image.pixelColor(x,y).alpha()>0 for x in range(0,1000,2) for y in range(145,190,2)))
        compact=QRectF(192,192,86,86)
        for _ in range(50):swarm.advance(.04,compact,QPointF(230,170),True)
        self.assertEqual(len(swarm.butterflies),160)
        self.assertTrue(all(2.99<=swarm.boundary(b.x,b.y)[0]<=170.01 for b in swarm.butterflies))
        swarm.advance(.04,self.rect,self.away)
        self.assertEqual(len(swarm.butterflies),420)

    def test_large_variant_triples_wings_without_changing_flight(self):
        swarm=ButterflySwarm(5);swarm.prepare(self.rect)
        b=swarm.butterflies[0];b.x=70;b.y=70;b.size=.09
        swarm.butterflies=[b]
        snapshot=(b.x,b.y,b.vx,b.vy,b.colour.name())
        def bounds(scale):
            image=QImage(140,140,QImage.Format.Format_ARGB32_Premultiplied);image.fill(0)
            painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            swarm.paint(painter,self.rect,1,False,size_multiplier=scale);painter.end()
            pixels=[(x,y) for x in range(140) for y in range(140) if image.pixelColor(x,y).alpha()>10]
            return max(x for x,y in pixels)-min(x for x,y in pixels)+1,max(y for x,y in pixels)-min(y for x,y in pixels)+1
        small=bounds(1);large=bounds(3)
        self.assertGreaterEqual(max(large),max(small)*2.5)
        self.assertEqual(snapshot,(b.x,b.y,b.vx,b.vy,b.colour.name()))
