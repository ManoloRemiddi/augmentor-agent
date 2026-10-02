# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Consent identity, late grant and resource cleanup; synthetic bus, no input."""
import importlib.util
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import Mock,patch
try:from gi.repository import Gio,GLib
except ImportError:Gio=GLib=None

spec=importlib.util.spec_from_file_location('desktop_consent',Path(__file__).resolve().parents[1]/'services/desktop/portal_session.py')
module=importlib.util.module_from_spec(spec)
if GLib is not None:spec.loader.exec_module(module)


def fixture():
    value=module.ConsentSession.__new__(module.ConsentSession)
    value.thread=threading.get_ident();value.context=GLib.MainContext.new();value.cancel=threading.Event();value.mutex=threading.Lock()
    value.generation=0;value.rpc_cancel=Gio.Cancellable();value.session=None;value.request_path=None;value.fd=None
    value.owners={name:':1.7' for name in module.OWNERS};value.subscriptions=[];value.closed=False;value.stream=None;value.on_stopped=None;value.on_request=None;value.request_timeout=80
    value.bus=Mock();value.bus.get_unique_name.return_value=':1.42';value.owner=Mock(return_value=':1.7')
    return value


@unittest.skipIf(GLib is None,'Linux GLib runtime required.')
class DesktopConsentTests(unittest.TestCase):
    def test_stop_is_immediate_cross_thread_and_notification_once(self):
        value=fixture();value.on_stopped=Mock();thread=threading.Thread(target=value.request_stop);thread.start();thread.join(1)
        self.assertTrue(value.cancel.is_set());self.assertTrue(value.rpc_cancel.is_cancelled());self.assertEqual(value.generation,1)
        value.request_stop();value.on_stopped.assert_called_once()
        with self.assertRaisesRegex(RuntimeError,'stopped'):value.verify(0)
        value.owner.assert_not_called()

    def test_thread_affinity_and_changed_owner_refuse_before_portal_rpc(self):
        value=fixture();value.thread=-1
        with self.assertRaisesRegex(RuntimeError,'owning worker'):value.call(module.RD,'Start',None,(),0)
        value.bus.call_sync.assert_not_called()
        value.thread=threading.get_ident();value.owner.return_value=':1.99'
        with self.assertRaisesRegex(RuntimeError,'service changed'):value.call(module.RD,'Start',None,(),0)
        value.bus.call_sync.assert_not_called();self.assertTrue(value.cancel.is_set())

    def test_wrong_request_reply_closes_only_precomputed_identity(self):
        value=fixture();value.call=Mock(return_value=('/untrusted/path',));value.close_path=Mock()
        with self.assertRaisesRegex(RuntimeError,'request identity'):
            value.request(module.RD,'CreateSession','(a{sv})',({},),0)
        path=value.close_path.call_args.args[0]
        self.assertTrue(path.startswith('/org/freedesktop/portal/desktop/request/1_42/request'))
        self.assertNotEqual(path,'/untrusted/path');value.bus.signal_unsubscribe.assert_called_once();self.assertIsNone(value.request_path)

    def test_late_session_grant_is_closed_even_before_handle_is_consumed(self):
        value=fixture();value.negotiate=Mock(return_value={});value.close_path=Mock()
        def grant(*_):
            expected=value.session;self.assertTrue(expected.startswith('/org/freedesktop/portal/desktop/session/1_42/session'))
            value.request_stop();return {'session_handle':expected}
        value.request=Mock(side_effect=grant)
        with self.assertRaisesRegex(RuntimeError,'stopped'):value.connect()
        self.assertIsNone(value.session)
        self.assertTrue(any(call.args[0] and '/session/1_42/' in call.args[0] for call in value.close_path.call_args_list))

    def test_foreign_session_reply_never_closes_foreign_path(self):
        value=fixture();value.negotiate=Mock(return_value={});value.request=Mock(return_value={'session_handle':'/foreign/session'});value.close_path=Mock()
        with self.assertRaisesRegex(RuntimeError,'session identity'):value.connect()
        self.assertNotIn('/foreign/session',[call.args[0] for call in value.close_path.call_args_list]);self.assertIsNone(value.session)

    def test_fd_is_owned_before_late_cancellation_and_closed_once(self):
        value=fixture();value.negotiate=Mock(return_value={});value.close_path=Mock();read,write=os.pipe();self.addCleanup(os.close,write)
        def request(_interface,method,*_):
            if method=='CreateSession':return {'session_handle':value.session}
            if method=='Start':return {'devices':3,'streams':[(7,{'size':(1280,800)})]}
            return {}
        value.request=Mock(side_effect=request)
        fds=Mock();fds.get.return_value=read
        def remote(*_):value.request_stop();return GLib.Variant('(h)',(0,)),fds
        value.bus.call_with_unix_fd_list_sync.side_effect=remote
        with self.assertRaisesRegex(RuntimeError,'stopped'):value.connect()
        with self.assertRaises(OSError):os.fstat(read)
        self.assertIsNone(value.fd);value.close()

    def test_incomplete_device_grant_is_refused_without_pipewire_or_input(self):
        value=fixture();value.negotiate=Mock(return_value={});value.close_path=Mock()
        def request(_interface,method,*_):
            if method=='CreateSession':return {'session_handle':value.session}
            if method=='Start':return {'devices':0,'streams':[(7,{})]}
            return {}
        value.request=Mock(side_effect=request)
        with self.assertRaisesRegex(RuntimeError,'must be shared together'):value.connect()
        value.bus.call_with_unix_fd_list_sync.assert_not_called();self.assertIsNone(value.session)
