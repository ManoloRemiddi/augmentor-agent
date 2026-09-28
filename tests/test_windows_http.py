# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual Windows TCP peer ownership before any authenticated HTTP bytes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))


def server(root,port):
    from http.server import HTTPServer,BaseHTTPRequestHandler
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length',0)))
            (root/'received').write_text('received',encoding='utf-8')
            body=json.dumps({'ok':True,'pid':os.getpid()}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        do_GET=do_POST
    service=HTTPServer(('127.0.0.1',port),Handler)
    (root/'ready.json').write_text(json.dumps({'port':service.server_port}),encoding='utf-8')
    # A connected peer can close before sending bytes when identity is refused.
    while not (root/'release').exists():
        service.timeout=.1;service.handle_request()
    service.server_close()


@unittest.skipUnless(sys.platform=='win32','requires actual Windows TCP ownership')
class WindowsHttpTests(unittest.TestCase):
    def test_credentials_wait_for_verified_peer_and_replacement_is_not_adopted(self):
        from platform_adapters.windows_http import ObservedHttp
        children=[];clients=[]
        with tempfile.TemporaryDirectory(prefix='augmentor-observed-http-') as temporary:
            base=Path(temporary)
            def start(name,port=0):
                root=base/name;root.mkdir()
                child=subprocess.Popen([sys.executable,'-I','-Xutf8','-B',__file__,'--server',str(root),str(port)],
                    stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                children.append((child,root));deadline=time.monotonic()+10
                while True:
                    try:metadata=json.loads((root/'ready.json').read_text(encoding='utf-8'));break
                    except (FileNotFoundError,ValueError):
                        if child.poll() is not None or time.monotonic()>=deadline:self.fail('The disposable HTTP peer did not start.')
                        time.sleep(.02)
                return child,root,metadata['port']
            try:
                first,first_root,port=start('first')
                def refuse(pid):
                    self.assertEqual(pid,first.pid)
                    raise ValueError('Fixture ownership refused.')
                rejected=ObservedHttp(port,sys.executable,verify_process=refuse);clients.append(rejected)
                with self.assertRaisesRegex(ValueError,'ownership refused'):
                    rejected.request('/internal/maintenance',{'operation':'fixture'},{'x-fixture-token':'private-fixture'})
                self.assertFalse((first_root/'received').exists(),'A refused peer received HTTP credentials.')
                wrong=ObservedHttp(port,ROOT/'not-the-running-program.exe',verify_process=lambda pid:None);clients.append(wrong)
                with self.assertRaisesRegex(ValueError,'executable differs'):wrong.request('/health')
                self.assertFalse((first_root/'received').exists())
                observed=[]
                client=ObservedHttp(port,sys.executable,verify_process=observed.append);clients.append(client)
                self.assertEqual(client.request('/internal/maintenance',{'fixture':True})['pid'],first.pid)
                self.assertEqual(observed,[first.pid]);self.assertFalse(client.exited())
                (first_root/'release').write_text('release',encoding='utf-8')
                _out,errors=first.communicate(timeout=10);self.assertEqual(first.returncode,0,errors.decode())
                self.assertTrue(client.exited())
                second,second_root,_=start('replacement',port)
                with self.assertRaisesRegex(ValueError,'exited or changed'):
                    client.request('/internal/maintenance',{'fixture':True},{'x-fixture-token':'private-fixture'})
                self.assertFalse((second_root/'received').exists(),'The replacement received an old observation\'s request.')
            finally:
                for child,root in children:
                    (root/'release').write_text('release',encoding='utf-8')
                    try:child.communicate(timeout=10)
                    except subprocess.TimeoutExpired:child.kill();child.communicate(timeout=5)
                for client in clients:client.close()


if __name__=='__main__':
    if sys.argv[1:2]==['--server']:server(Path(sys.argv[2]),int(sys.argv[3]))
    else:unittest.main()
