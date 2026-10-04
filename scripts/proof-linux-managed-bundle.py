#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise an actual produced ZIP through staging and offline target UI health.

Uses an isolated temporary selection/profile. No publisher trust, live DSH,
normal GUI, update installation or production eligibility is claimed.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from lifecycle.macos_payload import snapshot
from platform_adapters.private_files import atomic_json,descriptor,read_json
from updates.linux_staging import stage_download
from updates.linux_managed import load_deployment


def prove(directory):
    report=json.loads((directory/'artifact.json').read_text());item=report['artifact']
    if report['publicReleaseReady'] is not False or item['automaticInstallQualified'] is not False:
        raise ValueError('This proof requires an explicitly unqualified candidate.')
    project=directory/'Augmentor Agent Desktop';original=snapshot(project)
    receipt=json.loads((project/'release.json').read_text())
    with tempfile.TemporaryDirectory(prefix='augmentor-linux-bundle-proof-') as folder:
        base=Path(folder);environment=os.environ.copy()
        try:
            for key,relative in (('XDG_CONFIG_HOME','config'),('XDG_STATE_HOME','state'),('XDG_DATA_HOME','data'),
                    ('XDG_RUNTIME_DIR','run'),('XDG_CACHE_HOME','cache'),('AUGMENTOR_SHARED_CONFIG','config/shared'),
                    ('AUGMENTOR_SHARED_STATE','run/shared'),('AUGMENTOR_SHARED_DATA','data/shared')):
                path=base/relative;path.mkdir(mode=0o700,parents=True,exist_ok=True);os.environ[key]=str(path)
            data=base/'data/augmentor';data.mkdir(mode=0o700);stage=base/'stage';stage.mkdir(mode=0o700)
            previous={'root':str(project),'python':str(project/'python/bin/python3'),
                'node':str(project/'node/bin/node'),'version':receipt['version'],'dshService':None}
            atomic_json(data/'desktop.json',previous)
            artifact={'role':'bundle','targetPath':'releases/download/ci-managed-bundle/'+item['file'],
                'sha256':item['sha256'],'bytes':item['bytes']}
            candidate={key:receipt[key] for key in ('version','sourceCommit','channel','target','protocols','dataSchema','readableDataSchemas')}
            candidate.update(build=report['build'],component='desktop',installType='managed-linux',
                releaseUrl='https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/ci-managed-bundle',
                minimumOS='6.8',distributions=receipt['candidateDistributions'],
                automaticInstallQualified=False,artifacts=[artifact])
            fd=descriptor(directory/item['file'])
            try:
                target,raw,payload=stage_download({'artifact':artifact,'fd':fd},stage,candidate,data,development=True)
            finally:os.close(fd)
            if json.loads(raw)!=receipt or read_json(data/'desktop.json')!=previous:
                raise ValueError('Staging changed the exact receipt or original selection.')
            tool=load_deployment(data);manifest=tool.verify(target);configuration=manifest['deployment']
            if any(configuration[key]!=str(target/path) for key,path in (
                    ('python','python/bin/python3'),('node','node/bin/node'))):
                raise ValueError('Bundled runtimes did not follow the final immutable release.')
            health=json.loads(subprocess.check_output([configuration['python'],'-I','-B',
                str(target/'scripts/linux-local-health.py')],timeout=60))
            portal_code=('import sys,unittest;sys.path.insert(0,'+repr(str(target))+');'
                'suite=unittest.defaultTestLoader.discover('+repr(str(ROOT/'tests'))+
                ',pattern="test_dictation_portal.py");'
                'result=unittest.TextTestRunner(verbosity=2).run(suite);'
                'sys.exit(0 if result.wasSuccessful() and result.testsRun==2 and not result.skipped else 1)')
            subprocess.run(['dbus-run-session','--',configuration['python'],'-I','-B','-c',portal_code],
                env={**os.environ,'AUGMENTOR_PORTAL_PROOF':'1'},check=True,timeout=60)
            native_report=base/'dictation-proof.json'
            try:
                subprocess.run(['xvfb-run','-a','dbus-run-session','--',configuration['python'],'-I','-B',
                    str(target/'scripts/proof-dictation-maintenance.py'),'--runtime',str(target/'components/handy/runtime'),
                    '--out',str(native_report)],capture_output=True,check=True,timeout=180)
            except subprocess.CalledProcessError as error:
                sys.stderr.write(error.stderr[-4096:].decode('utf-8',errors='replace'));raise
            with native_report.open('rb') as stream:record=stream.read(4097)
            if len(record)>4096:raise ValueError('The staged native fixture report exceeded its bound.')
            dictation=json.loads(record)
            if (not isinstance(dictation,dict) or dictation.get('schema')!='augmentor-dictation-maintenance-proof/1'
                    or any(dictation.get(key) is not True for key in ('actualHandy','nativeOwnerPreserved',
                        'nativeAtomicReservation','brokerAdmissionFenced','cancellationRestoredAdmission',
                        'settingsPreserved','ordinaryChildExit'))
                    or any(dictation.get(key) is not False for key in ('microphoneCapture','modelDownload','automaticInstallQualified'))):
                raise ValueError('The staged native dictation component did not pass its bounded private fixture.')
            if (health!=report['offlineHealth'] or snapshot(target)!=payload or snapshot(project)!=original
                    or read_json(data/'desktop.json')!=previous):
                raise ValueError('The staged target or source changed during actual offline health.')
            return {'schema':'augmentor-linux-managed-bundle-proof/1','target':receipt['target'],
                'sourceCommit':receipt['sourceCommit'],'artifactSHA256':item['sha256'],
                'actualArchiveConsumer':True,'bundledInterpretersRelocated':True,'selectionUnchanged':True,
                'actualOfflineQtHealth':True,'immutableTarget':True,'liveProviderExercised':False,
                'actualPortalDBusFixture':True,'compositorPermissionExercised':False,
                'actualBundledDictationMaintenance':True,'microphoneCapture':False,'modelDownload':False,
                'installationExercised':False,'automaticInstallQualified':False}
        finally:os.environ.clear();os.environ.update(environment)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=prove(args.directory.resolve());args.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
