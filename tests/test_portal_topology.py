# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import os,sys,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services/desktop'))
try:
 from portal import Portal
 from screen_mapping import TopologyError,topology
except (ImportError,ValueError):Portal=None

@unittest.skipIf(Portal is None,'Linux portal dependencies unavailable')
class PortalTopologyTests(unittest.TestCase):
 def fixture(self,directory,scenes):
  p=Portal.__new__(Portal)
  p.owner=p.session=p.fd=p.node=p.stream=p.snapshot=p.request_path=None
  p.streams=[];p.bindings={};p.topology=None;p.persistence=False;p.cancel=threading.Event();p.keys=[];p.button=p.symbol=None;p.busy=threading.Lock();p.notify=Mock();p.restore_file=Path(directory)/'sharing.json';p.restore_file.write_text('{"restoreToken":"old"}')
  p.kwin=SimpleNamespace(read=Mock(side_effect=scenes))
  p.call=Mock(return_value=(2,));p.request=Mock(side_effect=[{'session_handle':'/session'},{},{},{'devices':3,'streams':[(1,{'source_type':1,'size':(800,600)})],'restore_token':'new'}])
  p.bus=SimpleNamespace(call_sync=Mock())
  return p
 def test_unidentifiable_selection_does_not_persist_a_failure_loop(self):
  screen={'name':'one','geometry':{'x':0,'y':0,'width':800,'height':600}}
  with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'XDG_SESSION_TYPE':'wayland','XDG_CURRENT_DESKTOP':'KDE'}):
   p=self.fixture(directory,[{'screens':[screen]},{'screens':[screen,{**screen,'name':'clone'}]}])
   with self.assertRaisesRegex(TopologyError,'identical logical sizes'):p.connect('codex:fixture')
   self.assertFalse(p.restore_file.exists());self.assertFalse(p.status()['active']);self.assertEqual(p.streams,[])
 def test_change_after_open_closes_fd_and_clears_all_bound_state(self):
  screen={'name':'one','geometry':{'x':0,'y':0,'width':800,'height':600}}
  with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'XDG_SESSION_TYPE':'wayland','XDG_CURRENT_DESKTOP':'KDE'}):
   p=self.fixture(directory,[{'screens':[screen]},{'screens':[screen]},{'screens':[{**screen,'scale':2}]}]);fd,writer=os.pipe()
   p.bus.call_with_unix_fd_list_sync=Mock(return_value=(SimpleNamespace(unpack=lambda:(0,)),SimpleNamespace(get=lambda _:fd)))
   try:
    with self.assertRaisesRegex(TopologyError,'topology changed'):p.connect('codex:fixture')
    with self.assertRaises(OSError):os.fstat(fd)
    self.assertFalse(p.restore_file.exists());self.assertIsNone(p.fd);self.assertIsNone(p.topology);self.assertEqual(p.bindings,{})
   finally:os.close(writer)
 def test_capture_and_input_reject_changed_topology_and_stop_connection(self):
  screen={'name':'one','geometry':{'x':0,'y':0,'width':800,'height':600}};changed={'screens':[{**screen,'scale':2}],'window':{'geometry':screen['geometry']}}
  for operation in ['capture','target']:
   with self.subTest(operation=operation),tempfile.TemporaryDirectory() as directory:
    p=self.fixture(directory,[changed]);p.owner='codex:fixture';p.fd,writer=os.pipe();p.topology=topology([screen]);p.bindings={1:'one'};p.streams=[(1,{'source_type':1,'size':(800,600)})]
    import time
    p.snapshot={'token':'fresh','created':time.monotonic(),'scene':{'screens':[screen]}}
    try:
     with self.assertRaisesRegex(TopologyError,'topology changed'):
      p.capture(p.owner) if operation=='capture' else p.target(p.owner,'fresh')
     self.assertIsNone(p.snapshot);self.assertEqual(p.status()['sharedScreens'],0);self.assertFalse(p.status()['persistentPermission']);self.assertIsNone(p.owner)
    finally:os.close(writer)
 def test_ordinary_observation_errors_keep_the_shared_connection(self):
  screen={'name':'one','geometry':{'x':0,'y':0,'width':800,'height':600}}
  for window in [None,{'geometry':{'x':900,'y':0,'width':100,'height':100}}]:
   with self.subTest(window=window),tempfile.TemporaryDirectory() as directory:
    p=self.fixture(directory,[{'screens':[screen],'window':window}]);p.owner='codex:fixture';p.fd,writer=os.pipe();p.topology=topology([screen]);p.bindings={1:'one'};p.streams=[(1,{'source_type':1,'size':(800,600)})]
    try:
     with self.assertRaises(RuntimeError):p.capture(p.owner)
     self.assertEqual(p.owner,'codex:fixture');self.assertEqual(p.bindings,{1:'one'});os.fstat(p.fd)
    finally:p.stop();os.close(writer)
 def test_success_persists_only_after_validation_and_service_can_reconnect(self):
  screen={'name':'one','geometry':{'x':0,'y':0,'width':800,'height':600}}
  with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'XDG_SESSION_TYPE':'wayland','XDG_CURRENT_DESKTOP':'KDE'}):
   p=self.fixture(directory,[{'screens':[screen]}]*6);readers=[];writers=[]
   for _ in range(2):
    fd,writer=os.pipe();readers.append(fd);writers.append(writer)
   p.bus.call_with_unix_fd_list_sync=Mock(side_effect=[(SimpleNamespace(unpack=lambda:(0,)),SimpleNamespace(get=lambda _,fd=fd:fd)) for fd in readers])
   responses=[{'session_handle':'/session'},{},{},{'devices':3,'streams':[(1,{'source_type':1,'size':(800,600)})],'restore_token':'new'}];p.request=Mock(side_effect=responses*2)
   import json
   try:
    for _ in range(2):
     # service.Handler clears cancellation only for a newly admitted connect.
     p.cancel.clear();self.assertTrue(p.connect('codex:fixture')['sharing']);self.assertEqual(json.loads(p.restore_file.read_text())['restoreToken'],'new');p.stop()
   finally:
    for writer in writers:os.close(writer)
if __name__=='__main__':unittest.main()
