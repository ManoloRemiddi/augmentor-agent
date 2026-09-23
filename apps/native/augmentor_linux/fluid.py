# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Small CPU fluid field for the halo: backtraced, bilinearly sampled transport.

Algorithm reference: GPU Gems, chapter 38 (Harris), following Stam's Stable
Fluids. This is a visual smoke transport model, not a physical plasma solver.
"""
import math
import numpy as np


class FluidField:
    def __init__(self):
        self.dye=None;self.origin=None;self.pointer=None

    @staticmethod
    def sample(field,x,y):
        h,w=field.shape[:2]
        valid=(x>=0)&(y>=0)&(x<=w-1)&(y<=h-1)
        x=np.clip(x,0,w-1);y=np.clip(y,0,h-1)
        ix=x.astype(np.int32);iy=y.astype(np.int32)
        jx=np.minimum(ix+1,w-1);jy=np.minimum(iy+1,h-1)
        fx=x-ix.astype(np.float32);fy=y-iy.astype(np.float32)
        if field.ndim==3:fx=fx[...,None];fy=fy[...,None];valid=valid[...,None]
        return ((field[iy,ix]*(1-fx)+field[iy,jx]*fx)*(1-fy)+(field[jy,ix]*(1-fx)+field[jy,jx]*fx)*fy)*valid

    def reset(self,source,origin):
        h,w=source.shape[:2]
        self.y,self.x=np.mgrid[:h,:w].astype(np.float32)
        self.velocity=np.zeros((h,w,2),np.float32)
        self.dye=source.copy();self.origin=origin;self.pointer=None

    def step(self,rgba,origin,cell,dt,pointer,distance):
        source=np.asarray(rgba,dtype=np.float32)/255
        source[...,:3]*=source[...,3,None]
        if self.dye is None or self.dye.shape!=source.shape:self.reset(source,origin)
        dt=max(.001,min(.08,dt))
        shift=((origin[0]-self.origin[0])/cell[0],(origin[1]-self.origin[1])/cell[1])
        self.origin=origin
        # Rebase old smoke into the new window-local grid, preserving its
        # desktop position. Fractional motion uses interpolation, never splats.
        if abs(shift[0])+abs(shift[1])>0:
            self.dye=self.sample(self.dye,self.x+shift[0],self.y+shift[1])
            self.velocity=self.sample(self.velocity,self.x+shift[0],self.y+shift[1])
        # Integrate emission along a moving border during this frame. This
        # prevents separate outline stamps when the window moves quickly.
        steps=min(8, math.ceil(max(abs(shift[0]), abs(shift[1]))))
        if steps>1:
            swept=source.copy()
            for i in range(1,steps):
                fraction=i/steps
                swept+=self.sample(source,self.x+shift[0]*fraction,self.y+shift[1]*fraction)
            source=.5*source+.5*swept/steps
        velocity=self.velocity
        if self.pointer is not None:
            dx=pointer[0]-self.pointer[0];dy=pointer[1]-self.pointer[1]
            speed=math.hypot(dx,dy)
            if .1<speed<250:
                # A swept finger-sized impulse follows pointer motion. No
                # radial alpha mask: stopping the mouse applies no force.
                wx=origin[0]+(self.x+.5)*cell[0];wy=origin[1]+(self.y+.5)*cell[1]
                along=np.clip(((wx-self.pointer[0])*dx+(wy-self.pointer[1])*dy)/(speed*speed),0,1)
                r2=(wx-self.pointer[0]-along*dx)**2+(wy-self.pointer[1]-along*dy)**2
                force=np.exp(-r2/(2*14**2))*.32
                velocity[...,0]+=force*np.clip(dx/dt,-700,700)/cell[0]
                velocity[...,1]+=force*np.clip(dy/dt,-700,700)/cell[1]
        self.pointer=pointer
        velocity=self.sample(velocity,self.x-dt*velocity[...,0],self.y-dt*velocity[...,1])
        velocity*=math.exp(-dt/.5)
        # Project away divergence so a stroke curls around neighbouring smoke
        # rather than stretching a circular hole into the density texture.
        vx,vy=velocity[...,0],velocity[...,1]
        divergence=np.zeros_like(vx)
        divergence[1:-1,1:-1]=.5*(vx[1:-1,2:]-vx[1:-1,:-2]+vy[2:,1:-1]-vy[:-2,1:-1])
        pressure=np.zeros_like(vx)
        for _ in range(24):
            next_pressure=np.zeros_like(pressure)
            next_pressure[1:-1,1:-1]=.25*(pressure[1:-1,2:]+pressure[1:-1,:-2]+pressure[2:,1:-1]+pressure[:-2,1:-1]-divergence[1:-1,1:-1])
            pressure=next_pressure
        vx[1:-1,1:-1]-=.5*(pressure[1:-1,2:]-pressure[1:-1,:-2])
        vy[1:-1,1:-1]-=.5*(pressure[2:,1:-1]-pressure[:-2,1:-1])
        velocity[[0,-1],:]=0;velocity[:,[0,-1]]=0
        self.velocity=velocity
        transported=self.sample(self.dye,self.x-dt*vx,self.y-dt*vy)
        # Rapidly replenish hot roots; let detached wisps cool and dissipate.
        retention=np.exp(-dt/(.07+.3*np.clip(distance/60,0,1)))[...,None]
        self.dye=transported*retention+source*(1-retention)
        self.dye[[0,-1],:]=0;self.dye[:,[0,-1]]=0
        return np.clip(self.dye*255,0,255).astype(np.uint8)
