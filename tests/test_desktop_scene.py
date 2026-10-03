# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Window identity and occlusion fences independent of OS toolkit availability."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('desktop_scene',Path(__file__).resolve().parents[1]/'services/desktop/scene.py')
scene=importlib.util.module_from_spec(spec);spec.loader.exec_module(scene)


class DesktopSceneTests(unittest.TestCase):
    def setUp(self):
        self.target={'window':{'id':'target','pid':123,'title':'Editor','geometry':{'x':0,'y':0,'width':600,'height':400}},
                     'above':[],'screens':[{'name':'screen','geometry':{'x':0,'y':0,'width':1280,'height':800}}]}
        self.dialog={'id':'dialog','pid':123,'geometry':{'x':20,'y':30,'width':100,'height':80}}

    def test_same_process_dialog_appearance_move_and_removal_invalidate(self):
        with_dialog=deepcopy(self.target);with_dialog['above']=[self.dialog]
        self.assertFalse(scene.same_scene(self.target,with_dialog))
        moved=deepcopy(with_dialog);moved['above'][0]['geometry']['x']+=1
        self.assertFalse(scene.same_scene(with_dialog,moved))
        self.assertFalse(scene.same_scene(with_dialog,self.target))

    def test_same_process_foreign_and_unknown_pid_covers_all_block(self):
        for pid in (123,456,0):
            with self.subTest(pid=pid):
                dialog={**self.dialog,'pid':pid};target={**self.target,'above':[dialog]}
                self.assertTrue(scene.covered(target,50,50))
                self.assertFalse(scene.covered(target,150,150))

    def test_cover_geometry_uses_half_open_bounds_and_screen_coordinates(self):
        target={**self.target,'above':[self.dialog]}
        for x,y,blocked in [(20,30,True),(119,109,True),(120,30,False),(20,110,False),(19,30,False)]:
            with self.subTest(x=x,y=y):self.assertEqual(scene.covered(target,x,y),blocked)

    def test_identity_focus_geometry_monitor_and_epoch_changes_invalidate(self):
        for field,value in [('id','replacement'),('pid',456),('geometry',{'x':10,'y':0,'width':600,'height':400})]:
            changed=deepcopy(self.target);changed['window'][field]=value
            self.assertFalse(scene.same_scene(self.target,changed))
        changed=deepcopy(self.target);changed['screens'][0]['geometry']['width']=1920
        self.assertFalse(scene.same_scene(self.target,changed))
        self.assertFalse(scene.same_scene({**self.target,'epoch':'old'},{**self.target,'epoch':'new'}))
        self.assertFalse(scene.same_scene({**self.target,'serial':10},{**self.target,'serial':11}))

    def test_unchanged_scene_and_caption_only_change_remain_valid(self):
        self.assertTrue(scene.same_scene(self.target,deepcopy(self.target)))
        changed=deepcopy(self.target);changed['window']['title']='Editor — Saved'
        self.assertTrue(scene.same_scene(self.target,changed))

    def test_stacking_changes_are_not_discarded_even_when_pids_match(self):
        other={**self.dialog,'id':'popup'}
        self.assertFalse(scene.same_scene({**self.target,'above':[self.dialog,other]},
                                          {**self.target,'above':[other,self.dialog]}))
