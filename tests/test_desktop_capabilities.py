# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Session/backend gating and restricted session-manager environment discovery."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services/desktop'))
spec=importlib.util.spec_from_file_location('desktop_discovery',ROOT/'services/desktop/capabilities.py')
cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)
from session_environment import graphical_environment
READY={cap.RD:{'version':2,'AvailableDeviceTypes':7},cap.SC:{'version':5,'AvailableSourceTypes':3}}
KDE={'XDG_SESSION_TYPE':'wayland','XDG_CURRENT_DESKTOP':'KDE','DISPLAY':':99'}
class DesktopCapabilityTests(unittest.TestCase):
    def test_gnome_x11_headless_and_substring_never_claim_kde(self):
        for env in ({},{**KDE,'XDG_CURRENT_DESKTOP':'GNOME'}, {**KDE,'XDG_SESSION_TYPE':'x11'}, {**KDE,'XDG_CURRENT_DESKTOP':'NOTKDE'}):
            with self.subTest(env=env):
                result=cap.assess(env,True,READY,True)
                self.assertFalse(result['available']);self.assertIsNone(result['backend'])
                self.assertEqual(result['reason'],'unsupported-session')
    def test_ready_kde_is_not_a_permission_or_functional_claim(self):
        result=cap.assess({**KDE,'XDG_CURRENT_DESKTOP':'plasma:KDE'},True,READY,True)
        self.assertTrue(result['available']);self.assertFalse(result['functionalTested'])
        self.assertEqual(result['permission'],'not-requested')
    def test_required_interpreter_stop_bus_and_observer_fail_closed(self):
        for env,deps,interfaces,kwin,reason in [({**KDE,'DISPLAY':''},True,READY,True,'stop-display-unavailable'),(KDE,False,READY,True,'dependencies-missing'),(KDE,True,None,True,'session-interfaces-unavailable'),(KDE,True,READY,False,'window-observer-unavailable')]:
            self.assertEqual(cap.assess(env,deps,interfaces,kwin)['reason'],reason)
        for value,expected in [('KWin version: 6.3.6',True),('KWin version: 6.6.2',True),('KWin version: 5.27.12',False),('KWin version: 6.2.5',False),('KWin version: 7.0.0',False),('unknown',False)]:
            self.assertEqual(cap.supported_kwin_version(value),expected)
    def test_monitor_keyboard_pointer_and_interface_versions_are_required(self):
        for interface,key,value in [(cap.RD,'AvailableDeviceTypes',1),(cap.RD,'AvailableDeviceTypes',2),(cap.RD,'version',0),(cap.SC,'AvailableSourceTypes',2),(cap.SC,'version',0)]:
            observed={name:dict(values) for name,values in READY.items()};observed[interface][key]=value
            self.assertEqual(cap.assess(KDE,True,observed,True)['reason'],'portal-capabilities-incomplete')
    def test_session_manager_only_overlays_graphical_allowlist(self):
        env=graphical_environment({'PRIVATE_TOKEN':'caller','DISPLAY':':0'},lambda:'DISPLAY=:99\nXDG_CURRENT_DESKTOP=KDE\nPRIVATE_TOKEN=manager-secret\nPATH=/hostile\nNO_SEPARATOR\n')
        self.assertEqual(env['DISPLAY'],':99');self.assertEqual(env['PRIVATE_TOKEN'],'caller');self.assertNotIn('PATH',env)
    def test_absent_user_manager_preserves_environment(self):
        def missing():raise subprocess.TimeoutExpired('systemctl',1)
        self.assertEqual(graphical_environment(KDE,missing),KDE)
    def test_unsupported_session_never_queries_bus_or_runtime_dependencies(self):
        with patch.object(cap,'graphical_environment',return_value={'XDG_CURRENT_DESKTOP':'GNOME','XDG_SESSION_TYPE':'wayland'}),patch.object(cap,'dependencies_available') as deps,patch.object(cap,'interfaces_available') as bus,patch.dict(cap.os.environ,{},clear=True):
            self.assertEqual(cap.report()['reason'],'unsupported-session')
        deps.assert_not_called();bus.assert_not_called()
if __name__=='__main__':unittest.main()
