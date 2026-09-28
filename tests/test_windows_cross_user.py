# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real other-user token denial on explicitly disposable hosted Windows VMs.

Never creates an account on a developer/customer machine through normal tests.
The temporary local account is removed in finally; no password is logged.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'services'))


@unittest.skipUnless(sys.platform == 'win32' and os.environ.get('AUGMENTOR_EPHEMERAL_WINDOWS_RUNNER') == '1',
                     'requires an explicitly disposable Windows account-security runner')
class OtherUserAccessTests(unittest.TestCase):
    def test_other_user_token_cannot_open_private_pipe_or_record(self):
        import pywintypes
        import win32con
        import win32file
        import win32net
        import win32netcon
        import win32security
        from platform_adapters.windows_identity import private_directory, private_file_descriptor, current_sid
        from platform_adapters.windows_pipe import PipeListener, pipe_name
        account = 'AugTest'+uuid.uuid4().hex[:12]
        password = uuid.uuid4().hex+'Aa!9'
        token = listener = None
        created = False
        try:
            win32net.NetUserAdd(None, 1, {'name': account, 'password': password,
                'priv': win32netcon.USER_PRIV_USER, 'home_dir': '', 'comment': 'Disposable Augmentor access-denial fixture',
                'flags': win32netcon.UF_SCRIPT | win32netcon.UF_NORMAL_ACCOUNT, 'script_path': ''})
            created = True
            token = win32security.LogonUser(account, '.', password,
                win32con.LOGON32_LOGON_NETWORK, win32con.LOGON32_PROVIDER_DEFAULT)
            other = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
            self.assertNotEqual(other, current_sid())
            with tempfile.TemporaryDirectory() as temporary:
                root = private_directory(Path(temporary)/'private')
                record = root/'record.json'
                with os.fdopen(private_file_descriptor(record, writable=True, exclusive=True), 'wb') as stream:
                    stream.write(b'{"fixture":true}')
                endpoint = root/'access.sock'; listener = PipeListener(endpoint)
                name = pipe_name(endpoint)
                try:
                    win32security.ImpersonateLoggedOnUser(token)
                    for path in (str(record), name):
                        with self.subTest(object='pipe' if path.startswith('\\\\.\\pipe') else 'record'):
                            try:
                                handle = win32file.CreateFile(path, win32con.GENERIC_READ,
                                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE, None,
                                    win32con.OPEN_EXISTING, 0, None)
                            except pywintypes.error as error:
                                self.assertEqual(error.winerror, 5, 'Access must be denied by the kernel.')
                            else:
                                handle.Close()
                                self.fail('Another Windows user opened a private Augmentor object.')
                finally:
                    win32security.RevertToSelf()
                    listener.close(); listener = None
        finally:
            if listener is not None: listener.close()
            if token is not None: token.Close()
            if created: win32net.NetUserDel(None, account)


if __name__ == '__main__': unittest.main()
