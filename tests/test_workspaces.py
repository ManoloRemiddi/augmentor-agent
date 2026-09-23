# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
import sys
from pathlib import Path
from unittest.mock import patch
from PySide6.QtDBus import QDBusMessage
from augmentor_linux.workspaces import run_script,release_scripts

@unittest.skipUnless(sys.platform == 'linux', 'KWin integration is Linux-specific')
class WorkspaceTests(unittest.TestCase):
    def test_occupied_script_id_is_never_executed(self):
        ran=[];unloaded=[];ids=iter([4,5])
        class Reply:
            def __init__(self,value):self.value=value
            def arguments(self):return [self.value]
            def type(self):return QDBusMessage.MessageType.ReplyMessage
        class Interface:
            def __init__(self,service,path,interface,bus):self.path=path
            def isValid(self):return True
            def call(self,method,*args):
                if method=='Introspect':return Reply('<node><node name="Script4"/></node>')
                if method=='loadScript':return Reply(next(ids))
                if method=='run':ran.append(self.path)
                if method=='unloadScript':unloaded.append(args[0])
                return Reply(True)
        with patch('augmentor_linux.workspaces.QDBusInterface',Interface):
            lease=run_script('/* requested action */')
            try:
                self.assertEqual(ran,['/Scripting/Script5'])
                self.assertIn('Inert reservation',Path(lease[0][1]).read_text())
                self.assertEqual(Path(lease[1][1]).read_text(),'/* requested action */')
            finally:release_scripts(lease)
        self.assertEqual(unloaded,[row[0] for row in reversed(lease)])
