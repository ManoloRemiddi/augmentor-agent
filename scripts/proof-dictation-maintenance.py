#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Handy/broker maintenance without microphone capture or model downloads."""
import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('dictation_maintenance_proof',ROOT/'services/dictation/server.py')
broker=importlib.util.module_from_spec(spec);spec.loader.exec_module(broker)


@contextmanager
def private_directory():
    directory=tempfile.TemporaryDirectory(prefix='ag-handy-maintenance-')
    try:yield Path(directory.name)
    finally:
        deadline=time.monotonic()+30
        while True:
            try:directory.cleanup();break
            except OSError:
                if os.name!='nt' or time.monotonic()>=deadline:raise
                time.sleep(.1)


def prove(runtime):
    with private_directory() as base:
        copy=base/'runtime';shutil.copytree(runtime,copy)
        binary=copy/'bin'/('handy.exe' if os.name=='nt' else 'handy')
        if sys.platform=='darwin' and (copy/'Augmentor Dictation.app/Contents/MacOS/handy').is_file():
            binary=copy/'Augmentor Dictation.app/Contents/MacOS/handy'
        (binary.parent/'portable').write_text('Handy Portable Mode\n')
        environment=os.environ.copy()
        backend=None
        try:
            for key,name in (('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state'),
                    ('XDG_CACHE_HOME','cache'),('XDG_RUNTIME_DIR','run'),('AUGMENTOR_DICTATION_STATE','dictation')):
                path=base/name;path.mkdir(mode=0o700);os.environ[key]=str(path)
            os.environ.update(WEBKIT_DISABLE_DMABUF_RENDERER='1',WEBKIT_DISABLE_COMPOSITING_MODE='1')
            if sys.platform=='linux':
                os.environ.update(GDK_BACKEND='x11',XDG_SESSION_TYPE='x11',LIBGL_ALWAYS_SOFTWARE='1',NO_AT_BRIDGE='1')
                os.environ.pop('WAYLAND_DISPLAY',None)
            backend=broker.Backend(base/'dictation');backend.binary=lambda:binary
            backend.start();child=backend.child
            original=backend.call('status',{})
            assert original['enabled'] is False and original['tray'] is False
            other={'token':'b'*32};token={'token':'a'*48}
            # A native owner unknown to the broker must also prevent preparation.
            backend.call('conversation.acquire',other)
            try:backend.request('host.maintenance.prepare',token)
            except RuntimeError:pass
            else:raise AssertionError('Maintenance adopted an occupied native microphone.')
            try:backend.call('conversation.acquire',{'token':'c'*32})
            except RuntimeError:pass
            else:raise AssertionError('Busy preparation released another native owner.')
            backend.call('conversation.release',other)
            assert backend.request('host.maintenance.prepare',token)['phase']=='prepared'
            try:backend.request('enable',{'enabled':True})
            except ValueError:pass
            else:raise AssertionError('Prepared broker admitted new capture.')
            try:backend.call('conversation.acquire',other)
            except RuntimeError:pass
            else:raise AssertionError('Native microphone escaped its update reservation.')
            assert backend.request('host.maintenance.cancel',token)['phase']=='ready'
            backend.call('conversation.acquire',other);backend.call('conversation.release',other)
            after=backend.call('status',{})
            assert after['enabled']==original['enabled'] and after['settings']==original['settings']
            assert backend.request('host.maintenance.prepare',token)['phase']=='prepared'
            assert backend.request('host.maintenance.commit',token)['phase']=='closing'
            backend.normal_stop();assert child.returncode==0 and backend.child is None
            return {'schema':'augmentor-dictation-maintenance-proof/1','actualHandy':True,
                'nativeOwnerPreserved':True,'nativeAtomicReservation':True,'brokerAdmissionFenced':True,
                'cancellationRestoredAdmission':True,'settingsPreserved':True,'ordinaryChildExit':True,
                'microphoneCapture':False,'modelDownload':False,'automaticInstallQualified':False}
        finally:
            if backend is not None and backend.child is not None:backend.stop()
            os.environ.clear();os.environ.update(environment)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,default=ROOT/'components/handy/runtime')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args();report=prove(args.runtime.resolve())
    if args.out is not None:
        with args.out.open('x',encoding='utf-8') as output:json.dump(report,output);output.write('\n')
        args.out.chmod(0o600)
    print(json.dumps(report))
