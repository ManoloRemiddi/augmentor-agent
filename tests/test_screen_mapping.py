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

    def test_kde_size_only_monitor_metadata_is_bound_without_frame_pixel_guessing(self):
        streams=[(node,{'size':p['size'],'source_type':1}) for node,p in self.streams]
        bindings=mapping.bind_streams(streams,self.screens);saved=mapping.topology(self.screens)
        for index,screen in enumerate(self.screens):
            scene={'screens':list(reversed(self.screens)),'window':{'geometry':screen['geometry']}}
            node,_,selected=mapping.select_stream(streams,scene,bindings,saved)
            self.assertEqual((node,selected['name']),(index+1,screen['name']))

    def test_duplicate_sizes_rotation_or_missing_size_cannot_select_an_output(self):
        duplicate={**self.screens[0],'name':'same-size','geometry':{**self.screens[0]['geometry'],'x':4000}}
        with self.assertRaisesRegex(RuntimeError,'identical logical sizes'):
            mapping.bind_streams([(1,{'source_type':1,'size':(720,2560)})],[*self.screens,duplicate])
        for p in [{'source_type':1,'size':(2560,720)},{'position':(0,0)},
                  {'source_type':2,'size':(720,2560)},{'size':(720,2560)}]:
            with self.subTest(properties=p),self.assertRaises(RuntimeError):mapping.match_screen(p,self.screens)

    def test_injective_stream_binding_rejects_duplicates_and_unidentified_multihead(self):
        for streams in [[(1,{}),(2,{})],[(1,self.streams[0][1]),(1,self.streams[1][1])],
                        [(1,self.streams[0][1]),(2,self.streams[0][1])]]:
            with self.subTest(streams=streams),self.assertRaises(RuntimeError):mapping.bind_streams(streams,self.screens)
        self.assertEqual(mapping.bind_streams([(1,{})],self.screens[:1]),{1:'rotated'})
        with self.assertRaises(RuntimeError):mapping.bind_streams([(1,{}),(2,{})],self.screens[:1])

    def test_bound_topology_cannot_rematch_after_move_scale_rotation_or_rename(self):
        import copy
        bindings=mapping.bind_streams(self.streams,self.screens);saved=mapping.topology(self.screens)
        for field,value in [('x',1),('width',2560),('name','replacement'),('scale',1.75),('transform',1)]:
            changed=copy.deepcopy(self.screens)
            if field in ('x','width'):changed[2]['geometry'][field]=value
            else:changed[2][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(RuntimeError,'topology changed'):
                mapping.select_stream(self.streams,{'screens':changed,'window':{'geometry':self.screens[0]['geometry']}},bindings,saved)
        for names in [['', 'two','three'],['same','same','three']]:
            changed=copy.deepcopy(self.screens)
            for screen,name in zip(changed,names):screen['name']=name
            with self.assertRaises(RuntimeError):mapping.bind_streams(self.streams,changed)

if __name__=='__main__':unittest.main()
