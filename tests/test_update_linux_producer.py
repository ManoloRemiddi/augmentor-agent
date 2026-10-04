# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual candidate tar/ZIP boundaries and consumer roundtrip; no build mocks."""
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import subprocess
import tarfile
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('linux_managed_producer',ROOT/'scripts/package-linux-managed.py')
producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
from updates.linux_staging import extract


@unittest.skipUnless(sys.platform=='linux','Linux managed producer/consumer boundaries.')
class ProducerTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory(prefix='augmentor-linux-producer-');self.addCleanup(directory.cleanup)
        self.base=Path(directory.name);self.project=self.base/'project';self.project.mkdir(mode=0o700)

    def archive(self,rows):
        archive=self.base/'python.tar.gz'
        with tarfile.open(archive,'w:gz') as bundle:
            for name,kind,content in rows:
                entry=tarfile.TarInfo(name);entry.type=kind;entry.mode=0o755
                if kind==tarfile.SYMTYPE:entry.linkname=content;entry.size=0;bundle.addfile(entry)
                elif kind==tarfile.REGTYPE:
                    content=content.encode();entry.size=len(content);bundle.addfile(entry,io.BytesIO(content))
                else:bundle.addfile(entry)
        return archive

    def test_safe_python_runtime_keeps_relative_interpreter_link_and_modes(self):
        archive=self.archive([('python/bin/python3.12',tarfile.REGTYPE,'Synthetic runtime'),
            ('python/bin/python3',tarfile.SYMTYPE,'python3.12')])
        runtime=producer.extract_python(archive,self.project)
        self.assertEqual((runtime/'bin/python3').read_text(),'Synthetic runtime')
        self.assertTrue((runtime/'bin/python3').is_symlink())
        self.assertEqual(stat.S_IMODE((runtime/'bin/python3.12').stat().st_mode),0o755)

    def test_unsafe_tar_refuses_before_product_write(self):
        cases=[('python/../../outside',tarfile.REGTYPE,'unsafe'),('another/bin/python3',tarfile.REGTYPE,'unsafe'),
            ('python/bin/python3',tarfile.SYMTYPE,'/outside'),('python/device',tarfile.CHRTYPE,''),
            ('python/linked',tarfile.LNKTYPE,'python/bin/python3')]
        for row in cases:
            with self.subTest(row=row):
                archive=self.archive([row])
                with self.assertRaises(ValueError):producer.extract_python(archive,self.project)
                self.assertEqual(list(self.project.iterdir()),[])

    def test_duplicate_tar_refuses_before_any_product_write(self):
        archive=self.archive([('python/bin/python3',tarfile.REGTYPE,'one'),('python/bin/python3',tarfile.REGTYPE,'two')])
        with self.assertRaisesRegex(ValueError,'Unsupported Python'):producer.extract_python(archive,self.project)
        self.assertEqual(list(self.project.iterdir()),[])

    def test_external_relative_python_link_is_refused_without_outside_write(self):
        archive=self.archive([('python/bin/python3',tarfile.SYMTYPE,'../../../outside')])
        with self.assertRaises((ValueError,tarfile.FilterError)):producer.extract_python(archive,self.project)
        self.assertFalse((self.base/'outside').exists())

    def tree(self):
        (self.project/'python/bin').mkdir(parents=True)
        (self.project/'python/bin/python3.12').write_bytes(b'Synthetic executable');(self.project/'python/bin/python3.12').chmod(0o755)
        (self.project/'python/bin/python3').symlink_to('python3.12')
        (self.project/'release.json').write_text('{"version":"1.0.0"}\n')
        return self.project

    def test_exact_export_roundtrip_uses_the_real_download_consumer(self):
        project=self.tree();expected=producer.snapshot(project);archive=self.base/'bundle.zip'
        report=producer.export(project,archive)
        target=self.base/'extracted';target.mkdir(mode=0o700)
        root,payload=extract(archive,target)
        self.assertEqual(payload,expected);self.assertEqual(producer.snapshot(root),expected)
        self.assertEqual(report['payloadSHA256'],expected['sha256'])
        self.assertEqual(report['sha256'],producer.sha(archive));self.assertFalse(report['automaticInstallQualified'])

    def test_export_is_repeatable_and_preserves_source_bytes(self):
        project=self.tree();before=producer.snapshot(project)
        first=self.base/'first.zip';second=self.base/'second.zip'
        producer.export(project,first);producer.export(project,second)
        self.assertEqual(first.read_bytes(),second.read_bytes());self.assertEqual(producer.snapshot(project),before)

    def test_linux_terminfo_case_distinct_paths_survive_actual_roundtrip(self):
        project=self.tree()
        for name in ('A/ANSI','a/ansi'):
            path=project/'python/share/terminfo'/name
            path.parent.mkdir(parents=True);path.write_text(name)
        archive=self.base/'bundle.zip';producer.export(project,archive)
        stage=self.base/'stage';stage.mkdir(mode=0o700)
        root,payload=extract(archive,stage)
        self.assertEqual(payload,producer.snapshot(project))
        self.assertEqual((root/'python/share/terminfo/A/ANSI').read_text(),'A/ANSI')
        self.assertEqual((root/'python/share/terminfo/a/ansi').read_text(),'a/ansi')

    def test_linux_duplicate_and_link_ancestor_are_still_refused(self):
        for rows in (
                [('same',stat.S_IFREG,b'one'),('same',stat.S_IFREG,b'two')],
                [('A',stat.S_IFLNK,b'elsewhere'),('A/file',stat.S_IFREG,b'unsafe')]):
            with self.subTest(rows=rows):
                archive=self.base/'unsafe.zip'
                with zipfile.ZipFile(archive,'w') as bundle:
                    for name,kind,content in rows:
                        entry=zipfile.ZipInfo(producer.NAME+'/'+name)
                        entry.create_system=3;entry.external_attr=(kind|0o755)<<16
                        bundle.writestr(entry,content)
                with archive.open('rb') as stream,self.assertRaises(ValueError):
                    producer.validate_zip(stream,producer.NAME)

    def test_machine_selection_or_external_product_link_cannot_publish(self):
        project=self.tree();selection=project/'desktop.json';selection.write_text('{"private":"synthetic"}')
        archive=self.base/'bundle.zip'
        with self.assertRaisesRegex(ValueError,'machine-specific'):producer.export(project,archive)
        self.assertFalse(archive.exists());selection.unlink()
        (project/'external').symlink_to('/etc/hosts')
        with self.assertRaisesRegex(ValueError,'external'):producer.export(project,archive)
        self.assertFalse(archive.exists())

    def test_locked_packages_and_both_archives_keep_unqualified_status(self):
        config=json.loads((ROOT/'release/linux-managed.json').read_text())
        lines=(ROOT/'release/linux-managed-requirements.txt').read_text().splitlines()
        locked={line.split()[0].partition('==')[0]:line.partition('==')[2].split()[0] for line in lines if line and not line.startswith('#')}
        self.assertEqual(locked,config['pythonPackages']);self.assertEqual(config['qualificationStatus'],'development-only')
        self.assertEqual(set(config['targets']),{'x64','arm64'})
        for arch,pins in config['targets'].items():
            self.assertFalse(pins['distributionsQualified']);self.assertEqual(pins['target'],'linux-'+arch)
            self.assertRegex(pins['python']['sha256'],r'^[a-f0-9]{64}$');self.assertRegex(pins['node']['sha256'],r'^[a-f0-9]{64}$')

    def test_only_tracked_application_inputs_enter_source_snapshot(self):
        repository=self.base/'repository';repository.mkdir()
        subprocess.run(['git','init','-q',str(repository)],check=True)
        (repository/'.gitignore').write_text('private-state.json\n')
        (repository/'public.py').write_text('# Synthetic reviewed code\n')
        (repository/'private-state.json').write_text('{"token":"synthetic-private-value"}')
        subprocess.run(['git','-C',str(repository),'add','.gitignore','public.py'],check=True)
        subprocess.run(['git','-C',str(repository),'-c','user.name=Augmentor Fixture',
            '-c','user.email=fixture@example.invalid','commit','-qm','Synthetic public inputs'],check=True)
        commit=subprocess.check_output(['git','-C',str(repository),'rev-parse','HEAD'],text=True).strip()
        root=producer.tracked_source(repository,commit,self.base/'reviewed-source')
        self.assertEqual((root/'public.py').read_text(),'# Synthetic reviewed code\n')
        self.assertFalse((root/'private-state.json').exists());self.assertFalse((root/'.git').exists())
