# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Author-supplied synthetic JSON -> real exporter CLI, using only read APIs."""
import os,sys,json,copy,base64,hashlib,types,importlib.util,contextlib,io,collections
from pathlib import Path
os.umask(0o077)
root,source,output=sys.argv[1:];root=Path(root);source=Path(source);output=Path(output)
spec=importlib.util.spec_from_file_location('exporter',root/'scripts/export-dsh-project.py');exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
value=json.loads(source.read_text());value['workspace']['workspaceId']='authored-bundle-project';home=source.parent/'source-dsh';home.mkdir(mode=0o700)
for row in value.get('attachments',[]):
 raw=base64.b64decode(row['data']);sha=hashlib.sha256(raw).hexdigest();assert row['attachmentId']=='sha256:'+sha
 path=home/'attachments/v1/objects'/sha[:2]/sha;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);path.write_bytes(raw)
class ReadOnly:
 def __init__(self):self.counts=collections.Counter();self.rows={row['opening']['header']['id']:row for row in value['sessions']+value['relatedSessions']}
 def call(self,method):
  assert method in ('workspace.list','session.list');self.counts[method]+=1
  if method=='workspace.list':return copy.deepcopy({'items':[value['workspace']],'archivedSessionIds':value['archivedSessionIds'],'pinnedSessionIds':value['pinnedSessionIds']})
  return {'items':[{'sessionId':sid,'running':False} for sid in value['workspace']['sessionIds']]}
 def stream(self,method,params):assert method=='session/follow';self.counts[method]+=1;self.address=params['request']['address'];return self
 def item(self,sock):
  sid=self.address.get('sessionId',self.address.get('childSessionId'));return copy.deepcopy({'type':'snapshot',**self.rows[sid]['opening']})
 def close(self):pass
 def invoke(self,method,params):
  assert method=='session/page';self.counts[method]+=1;p=params['request'];sid=p['address'].get('sessionId',p['address'].get('childSessionId'));rows=[row for row in self.rows[sid]['records'] if row['event']['seq']<=p['throughSeq'] and row['event']['seq']<p.get('beforeSeq',30001)]
  return {'records':copy.deepcopy(rows[-p['maxMessages']:]),'hasMore':len(rows)>p['maxMessages']}
remote=ReadOnly();fake=types.ModuleType('dsh.remote');fake.Remote=lambda *args:remote;sys.modules['dsh.remote']=fake
sys.argv=['export-dsh-project.py','--project','authored-bundle-project','--output',str(output),'--dsh-home',str(home),'--bundle']
report=io.StringIO()
with contextlib.redirect_stdout(report):exporter.main()
print(json.dumps({'receipt':json.loads(report.getvalue()),'readOnlyRequests':dict(remote.counts)}))
