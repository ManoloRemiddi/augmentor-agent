# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""The real spawned service must not mutate a signed app, even outside its launcher."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'apps/native'))
from augmentor_linux import prompt_client


class PromptServiceStartupTests(unittest.TestCase):
    def test_spawn_disables_bytecode_even_when_environment_enables_it(self):
        with tempfile.TemporaryDirectory(prefix='ag-prompt-', dir='/tmp') as temporary:
            root=Path(temporary)
            state=root/'state';state.mkdir()
            service=root/'services/prompt-library/service.py'
            service.parent.mkdir(parents=True)
            (service.parent/'owned_helper.py').write_text('VALUE = 42\n')
            service.write_text('''
import json, os, socket, sys
from pathlib import Path
import owned_helper
server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
server.settimeout(5)
server.bind(str(Path(os.environ['AUGMENTOR_SHARED_STATE'])/'prompts.sock'))
server.listen(1)
with server:
    connection,_=server.accept()
    with connection:
        request=json.loads(connection.makefile('rb').readline())
        connection.sendall((json.dumps({'id':request['id'],'result':{
            'bytecodeDisabled':sys.dont_write_bytecode,'value':owned_helper.VALUE}})+'\\n').encode())
''')
            with (patch.object(prompt_client,'__file__',str(root/'apps/native/augmentor_linux/prompt_client.py')),
                  patch.dict(os.environ,{'AUGMENTOR_SHARED_STATE':str(state),'PYTHONDONTWRITEBYTECODE':'0'})):
                result=prompt_client.PromptClient().call('fixture.check')
            self.assertEqual(result,{'bytecodeDisabled':True,'value':42})
            self.assertEqual(list(root.rglob('*.pyc')),[])


if __name__=='__main__':
    unittest.main()
