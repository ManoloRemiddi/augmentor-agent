# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Synthetic request/framing checks and actual Windows owned-command proofs."""
import base64
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

ROOT = Path(os.environ.get('AUGMENTOR_PI_TEST_ROOT', Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(ROOT/'services'))
from platform_adapters.shell_job import command_request, cmd_invocation, VERSION
HELPER = ROOT/'services/platform_adapters/shell_job.py'


def frame(value):
    return (json.dumps(value, ensure_ascii=False)+'\n').encode('utf-8')


class ShellRequestTests(unittest.TestCase):
    def test_cmd_limit_counts_the_complete_utf16_invocation_before_dispatch(self):
        with patch.dict(os.environ, {'SystemRoot': 'C:\\Windows'}):
            command='echo "literal & |"'
            executable,invocation=cmd_invocation(command)
            self.assertTrue(executable.endswith('cmd.exe'))
            self.assertTrue(invocation.endswith('/d /s /c "'+command+'"'))
            with self.assertRaisesRegex(ValueError,'CMD limit'):cmd_invocation('x'*8191)
            with self.assertRaisesRegex(ValueError,'CMD limit'):cmd_invocation('🙂'*4096)
    def test_command_text_is_preserved_without_shell_or_argv_transformation(self):
        command = '"C:\\space café\\node.exe" "literal & |" && echo done'
        self.assertEqual(command_request(frame({'version': VERSION, 'command': command})), command)

    def test_missing_extra_invalid_or_unbounded_request_is_refused(self):
        for value in [[], {}, {'version': VERSION, 'command': 'echo safe', 'type': 'cancel'},
                      {'version': 'foreign', 'command': 'echo safe'}, {'version': VERSION, 'command': ' '},
                      {'version': VERSION, 'command': 'echo\0unsafe'}, {'version': VERSION, 'command': 42},
                      {'version': VERSION, 'command': 'é'*8193}]:
            with self.subTest(value=str(value)[:90]), self.assertRaises(ValueError):command_request(frame(value))
        for raw in [b'', b'{}', b'x'*65537+b'\n', b'\xff\n']:
            with self.assertRaises(ValueError):command_request(raw)
        self.assertEqual(len(command_request(frame({'version': VERSION, 'command': 'é'*8192}))), 8192)


class Producer:
    def __init__(self, command, cwd, env=None, arguments=None):
        self.process = subprocess.Popen([sys.executable, '-I', '-Xutf8', '-B', *(arguments or [str(HELPER)])], cwd=cwd,
            env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW)
        self.events = [];self.incoming = queue.Queue()
        def read():
            try:
                for raw in self.process.stdout:self.incoming.put(json.loads(raw))
            finally:self.incoming.put(None)
        self.reader = threading.Thread(target=read, daemon=True);self.reader.start()
        self.process.stdin.write(frame({'version': VERSION, 'command': command}));self.process.stdin.flush()
    def until(self, predicate, timeout=10):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:event = self.incoming.get(timeout=min(.1, max(.001, deadline-time.monotonic())))
            except queue.Empty:continue
            if event is None:raise AssertionError('Private producer closed without the requested receipt.')
            self.events.append(event)
            if predicate(event):return event
        raise AssertionError('Private producer receipt timeout.')
    def settled(self):
        result = self.until(lambda event:event['type']=='settled')
        if not self.process.stdin.closed:self.process.stdin.close()
        self.process.wait(timeout=5);self.reader.join(timeout=5)
        assert self.process.returncode==0
        return result
    def close(self):
        if not self.process.stdin.closed:self.process.stdin.close()
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
        self.reader.join(timeout=5)
        self.process.stdout.close();self.process.stderr.close()


@unittest.skipUnless(sys.platform=='win32', 'requires the actual Windows Job kernel')
class WindowsShellJobTests(unittest.TestCase):
    def quote(self, argv):return subprocess.list2cmdline(list(map(str, argv)))
    def wait_file(self, path):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            try:return json.loads(path.read_text(encoding='utf-8'))
            except (FileNotFoundError, json.JSONDecodeError):time.sleep(.02)
        self.fail('Synthetic owned workload did not record identities.')
    def handles(self, pids):
        import win32api, win32con
        result=[]
        try:
            for pid in pids:result.append(win32api.OpenProcess(win32con.SYNCHRONIZE, False, pid))
        except BaseException:
            for handle in result:handle.Close()
            raise
        return result
    def assert_exit(self, handles):
        import win32event
        for handle in handles:self.assertEqual(win32event.WaitForSingleObject(handle, 5000), win32event.WAIT_OBJECT_0)
    def scripts(self, root, leader_exits=False):
        descendant=root/'detached child.py';target=root/'command leader.py';record=root/'owned-pids.json';release=root/'release'
        descendant.write_text('import sys,time\nfrom pathlib import Path\nwhile not Path(sys.argv[1]).exists():time.sleep(.02)\n', encoding='utf-8')
        target.write_text('''import json,os,subprocess,sys,time
from pathlib import Path
child=subprocess.Popen([sys.executable,sys.argv[1],sys.argv[3]],creationflags=subprocess.DETACHED_PROCESS,
 stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
Path(sys.argv[2]).write_text(json.dumps([os.getpid(),child.pid]))
print('owned-command-started',flush=True)
if sys.argv[4]=='hold':time.sleep(300)
else:
 while not Path(sys.argv[5]).exists():time.sleep(.02)
''', encoding='utf-8')
        return self.quote([sys.executable, '-Xutf8', target, descendant, record, release, 'exit' if leader_exits else 'hold', root/'leader-release']), record, release
    def test_fast_output_unicode_paths_quoting_binary_frames_and_nonzero_receipt(self):
        with tempfile.TemporaryDirectory(prefix='augmentor shell café ') as temporary:
            root=Path(temporary);target=root/'quoted café command.py';payload=bytes(range(256))*400
            target.write_text('''import json,os,sys
sys.stdout.buffer.write(bytes(range(256))*400)
sys.stdout.buffer.write(json.dumps({'version':'augmentor-shell-job/1','type':'settled','state':'completed','drained':True,'exitCode':0}).encode())
sys.stdout.buffer.flush()
sys.stderr.buffer.write(json.dumps([sys.argv[1:],os.environ['AUGMENTOR_SHELL_FIXTURE']],ensure_ascii=False).encode('utf-8'))
sys.stderr.buffer.flush()
sys.exit(7)
''', encoding='utf-8')
            producer=Producer(self.quote([sys.executable, '-Xutf8', target, 'literal & |', 'space café', 'trailing\\']), root,
                {**os.environ, 'AUGMENTOR_SHELL_FIXTURE':'café 秘密'})
            try:
                settled=producer.settled();self.assertEqual(settled['state'],'failed');self.assertTrue(settled['drained']);self.assertEqual(settled['exitCode'],7)
                self.assertEqual(producer.events[0]['type'],'ready')
                output=b''.join(base64.b64decode(event['data']) for event in producer.events if event['type']=='output' and event['channel']=='stdout')
                errors=b''.join(base64.b64decode(event['data']) for event in producer.events if event['type']=='output' and event['channel']=='stderr')
                self.assertEqual(output[:len(payload)],payload);self.assertEqual(json.loads(output[len(payload):])['state'],'completed')
                self.assertEqual(json.loads(errors.decode('utf-8')),[['literal & |','space café','trailing\\'],'café 秘密'])
            finally:producer.close()
    def test_stop_eof_and_supervisor_crash_end_owned_leader_and_detached_descendant(self):
        for operation in ['cancel','eof','crash']:
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);command,record,_release=self.scripts(root);producer=Producer(command,root);handles=[]
                try:
                    producer.until(lambda event:event['type']=='output');handles=self.handles(self.wait_file(record))
                    if operation=='cancel':producer.process.stdin.write(frame({'version':VERSION,'type':'cancel'}));producer.process.stdin.flush()
                    elif operation=='eof':producer.process.stdin.close()
                    else:producer.process.kill()
                    if operation!='crash':self.assertEqual(producer.settled()['state'],'cancelled')
                    else:producer.process.wait(timeout=5)
                    self.assert_exit(handles)
                finally:
                    producer.close()
                    for handle in handles:handle.Close()
    def test_exited_leader_does_not_settle_or_kill_a_surviving_detached_descendant(self):
        import win32event
        for cancel in [False,True]:
            with self.subTest(cancel=cancel), tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);command,record,release=self.scripts(root,leader_exits=True);producer=Producer(command,root);handles=[]
                try:
                    producer.until(lambda event:event['type']=='output');handles=self.handles(self.wait_file(record))
                    (root/'leader-release').write_text('Synthetic leader may exit',encoding='utf-8')
                    self.assertEqual(win32event.WaitForSingleObject(handles[0],5000),win32event.WAIT_OBJECT_0)
                    self.assertEqual(win32event.WaitForSingleObject(handles[1],200),win32event.WAIT_TIMEOUT)
                    self.assertIsNone(producer.process.poll())
                    self.assertFalse(any(event['type']=='settled' for event in producer.events))
                    if cancel:producer.process.stdin.write(frame({'version':VERSION,'type':'cancel'}));producer.process.stdin.flush()
                    else:release.write_text('Synthetic natural descendant exit',encoding='utf-8')
                    self.assertEqual(producer.settled()['state'],'cancelled' if cancel else 'completed');self.assert_exit(handles)
                finally:
                    producer.close()
                    for handle in handles:handle.Close()
    def test_invalid_command_never_launches_a_shell(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);target=root/'must-not-run.py';marker=root/'forbidden'
            target.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("forbidden")\n',encoding='utf-8')
            producer=Producer(self.quote([sys.executable,target])+'\0',root)
            try:self.assertEqual(producer.settled()['state'],'failed');self.assertFalse(marker.exists())
            finally:producer.close()
    def test_failed_job_bootstrap_has_no_direct_shell_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);target=root/'must-not-run.py';marker=root/'forbidden'
            target.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("forbidden")\n',encoding='utf-8')
            code='''import sys
sys.path.insert(0,sys.argv[1])
import win32job
from unittest.mock import patch
from platform_adapters.shell_job import supervisor
with patch.object(win32job,'QueryInformationJobObject',side_effect=RuntimeError('Synthetic unavailable containment')):
 raise SystemExit(supervisor())
'''
            producer=Producer(self.quote([sys.executable,target]),root,arguments=['-c',code,str(ROOT/'services')])
            try:
                settled=producer.settled();self.assertEqual(settled['state'],'failed');self.assertFalse(settled['drained']);self.assertEqual(len(producer.events),1);self.assertFalse(marker.exists())
            finally:producer.close()


if __name__=='__main__':unittest.main()
