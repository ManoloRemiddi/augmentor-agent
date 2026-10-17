# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Independently authored stores, initialized through public companion owners."""
import importlib.util
import json
import os
from pathlib import Path
import sys
root,base=Path(sys.argv[1]),Path(sys.argv[2]);mode=sys.argv[3] if len(sys.argv)>3 else 'plain'
sys.path.insert(0,str(root/'services'))
from memory.hindsight import HindsightMemory
from memory.dual import DualMemory
spec=importlib.util.spec_from_file_location('authored_prompt_service',root/'services/prompt-library/service.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
result={}
for name in ['source','target']:
 (base/name).mkdir(mode=0o700)
 data=base/name/'data';state=base/name/'state';data.mkdir(mode=0o700);state.mkdir(mode=0o700)
 os.environ.update(AUGMENTOR_SHARED_DATA=str(data),AUGMENTOR_SHARED_STATE=str(state),XDG_CONFIG_HOME=str(base/name/'config'),AUGMENTOR_PI_CONFIG=str(base/name/'pi-config'))
 library=module.Library(data/'prompts.sqlite3')
 def save(shortcut,content):return library.call('prompts.save',{'name':shortcut,'content':content},name+'-'+shortcut)
 save('same','Authored identical prompt. Café 😀');save('collide','Authored '+name+' prompt.')
 if name=='source':
  save('source-only','Authored source-only prompt.')
  library.call('prompts.improvement.save',{'content':'Authored source improvement instructions.','expectedRevision':0},'source-improve')
  value=library.call('prompts.import',{'source':'authored-dsh','prompts':[{'id':'deleted-old','name':'deleted-old','content':'Do not resurrect this deleted shortcut.'}]},'source-import')
  deleted=next(r for r in value['prompts'] if r['name']=='deleted-old');library.call('prompts.delete',{'id':deleted['id'],'expectedRevision':deleted['revision']},'source-delete')
 memory=HindsightMemory(data/'dual-memory.sqlite3');memory.call('memory.dual.configure',{'person':name+'-person'})
 sid='pi:'+name+'-chat';memory.call('memory.dual.bind',{'session':sid,'cwd':'/authored/'+name+'-project'})
 memory.call('memory.dual.append',{'session':sid,'events':[{'id':'event-1','role':'user','mode':'text','content':'Authored '+name+' human. Café 😀','status':'complete'}]})
 if name=='source':
  memory.call('memory.dual.append',{'session':sid,'events':[{'id':'event-2','role':'assistant','mode':'voice','content':'Authored source reply with an uncertain outcome.','status':'interrupted'}]})
  with memory.connect() as db:
   db.execute('INSERT INTO memory_eligible VALUES (1,NULL)')
   db.execute("INSERT INTO memory_windows VALUES ('old-window',?,999999999,0,'old-boot')",(sid,))
 if name=='target':memory.call('memory.dual.configure',{'enabled':False});memory.call('memory.dual.processing',{'paused':True})
 if mode in ('processed','target-processed'):
  config={'endpoint':'http://127.0.0.1:9','apiKey':'authored-not-a-secret'};(data/'hindsight.json').write_text(json.dumps(config));os.chmod(data/'hindsight.json',0o600)
  with memory.connect() as db:db.execute('INSERT OR IGNORE INTO hindsight_destination VALUES (1,?)',(config['endpoint'],))
  if name==('target' if mode=='target-processed' else 'source'):
   with memory.connect() as db:
    banks=memory.banks(db)
    for bank in banks:db.execute('UPDATE hindsight_banks SET ready=1,cursor=1,snapshot=?,updated=5 WHERE bank=?',(json.dumps({'summary':'Authored cached '+bank['kind'],'pages':[],'items':[{'text':'Authored cached fact.','document_id':'transcript-1-original'}]}),bank['bank']))
    values={'summary':'Authored old projection.','items':[{'text':'Authored old fact.','state':'uncertain','sources':[1]}]}
    for kind,scope in DualMemory.scopes(None,{'person':name+'-person','project':'/authored/'+name+'-project'}):
     db.execute('UPDATE projections SET revision=1,cursor=1,value=? WHERE kind=? AND scope=?',(json.dumps(values),kind,scope));db.execute('INSERT INTO revisions VALUES (?,?,1,1,?,5)',(kind,scope,json.dumps(values)))
    events=[dict(r) for r in db.execute('SELECT * FROM events WHERE seq=1')];stages=[{'stage':'retain','bank':banks[0]['bank']},{'stage':'consolidate','bank':banks[0]['bank']}]
    db.execute("INSERT INTO memory_jobs VALUES ('authored-job',?,?,?,1,'pending','',0)",(sid,json.dumps(events),json.dumps(stages)));db.execute("INSERT INTO memory_budgets VALUES ('authored-job',19,17,3,1,'pending')");db.execute("UPDATE memory_eligible SET job='authored-job'")
 result[name]={'state':str(state),'data':str(data),'sid':sid}
print(json.dumps(result))
