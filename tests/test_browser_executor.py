# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual authenticated local transport with an authored extension peer."""
import importlib.util
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('browser_executor',ROOT/'services/browser/executor.py')
executor=importlib.util.module_from_spec(spec);spec.loader.exec_module(executor)

class BrowserExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ab-');self.addCleanup(self.temp.cleanup)
        # Let the platform adapter create an owner-private child. Windows
        # tempfile's inherited owner can be Administrators in an SSH session.
        self.env=patch.dict(os.environ,{'AUGMENTOR_BROWSER_EXECUTOR_DIR':str(Path(self.temp.name)/'executors')});self.env.start();self.addCleanup(self.env.stop)
        self.children=[];self.requests=[]
        self.addCleanup(self.close)
    def close(self):
        for child in self.children:
            child.stdin.close()
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=3)
            child.stdout.close();child.stderr.close()
    def peer(self,label):
        child=subprocess.Popen([sys.executable,'-Xutf8','-B',str(ROOT/'services/browser/executor.py'),'serve'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        self.children.append(child);ready=json.loads(child.stdout.readline());self.assertEqual(ready['type'],'ready')
        def respond():
            for line in child.stdout:
                value=json.loads(line)
                if value.get('type')!='request':continue
                self.requests.append(value)
                result={'ok':True,'tabs':[{'id':7,'title':label,'url':'https://fixture.test/'}]} if value['params']['action']=='tabs_list' else {'ok':True,'label':label,'action':value['params']['action']}
                child.stdin.write(json.dumps({'id':value['id'],'result':result})+'\n');child.stdin.flush()
        threading.Thread(target=respond,daemon=True).start()
        return ready['id']
    def request(self,params):return executor.request({'owner':'pi:fixture','params':params,'expiresAt':time.time()*1000+5000})
    def test_tabs_identify_executors_and_mutations_require_unambiguous_identity(self):
        first=self.peer('first');second=self.peer('second')
        tabs=self.request({'action':'tabs_list'})['tabs'];self.assertEqual({r['executorId'] for r in tabs},{first,second})
        with self.assertRaisesRegex(RuntimeError,'Choose executorId'):self.request({'action':'pointer','selector':'#fixture'})
        result=self.request({'action':'pointer','selector':'#fixture','executorId':second});self.assertEqual(result['label'],'second')
        self.assertEqual(len([r for r in self.requests if r['params']['action']=='pointer']),1)
    def test_expired_request_never_reaches_extension_and_shutdown_removes_registration(self):
        identity=self.peer('fixture');row=next(r for r in executor.records() if r['id']==identity)
        with self.assertRaisesRegex(RuntimeError,'expired'):executor.call(row,{'owner':'pi:fixture','params':{'action':'insert_text','text':'never'},'expiresAt':time.time()*1000-1})
        self.assertEqual(self.requests,[])
    def test_dead_registry_is_ignored_and_stop_reaches_every_live_executor(self):
        first=self.peer('first');second=self.peer('second')
        root=executor.directory();path=root/('b'*32+'.json');path.write_text(json.dumps({'id':'b'*32,'endpoint':str(path.with_suffix('.sock')),'pid':99999999}));path.chmod(0o600)
        self.assertEqual(len(executor.records()),2)
        self.assertTrue(self.request({'action':'stop'})['stopped'])
        self.assertEqual(len([r for r in self.requests if r['params']['action']=='stop']),2)
    def test_oversized_reply_fails_one_request_and_keeps_executor_alive(self):
        child=subprocess.Popen([sys.executable,'-Xutf8','-B',str(ROOT/'services/browser/executor.py'),'serve'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1);self.children.append(child)
        ready=json.loads(child.stdout.readline());row=next(r for r in executor.records() if r['id']==ready['id']);result={}
        def query():
            try:executor.call(row,{'owner':'pi:fixture','params':{'action':'snapshot'},'expiresAt':time.time()*1000+5000})
            except RuntimeError as error:result['error']=str(error)
        thread=threading.Thread(target=query);thread.start();request=json.loads(child.stdout.readline())
        child.stdin.write(json.dumps({'id':request['id'],'result':'x'*(executor.LIMIT+1)})+'\n');child.stdin.flush();thread.join(5)
        self.assertIn('transport bound',result['error']);self.assertIsNone(child.poll());self.assertTrue(executor.records())
    def test_symlinked_graphical_runtime_resolves_before_default_path_validation(self):
        if sys.platform=='win32':self.skipTest('POSIX symlink fixture')
        parent=Path(self.temp.name);real=parent/'real';real.mkdir(mode=0o700);link=parent/'link';link.symlink_to(real,target_is_directory=True)
        with patch.dict(os.environ,{'XDG_RUNTIME_DIR':str(link)},clear=False):
            saved=os.environ.pop('AUGMENTOR_BROWSER_EXECUTOR_DIR')
            try:
                alias=executor.directory();os.environ['XDG_RUNTIME_DIR']=str(real);self.assertEqual(alias,executor.directory());self.assertEqual(alias,alias.resolve());self.addCleanup(lambda:alias.rmdir())
            finally:os.environ['AUGMENTOR_BROWSER_EXECUTOR_DIR']=saved
    def test_public_or_linked_registry_records_are_not_consumed(self):
        root=executor.directory();path=root/('a'*32+'.json');path.write_text(json.dumps({'id':'a'*32,'endpoint':str(path.with_suffix('.sock'))}));path.chmod(0o644)
        if sys.platform!='win32':self.assertEqual(executor.records(),[])

if __name__=='__main__':unittest.main()
