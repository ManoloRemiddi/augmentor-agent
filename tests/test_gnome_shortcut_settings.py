# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""GSD schema generations and transaction failures; no grab-delivery claim."""
from contextlib import nullcontext
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

spec=importlib.util.spec_from_file_location('gnome_settings_backend',Path(__file__).resolve().parents[1]/'services/desktop/gnome_shortcuts.py')
backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)


class Schema:
    def __init__(self,keys):self.keys=keys
    def has_key(self,key):return key in self.keys
    def get_key(self,key):
        return SimpleNamespace(get_value_type=lambda:SimpleNamespace(dup_string=lambda:self.keys[key]))


def schemas(version,portal=False):
    fields={'name':'s','binding':'s','command':'s'}
    if version==50:fields['enable-in-lockscreen']='b'
    result={backend.CUSTOM:Schema(fields)}
    if portal:
        result[backend.PORTAL]=Schema({'applications':'as'})
        result[backend.PORTAL+'.application']=Schema({'shortcuts':'a(sa{sv})'})
    return result


class Variant:
    def __init__(self,kind,value):self.kind,self.value=kind,value
    def unpack(self):return self.value


class Entry:
    def __init__(self,values):self.values=dict(values);self.pending=None;self.fail_key=None
    def get_value(self,key):return Variant('b' if isinstance(self.values[key],bool) else 's',self.values[key])
    def get_string(self,key):return self.values[key]
    def is_writable(self,key):return key in self.values
    def delay(self):self.pending={}
    def set_value(self,key,value):
        if key==self.fail_key:return False
        if self.pending is None:self.values[key]=value.unpack()
        else:self.pending[key]=value.unpack()
        return True
    def apply(self):self.values.update(self.pending or {});self.pending=None
    def revert(self):self.pending=None


class GnomeSettingsProfiles(unittest.TestCase):
    def profile(self,version,rows):
        return backend.settings_profile(version,SimpleNamespace(lookup=lambda name,recursive:rows.get(name)))

    def test_46_has_three_fields_and_no_saved_portal_schemas(self):
        self.assertEqual(self.profile('46.0',schemas(46)),(backend.FIELDS,False))
        self.assertEqual(self.profile('46.2',schemas(46,True)),(backend.FIELDS,True))

    def test_50_keeps_explicit_lock_exclusion_and_portal_checks(self):
        self.assertEqual(self.profile('50.5',schemas(50,True)),(backend.FIELDS+('enable-in-lockscreen',),True))
        for rows in (schemas(46,True),schemas(50)):
            with self.assertRaises(RuntimeError):self.profile('50.5',rows)

    def test_unreviewed_versions_partial_portal_and_malformed_present_schemas_refuse(self):
        for version in ('45.9','47.0','48.3','49.5','51.0','46.0-foreign',None):
            with self.subTest(version=version),self.assertRaises(RuntimeError):self.profile(version,schemas(46))
        rows=schemas(46);rows[backend.PORTAL]=Schema({'applications':'as'})
        with self.assertRaises(RuntimeError):self.profile('46.0',rows)
        for name,key,kind in ((backend.PORTAL,'applications','s'),(backend.PORTAL+'.application','shortcuts','as'),
                              (backend.CUSTOM,'binding','as')):
            rows=schemas(46,True);rows[name].keys[key]=kind
            with self.subTest(schema=name),self.assertRaises(RuntimeError):self.profile('46.0',rows)

    def transaction(self,version):
        obj=backend.NativeShortcuts.__new__(backend.NativeShortcuts)
        obj.fields,obj.portal_available=self.profile(version,schemas(int(version.split('.')[0]),version.startswith('50.')))
        old={'name':'Augmentor Agent','binding':'<Super>F8','command':'canonical'}
        if 'enable-in-lockscreen' in obj.fields:old['enable-in-lockscreen']=False
        entry=Entry(old);parent=Mock();paths=[backend.PREFIX+'main/','/foreign/']
        parent.get_strv.side_effect=lambda key:list(paths)
        def set_paths(key,value):paths[:]=value;return True
        parent.set_strv.side_effect=set_paths;parent.is_writable.return_value=True
        obj.parent=parent;obj.custom=Mock(return_value=entry);obj.owned=Mock();obj.conflicts=Mock()
        obj.encode=Mock(return_value='<Super>F9');obj.launcher=Mock(return_value='canonical')
        obj.GLib=SimpleNamespace(Variant=Variant);obj.Gio=SimpleNamespace(Settings=SimpleNamespace(sync=lambda:None))
        obj.read=Mock(return_value={'functionalTested':False})
        return obj,entry,paths,old

    def test_save_46_never_writes_nonexistent_key_and_50_clears_lock_enable(self):
        for version in ('46.0','50.5'):
            obj,entry,paths,old=self.transaction(version)
            if version.startswith('50.'):entry.values['enable-in-lockscreen']=True
            with patch.object(backend,'locked',return_value=nullcontext()):
                self.assertEqual(obj.save('main',{}),{'functionalTested':False})
            self.assertEqual(entry.values['binding'],'<Super>F9');self.assertIn('/foreign/',paths)
            if version.startswith('50.'):self.assertIs(entry.values['enable-in-lockscreen'],False)
            else:self.assertNotIn('enable-in-lockscreen',entry.values)

    def test_registration_failure_rolls_back_only_own_values_and_preserves_foreign_entry(self):
        for version in ('46.0','50.5'):
            obj,entry,paths,old=self.transaction(version);paths.remove(backend.PREFIX+'main/')
            obj.parent.set_strv.return_value=False;obj.parent.set_strv.side_effect=None
            with patch.object(backend,'locked',return_value=nullcontext()),self.assertRaisesRegex(RuntimeError,'registration'):
                obj.save('main',{})
            self.assertEqual(entry.values,old);self.assertEqual(paths,['/foreign/']);obj.read.assert_not_called()

    def test_conflict_refuses_before_mutation_for_both_profiles(self):
        for version in ('46.0','50.5'):
            obj,entry,paths,old=self.transaction(version);obj.conflicts.side_effect=ValueError('already assigned')
            with patch.object(backend,'locked',return_value=nullcontext()),self.assertRaises(ValueError):obj.save('main',{})
            self.assertEqual(entry.values,old);self.assertIsNone(entry.pending);obj.parent.set_strv.assert_not_called()


if __name__=='__main__':unittest.main()
