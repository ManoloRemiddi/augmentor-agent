# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real retained-runtime exec and inherited flock, with public development refusal."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.macos_payload import snapshot
from platform_adapters.private_files import atomic_json,read_json
from updates.linux_managed import load_deployment
from updates.linux_bootstrap import locations


@unittest.skipUnless(sys.platform=='linux','Actual copied ELF interpreter, exec and inherited Unix lock.')
class LinuxHandoffTests(unittest.TestCase):
    def test_actual_retained_observer_exec_refuses_unqualified_source_before_network_or_apply(self):
        with tempfile.TemporaryDirectory(prefix='augmentor-linux-exec-proof-') as temporary:
            base=Path(temporary);data=base/'data/augmentor';runtime=base/'runtime';state=base/'state'
            for path in (data,runtime,state):path.mkdir(parents=True,mode=0o700)
            candidate=base/'candidate';candidate.mkdir(mode=0o700)
            for part in ('services','scripts'):
                shutil.copytree(ROOT/part,candidate/part,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            (candidate/'apps/native/augmentor_linux').mkdir(parents=True)
            (candidate/'apps/native/augmentor_linux/window.py').write_text('--ensure-running')
            (candidate/'python/bin').mkdir(parents=True);(candidate/'node/bin').mkdir(parents=True)
            shutil.copy2(Path(sys.executable).resolve(),candidate/'python/bin/python3')
            (candidate/'node/bin/node').write_text('Inert Node; no repository request may execute.')
            (candidate/'node/bin/node').chmod(0o755)
            (candidate/'release').mkdir();product=json.loads((ROOT/'release/product.json').read_text())
            (candidate/'release/product.json').write_text(json.dumps(product))
            (candidate/'release.json').write_text(json.dumps({**product,'sourceCommit':'c'*40,'target':'linux-x64',
                'component':'desktop','update':{'build':1,'automaticInstallQualified':False}}))
            tool=load_deployment(data);tool.check=Mock()
            atomic_json(data/'desktop.json',{'root':str(candidate),'python':str(candidate/'python/bin/python3'),
                'node':str(candidate/'node/bin/node')})
            source=tool.stage(candidate,'inert-exec-source');tool.activate(source)
            (data/'updates').mkdir(mode=0o700)
            transactions=state/'augmentor/updates';transactions.mkdir(parents=True,mode=0o700)
            attempt='d'*48
            observer=data/'updates/observers'/('linux-'+attempt)/'Observer'
            observer.parent.mkdir(parents=True,mode=0o700)
            shutil.copytree(source,observer,symlinks=True)
            payload=snapshot(source)
            self.assertEqual(snapshot(observer),payload)
            digest=hashlib.sha256((source/'release.json').read_bytes()).hexdigest()
            environment={key:value for key,value in os.environ.items() if not key.startswith(('XDG_','AUGMENTOR_','PYTHON','NODE_'))}
            environment.update(XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(state),XDG_RUNTIME_DIR=str(runtime))
            # This actual process creates the private kernel lock and execs the
            # copied ELF runtime; no saved PID or mocked executable is adopted.
            helper='''import fcntl,os,sys
fd=os.open(sys.argv[1],os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600)
fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
os.set_inheritable(fd,True)
args=sys.argv[2:]+['--bootstrap-fd',str(fd)]
os.execv(args[0],args)
'''
            result=subprocess.run([sys.executable,'-I','-B','-c',helper,str(transactions/'bootstrap.lock'),
                str(observer/'python/bin/python3'),'-I','-B',str(observer/'scripts/linux-update-observer.py'),
                '--attempt',attempt,'--source-root',str(source),'--source-release-sha256',digest,
                '--source-payload-sha256',payload['sha256']],env=environment,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=30)
            self.assertNotEqual(result.returncode,0)
            report=read_json(transactions/('attempt-'+attempt+'.json'))
            self.assertEqual(report['outcome'],'deferred')
            self.assertEqual(report['error'],'This source build has not qualified automatic managed installation.')
            self.assertIsNone(report['transactionId'])
            self.assertFalse((transactions/'active.json').exists())
            self.assertEqual(snapshot(source),payload);self.assertEqual(snapshot(observer),payload)
            self.assertEqual(read_json(data/'desktop.json')['root'],str(source))

    def test_custom_selected_source_or_external_interpreter_is_not_adopted(self):
        with tempfile.TemporaryDirectory(prefix='augmentor-linux-location-proof-') as temporary:
            base=Path(temporary);data=base/'data/augmentor';runtime=base/'runtime'
            data.mkdir(parents=True,mode=0o700);runtime.mkdir(mode=0o700)
            source=data/'releases/source';source.mkdir(parents=True,mode=0o700)
            config={'root':str(source),'python':str(source/'python/bin/python3'),'node':str(source/'node/bin/node')}
            atomic_json(data/'desktop.json',config)
            with patch.dict(os.environ,{'XDG_DATA_HOME':str(base/'data'),'XDG_RUNTIME_DIR':str(runtime)}):
                self.assertEqual(locations(source)[0],data)
                atomic_json(data/'desktop.json',{**config,'python':'/usr/bin/python3'})
                with self.assertRaisesRegex(ValueError,'retained interpreters'):locations(source)
                with self.assertRaisesRegex(ValueError,'canonical private'):locations(base/'other-source')
