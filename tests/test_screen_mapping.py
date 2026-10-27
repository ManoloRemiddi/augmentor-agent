# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('screen_mapping',Path(__file__).resolve().parents[1]/'services/desktop/screen_mapping.py')
mapping=importlib.util.module_from_spec(spec);spec.loader.exec_module(mapping)

class ScreenMappingTests(unittest.TestCase):
    def setUp(self):
        self.screens=[{'name':'rotated','geometry':{'x':0,'y':0,'width':720,'height':2560}},
                      {'name':'fractional','geometry':{'x':720,'y':664,'width':1463,'height':823}},
                      {'name':'negative','geometry':{'x':-1920,'y':0,'width':1920,'height':1080}}]
        self.streams=[(i,{'position':(s['geometry']['x'],s['geometry']['y']),'size':(s['geometry']['width'],s['geometry']['height'])}) for i,s in enumerate(self.screens,1)]
    def test_multihead_selects_exact_logical_screen_independent_of_frame_pixels(self):
        for index,screen in enumerate(self.screens):
            r=screen['geometry'];scene={'screens':self.screens,'window':{'geometry':{**r,'width':r['width']//2}}}
            node,properties,selected=mapping.select_stream(self.streams,scene)
            self.assertEqual(node,index+1);self.assertEqual(selected,screen)
    def test_ambiguous_missing_or_changed_topology_is_not_guessed(self):
        with self.assertRaisesRegex(RuntimeError,'did not identify'):mapping.match_screen({},self.screens)
        with self.assertRaisesRegex(RuntimeError,'no longer matches'):mapping.match_screen({'position':(999,0),'size':(720,2560)},self.screens)
        self.assertEqual(mapping.match_screen({},self.screens[:1]),self.screens[0])
    def test_partial_window_uses_greatest_shared_overlap_and_offscreen_window_refuses(self):
        scene={'screens':self.screens,'window':{'geometry':{'x':650,'y':700,'width':500,'height':500}}}
        self.assertEqual(mapping.select_stream(self.streams,scene)[0],2)
        scene['window']['geometry']['y']=10000
        with self.assertRaisesRegex(RuntimeError,'outside the shared'):mapping.select_stream(self.streams,scene)

if __name__=='__main__':unittest.main()
