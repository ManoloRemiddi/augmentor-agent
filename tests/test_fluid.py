# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
import numpy as np
from augmentor_linux.fluid import FluidField


class FluidTests(unittest.TestCase):
    def test_fractional_sampling_preserves_continuous_ramp(self):
        y,x=np.mgrid[:24,:32].astype(np.float32)
        field=x*.01+y*.02
        result=FluidField.sample(field,x+.37,y+.62)
        np.testing.assert_allclose(result[2:-2,2:-2],(field+.37*.01+.62*.02)[2:-2,2:-2],atol=1e-6)

    def test_stationary_pointer_does_not_cut_a_hole(self):
        source=np.full((48,48,4),180,np.uint8);distance=np.full((48,48),30,np.float32)
        a=FluidField();b=FluidField()
        for _ in range(8):
            near=a.step(source,(0,0),(4,4),.04,(96,96),distance)
            far=b.step(source,(0,0),(4,4),.04,(1000,1000),distance)
        np.testing.assert_array_equal(near,far)
        self.assertEqual(float(np.max(np.abs(a.velocity))),0)

    def test_pointer_stroke_stirs_persistent_velocity_without_erasing_density(self):
        source=np.zeros((48,48,4),np.uint8);source[:,20:24]=[120,200,180,180]
        distance=np.full((48,48),35,np.float32);field=FluidField()
        field.step(source,(0,0),(4,4),.04,(64,96),distance)
        before=field.dye.copy()
        field.step(source,(0,0),(4,4),.04,(100,96),distance)
        self.assertGreater(float(np.max(np.abs(field.velocity))),1)
        self.assertGreater(float(np.sum(np.abs(field.dye-before))),.1)
        self.assertTrue(np.isfinite(field.dye).all())
        moving=float(np.max(np.abs(field.velocity)))
        for _ in range(30):field.step(source,(0,0),(4,4),.04,(100,96),distance)
        self.assertLess(float(np.max(np.abs(field.velocity))),moving*.3)

    def test_window_motion_leaves_smooth_world_space_wake(self):
        source=np.zeros((32,64,4),np.uint8);source[:,28:34]=[120,200,180,180]
        distance=np.full((32,64),60,np.float32);field=FluidField()
        field.step(source,(0,0),(4,4),.04,(-1000,-1000),distance)
        moved=field.step(source,(19,0),(4,4),.04,(-1000,-1000),distance)
        self.assertGreater(int(moved[16,24,3]),0)
        self.assertTrue(np.all(moved[16,24:34,3]>0))
        for _ in range(40):moved=field.step(source,(19,0),(4,4),.04,(-1000,-1000),distance)
        self.assertLess(int(moved[16,24,3]),4)
