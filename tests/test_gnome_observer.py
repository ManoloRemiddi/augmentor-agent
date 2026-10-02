# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Observer protocol and compositor/epoch fences; no live desktop mutation."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

spec=importlib.util.spec_from_file_location('gnome_observer_protocol',Path(__file__).resolve().parents[1]/'services/desktop/gnome.py')
gnome=importlib.util.module_from_spec(spec);spec.loader.exec_module(gnome)
EPOCH='01234567-89ab-cdef-0123-456789abcdef'


def fixture():
    window={'id':EPOCH+':1','pid':123,'application':'fixture','title':'Editor',
            'geometry':{'x':-20,'y':30,'width':300,'height':200},'overrideRedirect':False,'unmanaging':False}
    return {'schema':1,'backend':'gnome-shell-observer','shellVersion':'50.5','epoch':EPOCH,'serial':10,
        'inputQualified':False,'window':window,'windows':[window],'above':[],
        'screens':[{'name':'monitor:0','geometry':{'x':0,'y':0,'width':1280,'height':800},'scale':1}],
        'workspace':{'id':1,'index':0},'blockedReasons':['screen-shield-unavailable'],
        'guards':{'locked':False,'greeter':False,'sessionMode':'user','actionMode':1,'modalCount':0,'overview':False,
                  'overviewTarget':False,'overviewAnimation':False,'stageGrabbed':False,'windowDragging':False,
                  'stageGrabActor':None,'stageKeyFocus':None,'screenShieldAvailable':False,
                  'screenShieldActive':None,'screenShieldLocked':None}}


class GnomeObserverTests(unittest.TestCase):
    def test_46_profile_requires_parent_mode_and_remains_read_only(self):
        value=fixture();value['shellVersion']='46.0';value['guards']['sessionMode']='ubuntu'
        with self.assertRaisesRegex(RuntimeError,'incomplete session mode'):gnome.valid_scene(value)
        value['guards']['parentSessionMode']='user'
        self.assertEqual(gnome.valid_scene(value),value)
        value['inputQualified']=True
        with self.assertRaises(RuntimeError):gnome.valid_scene(value)
        value['inputQualified']=False;value['guards']['parentSessionMode']=True
        with self.assertRaisesRegex(RuntimeError,'parent session mode'):gnome.valid_scene(value)

    def test_48_modern_profile_retains_epoch_and_read_only_fences(self):
        value=fixture();value['shellVersion']='48.4'
        self.assertEqual(gnome.valid_scene(value),value)
        value['inputQualified']=True
        with self.assertRaises(RuntimeError):gnome.valid_scene(value)

    def test_real_schema_preserves_negative_coordinates_and_unavailable_provider(self):
        value=fixture();self.assertEqual(gnome.valid_scene(value),value)
        value['window']['pid']=0;self.assertEqual(gnome.valid_scene(value),value)

    def test_malformed_oversize_nonfinite_and_nonobject_json_are_refused(self):
        for value in ('null','[1]','{broken','x'*131073,'{"number": NaN}'):
            with self.subTest(value=value[:20]),self.assertRaises(RuntimeError):gnome.parsed(value)

    def test_false_input_qualification_and_valid_epoch_serial_are_required(self):
        for field,value in [('inputQualified',True),('serial',True),('serial',2**53),('epoch','old-session'),('shellVersion','49.5')]:
            status=fixture();status[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):gnome.valid_status(status)

    def test_duplicate_identity_missing_focus_and_unlisted_cover_are_refused(self):
        value=fixture();value['windows'].append(deepcopy(value['window']))
        with self.assertRaisesRegex(RuntimeError,'duplicate'):gnome.valid_scene(value)
        value=fixture();value['windows']=[]
        with self.assertRaisesRegex(RuntimeError,'absent'):gnome.valid_scene(value)
        value=fixture();value['above']=[{**value['window'],'id':EPOCH+':2'}]
        with self.assertRaisesRegex(RuntimeError,'covering'):gnome.valid_scene(value)

    def test_missing_lock_stage_geometry_and_scale_metadata_are_refused(self):
        for key in ('locked','stageKeyFocus','screenShieldLocked','screenShieldAvailable','sessionMode'):
            value=fixture();del value['guards'][key]
            with self.subTest(key=key),self.assertRaises(RuntimeError):gnome.valid_scene(value)
        for bad in (float('inf'),True,0):
            value=fixture();value['window']['geometry']['width']=bad
            with self.assertRaises(RuntimeError):gnome.valid_scene(value)
        value=fixture();value['screens'][0]['scale']=float('nan')
        with self.assertRaises(RuntimeError):gnome.valid_scene(value)

    def observer(self,reply):
        observer=gnome.GnomeObserver.__new__(gnome.GnomeObserver)
        observer.owner=':1.23';observer.epoch=EPOCH
        observer.current_owner=Mock(return_value=observer.owner)
        observer.Gio=SimpleNamespace(DBusCallFlags=SimpleNamespace(NO_AUTO_START=4))
        observer.GLib=SimpleNamespace(Variant=lambda signature,value:(signature,value))
        observer.bus=Mock();observer.bus.call_sync.return_value.unpack.return_value=(json.dumps(reply),)
        return observer

    def test_unique_compositor_owner_is_fenced_before_and_after_bounded_call(self):
        observer=self.observer(fixture());observer.read()
        call=observer.bus.call_sync.call_args.args
        self.assertEqual(call[0],':1.23');self.assertEqual(call[6:8],(4,1000))
        observer=self.observer(fixture());observer.current_owner.side_effect=[':1.23',':1.99']
        with self.assertRaisesRegex(RuntimeError,'Shell changed'):observer.read()
        observer=self.observer(fixture());observer.current_owner.return_value=':1.99'
        with self.assertRaisesRegex(RuntimeError,'Shell changed'):observer.read()
        observer.bus.call_sync.assert_not_called()

    def test_extension_restart_and_inconsistent_point_guard_are_refused(self):
        value=fixture();value['epoch']='ffffffff-ffff-ffff-ffff-ffffffffffff'
        with self.assertRaisesRegex(RuntimeError,'restarted'):self.observer(value).read()
        point={'schema':1,'epoch':EPOCH,'serial':10,'inputQualified':False,'expected':EPOCH+':1',
               'blocked':False,'windowMatches':True,'reactiveWindowMatches':True,'paintedWindowMatches':False}
        with self.assertRaisesRegex(RuntimeError,'invalid point'):self.observer(point).inspect_point(EPOCH+':1',10,20)
