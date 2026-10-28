# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('tool_repair_compat',Path(__file__).resolve().parents[1]/'scripts/tool-repair-compat.py')
compat=importlib.util.module_from_spec(spec);spec.loader.exec_module(compat)
class CompatibleDshTimeTests(unittest.TestCase):
 def test_optional_times_preserve_branching_values_and_old_chunk_only_adapter(self):
  start="event={'type':'assistant/start','time':frame['frame']['time'],'data':{}}"
  chunk="event={'type':'assistant/chunk','time':frame['frame']['time'],'data':{'chunk':frame['frame']['chunk']}}"
  for include_start in [True,False]:
   branches=("    if frame['type']=='start':\n        "+start+"\n    elif" if include_start else "    if")
   original="def convert(frame):\n    event=None\n"+branches+" frame['type']=='chunk':\n        "+chunk+"\n    else: event={'type':'terminal'}\n    return event\n"
   patched=compat.optional_dsh_times(original);self.assertEqual(compat.optional_dsh_times(patched),patched)
   scope={};exec(patched,scope)
   for kind in ['start','chunk'] if include_start else ['chunk']:
    for timestamp in ['absent',None,0,42]:
     frame={'type':kind,'frame':{'chunk':'hello'}}
     if timestamp!='absent':frame['frame']['time']=timestamp
     result=scope['convert'](frame);self.assertEqual(result['type'],'assistant/'+kind)
     self.assertEqual('time' in result,timestamp!='absent')
     if timestamp!='absent':self.assertEqual(result['time'],timestamp)
   self.assertEqual(scope['convert']({'type':'terminal'}),{'type':'terminal'})
if __name__=='__main__':unittest.main()
