# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic finite native-payload refusal tests; no native execution or qualification."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


qt = load('linux-source-qt')
runtime = load('linux-python-runtime')


class SourceQtTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.home = Path(self.folder.name)
        self.value = runtime.policy(ROOT/'release/ubuntu24.04-python-source-qt-voice.json')

    def tree(self):
        root = self.home/'qt'; root.mkdir()
        paths = ['lib/'+name+'.8.2' for name in sorted(qt.SONAMES)]
        paths += ['plugins/synthetic/file'+str(n) for n in range(49)]
        rows = []
        for path in paths:
            target = root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(b'synthetic')
            rows.append({'path':path,'bytes':9,'sha256':qt.digest(target)})
        links = [{'path':'lib/'+name,'target':name+'.8.2'} for name in sorted(qt.SONAMES)]
        for row in links:(root/row['path']).symlink_to(row['target'])
        value = {'format':'augmentor-source-qt-runtime-stage/1','qtVersion':'6.8.2','qtSonames':sorted(qt.SONAMES),
                 'files':rows,'symlinks':links, 'producerBytesChanged':False,'dynamicClosureQualified':False,
                 'licenseReviewComplete':False,'publicReleaseQualified':False}
        return root, value, self.write_manifest(root,value)

    def write_manifest(self, root, value):
        text = json.dumps(value)
        self.assertLess(len(text),34507)
        (root/'stage-inventory.json').write_text(text+' '*(34507-len(text)))
        return qt.digest(root/'stage-inventory.json')

    def test_finite_payload_accepts_exact_files_and_safe_soname_links(self):
        root,value,sha = self.tree()
        self.assertEqual(qt.manifest(root,sha),value)

    def test_extra_member_missing_library_and_changed_file_are_refused(self):
        root,_,sha = self.tree()
        extra = root/'lib/unreviewed.so';extra.write_bytes(b'synthetic')
        with self.assertRaisesRegex(ValueError,'Unexpected'):qt.manifest(root,sha)
        extra.unlink()
        target = root/'lib/libQt6Core.so.6.8.2';original = target.read_bytes()
        target.write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError,'checksum'):qt.manifest(root,sha)
        target.write_bytes(original);target.unlink()
        with self.assertRaisesRegex(ValueError,'member set'):qt.manifest(root,sha)

    def test_symlink_directory_cannot_redirect_native_file_reads(self):
        root,_,sha = self.tree()
        (root/'plugins').rename(self.home/'plugins')
        (root/'plugins').symlink_to(self.home/'plugins')
        with self.assertRaisesRegex(ValueError,'directory is a link'):qt.manifest(root,sha)

    def test_wrong_link_and_same_byte_hardlink_are_refused(self):
        root,_,sha = self.tree()
        link = root/'lib/libQt6Core.so.6';link.unlink();link.symlink_to('/outside/QtCore')
        with self.assertRaisesRegex(ValueError,'SONAME link differs'):qt.manifest(root,sha)
        link.unlink();link.symlink_to('libQt6Core.so.6.8.2')
        os.link(root/'lib/libQt6Core.so.6.8.2', self.home/'shared')
        with self.assertRaisesRegex(ValueError,'checksum/size/type'):qt.manifest(root,sha)

    def test_changed_manifest_and_unsafe_paths_are_refused(self):
        root,value,sha = self.tree()
        for replacement in ('../outside','/absolute','plugins//double','plugins/./dot','plugins\\other'):
            altered=copy.deepcopy(value);altered['files'][-1]['path']=replacement
            changed_sha=self.write_manifest(root,altered)
            with self.subTest(path=replacement),self.assertRaisesRegex(ValueError,'Unsafe'):
                qt.manifest(root,changed_sha)
        self.write_manifest(root,value);(root/'stage-inventory.json').write_text('changed')
        with self.assertRaisesRegex(ValueError,'checksum'):qt.manifest(root,sha)

    def test_duplicate_members_and_escaping_manifest_link_are_refused(self):
        root,value,_ = self.tree()
        value['files'][-1]=value['files'][0]
        sha=self.write_manifest(root,value)
        with self.assertRaisesRegex(ValueError,'Duplicate'):qt.manifest(root,sha)
        value['files'][-1]={'path':'plugins/synthetic/file48','bytes':9,'sha256':qt.digest(root/'plugins/synthetic/file48')}
        value['symlinks'][0]['target']='../../outside';sha=self.write_manifest(root,value)
        with self.assertRaisesRegex(ValueError,'Unsafe'):qt.manifest(root,sha)

    def test_source_identity_binds_native_manifest_and_derivation(self):
        for key in ('manifestSha256','qtVersion'):
            changed=copy.deepcopy(self.value);changed['sourceQt'][key]='changed'
            self.assertNotEqual(runtime.identity(changed),runtime.identity(self.value))
        changed=copy.deepcopy(self.value);changed['sourceQt']['derivationReceipt']['sha256']='0'*64
        self.assertNotEqual(runtime.identity(changed),runtime.identity(self.value))

    def test_source_policy_cannot_relabel_bindings_or_broaden_host(self):
        for key,replacement in (('target','fedora44-x86_64'),('pythonAbi',[3,14]),('architecture','aarch64')):
            changed=copy.deepcopy(self.value);changed[key]=replacement
            path=self.home/'policy.json';path.write_text(json.dumps(changed))
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Unsupported'):runtime.policy(path)
        for key,replacement in (('name','PySide6-Essentials'),('sha256','0'*64),('url','https://files.pythonhosted.org/packages/substitute.whl')):
            changed=copy.deepcopy(self.value);changed['wheels'][0][key]=replacement
            path.write_text(json.dumps(changed))
            with self.subTest(key=key),self.assertRaises(ValueError):runtime.policy(path)
        changed=copy.deepcopy(self.value);changed['sourceQt']['manifestSha256']='0'*64
        path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'exact reviewed native'):runtime.policy(path)

    def test_native_input_failure_precedes_python_and_runtime_creation(self):
        with patch.object(runtime,'verify_wheels'),patch.object(runtime,'host') as host,\
                patch.object(runtime.subprocess,'run') as run:
            with self.assertRaises(ValueError):runtime.prepare(self.value,self.home/'absent-inputs',self.home/'store')
        host.assert_not_called();run.assert_not_called();self.assertFalse((self.home/'store').exists())

    def test_source_preload_refusal_precedes_system_python_abi_probe(self):
        with patch.object(runtime.Path,'read_text',return_value='ID=ubuntu\nVERSION_ID=24.04\n'),\
                patch.object(runtime.platform,'machine',return_value='x86_64'),\
                patch.dict(os.environ,{'LD_PRELOAD':'/unreviewed.so'}),\
                patch.object(runtime.subprocess,'check_output') as python:
            with self.assertRaisesRegex(ValueError,'unreviewed loader'):runtime.host(self.value)
        python.assert_not_called()

    def test_native_stage_preserves_prior_destination_and_cleans_only_new_failure(self):
        root,value,sha=self.tree();self.value['sourceQt']['manifestSha256']=sha
        source=self.home/'inputs';source.mkdir();root.rename(source/'source-qt')
        destination=self.home/'installed';destination.mkdir();(destination/'prior').write_text('retained')
        with patch.object(qt,'inputs',return_value=value):
            with self.assertRaises(FileExistsError):qt.stage(self.value,source,destination)
        self.assertEqual((destination/'prior').read_text(),'retained')
        missing=self.home/'new'
        with patch.object(qt,'inputs',return_value=value),patch.object(qt.shutil,'copyfileobj',side_effect=OSError('copy interrupted')):
            with self.assertRaisesRegex(OSError,'copy interrupted'):qt.stage(self.value,source,missing)
        self.assertFalse(missing.exists());self.assertEqual((destination/'prior').read_text(),'retained')

    def test_loader_preloads_are_refused_and_display_decisions_preserved(self):
        for key in ('LD_PRELOAD','LD_AUDIT'):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'unreviewed loader'):
                qt.environment(self.home,{key:'/outside.so'})
        inherited={'LD_LIBRARY_PATH':'/producer/lib','QT_PLUGIN_PATH':'/producer/plugins',
                   'QT_QPA_PLATFORM':'wayland','QT_QUICK_BACKEND':'opengl','DISPLAY':':2',
                   'XDG_SESSION_TYPE':'wayland','PYTHONPATH':'/app/native','NODE_SELECTION':'chosen'}
        env=qt.environment(self.home,inherited)
        for key in ('QT_QPA_PLATFORM','QT_QUICK_BACKEND','DISPLAY','XDG_SESSION_TYPE','PYTHONPATH','NODE_SELECTION'):
            self.assertEqual(env[key],inherited[key])
        self.assertEqual(env['LD_LIBRARY_PATH'],str(self.home/'qt/lib'))
        self.assertEqual(env['QML_IMPORT_PATH'],str(self.home/'qt/qml'))
        self.assertEqual(inherited['LD_LIBRARY_PATH'],'/producer/lib')

    def test_vendor_identity_and_native_environment_are_unchanged(self):
        vendor=runtime.policy(ROOT/'release/ubuntu24.04-python-voice.json')
        app=self.home/'app';app.mkdir();(app/runtime.POLICY_FILE).write_text(json.dumps(vendor))
        inherited={'LD_LIBRARY_PATH':'/owner/paths','QT_QPA_PLATFORM':'xcb'}
        with patch.object(runtime,'resolve',return_value='/existing/bin/python3'):
            env=runtime.environment(app,'/existing/bin/python3',inherited)
        for key,val in inherited.items():self.assertEqual(env[key],val)
        altered=copy.deepcopy(vendor);altered['sourceQt']=self.value['sourceQt']
        (app/runtime.POLICY_FILE).write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError,'cannot declare source Qt'):runtime.policy(app/runtime.POLICY_FILE)

    def test_root_owned_package_is_readable_without_interpreting_symlink_mode_as_write_permission(self):
        prefix='python-wheels/source-qt';link=prefix+'/lib/libQt6Core.so.6'
        metadata={prefix:(0,0,0o755,True),prefix+'/lib':(0,0,0o755,True),
                  prefix+'/lib/libQt6Core.so.6.8.2':(0,0,0o644,False),link:(0,0,0o777,False)}
        self.assertTrue(qt.package_permissions(metadata,{link:'libQt6Core.so.6.8.2'},prefix+'/'))
        for name,record in ((prefix,(0,0,0o700,True)),
                            (prefix+'/lib/libQt6Core.so.6.8.2',(0,0,0o640,False)),
                            (prefix+'/lib/libQt6Core.so.6.8.2',(0,0,0o666,False))):
            changed=dict(metadata);changed[name]=record
            with self.subTest(name=name,mode=record[2]),self.assertRaisesRegex(ValueError,'unreadable'):
                qt.package_permissions(changed,{link:'libQt6Core.so.6.8.2'},prefix)
        metadata[prefix]=(1001,1001,0o755,True)
        with self.assertRaisesRegex(ValueError,'ownership'):qt.package_permissions(metadata,{link:'libQt6Core.so.6.8.2'},prefix)


if __name__=='__main__':unittest.main()
