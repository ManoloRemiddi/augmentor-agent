# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class DesktopStartupTests(unittest.TestCase):
    def test_all_entrypoints_select_same_deployment_and_keep_venv(self):
        installer=load('install-desktop-startup')
        with tempfile.TemporaryDirectory(prefix='desktop space ') as folder:
            home=Path(folder);root=home/'preview';native=root/'apps/native/augmentor_linux';native.mkdir(parents=True)
            (native/'window.py').write_text('--ensure-running')
            (root/'release').mkdir();(root/'release/product.json').write_text('{"version":"test"}')
            python=home/'venv/bin/python';python.parent.mkdir(parents=True);python.symlink_to('/usr/bin/python3')
            data=home/'data';config=home/'config';state=home/'state'
            (config/'augmentor').mkdir(parents=True)
            (config/'augmentor/harnesses.json').write_text(json.dumps({'dsh':{'endpoint':'http://127.0.0.1:3080','home':str(home/'.dsh')}}))
            with patch.dict(os.environ,{'XDG_DATA_HOME':str(data),'XDG_CONFIG_HOME':str(config),'XDG_STATE_HOME':str(state)}),patch.object(Path,'home',return_value=home),patch.object(installer.subprocess,'run',return_value=Mock(returncode=0)):
                manifest=installer.install(root,python,Path('/usr/bin/python3'),'dsh-web.service')
            self.assertEqual(manifest['python'],str(python))
            for path in (data/'applications/com.augmentor.Agent.desktop',data/'applications/com.augmentor.Agent.secondary.desktop',config/'autostart/com.augmentor.Agent.desktop'):
                self.assertIn(str(home/'.local/bin/augmentor-agent'),path.read_text())
                self.assertNotIn('/usr/bin/augmentor-agent',path.read_text())
            self.assertIn('Restart=on-failure',(config/'systemd/user/augmentor-desktop.service').read_text())

    def test_login_only_starts_supervisor_and_does_not_toggle_existing_window(self):
        launch=load('desktop-launch')
        with patch.object(launch,'start_service') as start,patch.object(launch.os,'execve') as execute:
            self.assertEqual(launch.main(['--autostart']),0)
        start.assert_called_once();execute.assert_not_called()

    def test_pending_update_does_not_disable_recovery_of_running_window(self):
        launch=load('desktop-launch')
        old={'buildRoot':'/previous','online':True,'accepted':True}
        with patch.object(launch,'start_service'),patch.object(launch,'configuration',return_value={'root':'/new'}),patch.object(launch,'exchange',side_effect=[old,old,old]) as exchange:
            launch.recover()
        self.assertEqual([call.args[0] for call in exchange.call_args_list],['maintenance.status','maintenance.recover','maintenance.status'])

    def test_service_uses_selected_build_and_non_toggling_activation(self):
        launch=load('desktop-launch')
        config={'root':str(ROOT),'python':'/venv/bin/python','node':'/node','dshService':'dsh-web.service'}
        with patch.object(launch,'configuration',return_value=config),patch.object(launch,'exchange',return_value=None),patch.object(launch.os,'execve') as execute:
            launch.main(['--service-run'])
        args=execute.call_args.args
        self.assertEqual(args[0],'/venv/bin/python');self.assertIn('--ensure-running',args[1])
        self.assertEqual(args[2]['AUGMENTOR_DSH_SERVICE'],'dsh-web.service')
        self.assertEqual(args[2]['PYTHONPATH'],str(ROOT/'apps/native'))

    def test_session_restore_cannot_keep_an_idle_old_build_in_charge(self):
        launch=load('desktop-launch')
        config={'root':str(ROOT),'python':'/venv/bin/python','node':'/node'}
        # First observation is busy: no close. The next is idle: guarded close.
        with patch.object(launch,'configuration',return_value=config),patch.object(launch,'exchange',side_effect=[{'accepted':False},{'accepted':True},{'accepted':True},None]) as exchange,patch.object(launch.time,'sleep'),patch.object(launch.os,'execve') as execute:
            launch.main(['--service-run'])
        self.assertEqual([c.args[0] for c in exchange.call_args_list],['maintenance.status','maintenance.status','maintenance.close','maintenance.status'])
        execute.assert_called_once()
