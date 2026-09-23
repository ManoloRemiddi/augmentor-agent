#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Installed upgrade/rollback/failure proof in an expendable container or test VM."""
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

assert os.getuid()==0
assert Path('/run/.containerenv').exists() or Path('/.dockerenv').exists() or Path('/etc/augmentor-test-vm').exists()
APP=Path('/usr/lib/augmentor')
HOME=Path('/home/beta')
LOG=Path('/tmp/augmentor-lifecycle-proof');LOG.mkdir(exist_ok=True)
base=Path(sys.argv[1]);current=Path(sys.argv[2])
for directory in (base,current):
    manifest=json.loads((directory/'artifacts.json').read_text())
    for item in manifest['artifacts']:
        assert Path(item['file']).name==item['file']
        with (directory/item['file']).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256']


def run(args,ok=True):
    result=subprocess.run(args,text=True,capture_output=True,env={**os.environ,'DEBIAN_FRONTEND':'noninteractive'})
    (LOG/(str(time.time_ns())+'.log')).write_text(result.stdout+result.stderr)
    if ok:assert result.returncode==0,result.stdout+result.stderr
    else:assert result.returncode!=0,'Operation should have refused: '+str(args)
    return result


def user(args,ok=True):
    return run(['runuser','-u','beta','--','env','AUGMENTOR_PI_NODE=/usr/lib/augmentor/node/bin/node',*args],ok)


def python(code,*args,ok=True):
    return user(['python3','-c',code,*args],ok)


def call(method,params=None):
    code="import sys,json;sys.path.insert(0,'/usr/lib/augmentor/apps/native');from augmentor_linux.pi_client import PiClient;print(json.dumps(PiClient().call(sys.argv[1],json.loads(sys.argv[2]))))"
    return json.loads(python(code,method,json.dumps(params or {})).stdout)


def journal_bytes():
    return (HOME/'.local/state/augmentor-pi/sessions/upgrade-context.events.jsonl').read_bytes()


def display_history(value):
    # The newer API suppresses streaming deltas covered by a final reply.
    # Preserve every other event, field and ordering in the comparison.
    compact=[];pending=[]
    for row in value['events']:
        event=row['event'];data=event.get('data',{})
        if event['type']=='assistant/chunk':
            chunk=data.get('chunk',{})
            if chunk.get('type')=='reasoning-delta' and not chunk.get('text'):continue
            pending.append(row);continue
        final=event['type']=='assistant/message' and any(
            part.get('type')=='text' and part.get('text')
            for part in data.get('message',{}).get('content',[]))
        if not final:compact.extend(pending)
        pending=[];compact.append(row)
    compact.extend(pending)
    return {**value,'events':compact}


def assert_history_preserved(expected,expected_journal):
    actual=call('session.history',{'sessionId':'upgrade-context'})
    assert journal_bytes()==expected_journal,'Upgrade/rollback changed the persisted display journal'
    assert display_history(actual)==display_history(expected),'Completed history or nonredundant events changed'


def assert_prompts_preserved(expected):
    actual=call('prompts.list')
    # New releases may add response fields, such as improvement instructions.
    # Every saved prompt field (IDs, content, revisions and timestamps) and the
    # library revision must still match exactly across both directions.
    assert actual['prompts']==expected['prompts'],{'expected':expected,'actual':actual}
    assert actual['revision']==expected['revision'],{'expected':expected,'actual':actual}
    return actual


def packages(directory):
    return [str(directory/item['file']) for item in json.loads((directory/'artifacts.json').read_text())['artifacts']]


def install(directory):run(['apt-get','install','-y','--allow-downgrades',*packages(directory)])
def prepare(remove=False):
    return json.loads(user(['augmentor-maintenance','prepare',*(['--remove'] if remove else [])]).stdout)
def until(check,timeout=25):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if check():return
        time.sleep(.05)
    raise AssertionError('Lifecycle condition timed out')


requests=[]
slow=threading.Event()
class Model(http.server.BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));requests.append(body)
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
        def chunk(text,finish=None):
            value={'id':'lifecycle','object':'chat.completion.chunk','created':1,'model':'fixture','choices':[{'index':0,'delta':{'role':'assistant','content':text},'finish_reason':finish}]}
            self.wfile.write(('data: '+json.dumps(value)+'\n\n').encode());self.wfile.flush()
        try:
            if 'SLOW' in json.dumps(body['messages'][-1]):
                slow.set()
                for _ in range(1200):chunk('working ');time.sleep(.05)
            else:chunk('Lifecycle context: Café π','stop')
            self.wfile.write(b'data: [DONE]\n\n')
        except (BrokenPipeError,ConnectionResetError):pass


run(['apt-get','update'])
if not HOME.exists():run(['useradd','--create-home','beta'])
install(base)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Model)
threading.Thread(target=server.serve_forever,daemon=True).start()
model={'providers':{'fixture':{'baseUrl':f'http://127.0.0.1:{server.server_port}/v1','api':'openai-completions','apiKey':'fixture-not-a-credential',
       'models':[{'id':'fixture','name':'Fixture','reasoning':False,'input':['text'],'contextWindow':32000,'maxTokens':2048}]}}}
python("from pathlib import Path;import sys,os;os.umask(0o077);p=Path.home()/'.config/augmentor-pi/agent';p.mkdir(parents=True,exist_ok=True);(p/'models.json').write_text(sys.argv[1])",json.dumps(model))
events=None
try:
    assert call('host.describe')['version']==json.loads((base/'artifacts.json').read_text())['version']
    call('session.create',{'sessionId':'upgrade-context','cwd':str(HOME/'work'),'selection':{'provider':'fixture','model':'fixture'}})
    call('session.prompt',{'sessionId':'upgrade-context','content':[{'type':'text','text':'Keep this context across upgrades.'}]})
    until(lambda:not next(r for r in call('session.list')['items'] if r['sessionId']=='upgrade-context')['running'])
    events=call('session.history',{'sessionId':'upgrade-context'});journal=journal_bytes()
    prompts=call('prompts.save',{'name':'lifecycle','content':'Rewrite [clipboard]. Café π'})
    old_release=(APP/'release.json').read_bytes()
    denied=run(['apt-get','install','-y',*packages(current)],ok=False)
    assert 'Augmentor is still open' in denied.stdout+denied.stderr
    assert (APP/'release.json').read_bytes()==old_release,'An in-use release was overwritten'
    # The 0.2.0 baseline predates maintenance; close its owned worker and prompt
    # service through their verified private endpoints, without touching DSH.
    if Path('/usr/bin/augmentor-maintenance').exists():
        assert prepare()['prepared']
    else:
        call('host.shutdown')
        python("import sys,os,signal;sys.path.insert(0,'/usr/lib/augmentor/apps/native');from augmentor_linux.prompt_client import PromptClient;p=PromptClient().call('host.describe');os.kill(p['pid'],signal.SIGTERM)")
        until(lambda:not (HOME/'.local/state/augmentor/prompts.sock').exists())
    install(current)
    before=len(requests)
    assert call('host.describe')['version']==json.loads((current/'artifacts.json').read_text())['version']
    assert_history_preserved(events,journal)
    upgraded=assert_prompts_preserved(prompts)
    assert upgraded['improvement']['content'] and upgraded['improvement']['revision']==0
    custom_improvement='Keep these custom instructions across rollback. Café π'
    code="import sys,json;sys.path.insert(0,'/usr/lib/augmentor/apps/native');from augmentor_linux.prompt_client import PromptClient;print(json.dumps(PromptClient().call('prompts.improvement.save',{'content':sys.argv[1],'expectedRevision':0})))"
    prompts=json.loads(python(code,custom_improvement).stdout)
    assert len(requests)==before,'Upgrade replayed a model request'
    call('session.prompt',{'sessionId':'upgrade-context','content':[{'type':'text','text':'SLOW'}]})
    assert slow.wait(20)
    refusal=user(['augmentor-maintenance','prepare'],ok=False)
    assert 'active Pi tasks' in refusal.stdout+refusal.stderr
    denied=run(['apt-get','install','-y','--allow-downgrades',*packages(base)],ok=False)
    assert 'Augmentor is still open' in denied.stdout+denied.stderr
    assert call('host.describe')['activeTurns']==1,'Maintenance aborted a task'
    # Removing only the desktop preserves a running companion and its task.
    run(['apt-get','remove','-y','augmentor-desktop'])
    assert call('host.describe')['activeTurns']==1
    call('session.cancel',{'sessionId':'upgrade-context'})
    until(lambda:call('host.describe')['activeTurns']==0)
    events=call('session.history',{'sessionId':'upgrade-context'});journal=journal_bytes()
    prepared=prepare();assert prepared['prepared']
    assert (Path(prepared['backup'])/'data/shared/prompts.sqlite3').exists()
    # Stop between unpack and configure: launches must fail throughout that
    # interrupted state, then recover through normal dpkg configuration.
    run(['dpkg','--unpack',*packages(current)])
    blocked=user(['augmentor-runtime'],ok=False)
    assert 'maintenance' in blocked.stderr
    run(['dpkg','--configure','augmentor-runtime','augmentor-desktop'])
    assert call('host.describe')
    assert_history_preserved(events,journal)
    prepare()
    install(base)
    before=len(requests)
    assert call('host.describe')['version']==json.loads((base/'artifacts.json').read_text())['version']
    assert_history_preserved(events,journal)
    assert_prompts_preserved(prompts)
    assert len(requests)==before,'Rollback replayed a model request'
    if Path('/usr/bin/augmentor-maintenance').exists():
        assert prepare()['prepared']
    else:
        call('host.shutdown')
        python("import sys,os,signal;sys.path.insert(0,'/usr/lib/augmentor/apps/native');from augmentor_linux.prompt_client import PromptClient;p=PromptClient().call('host.describe');os.kill(p['pid'],signal.SIGTERM)")
        until(lambda:not (HOME/'.local/state/augmentor/prompts.sock').exists())
    install(current)
    # Create real owned integration files, plus unrelated user content that must
    # survive removal. The separate X11 proof tests live KDE binding cleanup.
    python("""from pathlib import Path
import shutil,json
root=Path.home()/'.local/share'
legacy=root/'augmentor-pi/app';legacy.mkdir(parents=True,exist_ok=True);(legacy/'preserved.txt').write_text('Legacy app must remain available')
for folder in ('applications','kglobalaccel'):
 p=root/folder;p.mkdir(parents=True,exist_ok=True)
 text=Path('/usr/share/applications/com.augmentor.Agent.desktop').read_text().replace('Exec=augmentor-agent','Exec='+str(legacy/'scripts/augmentor-linux'))
 (p/'com.augmentor.LinuxPi.desktop').write_text(text+'X-KDE-Shortcuts=Ctrl+Alt+J\\n')
 (p/'unrelated.desktop').write_text('[Desktop Entry]\\nName=Unrelated\\n')
target=Path.home()/'.config/chromium/NativeMessagingHosts';target.mkdir(parents=True,exist_ok=True)
host=json.loads(Path('/etc/chromium/native-messaging-hosts/com.augmentor.agent.json').read_text());host['path']=str(legacy/'scripts/augmentor-browser-host')
(target/'com.augmentor.agent.json').write_text(json.dumps(host))
""")
    migrated=json.loads(user(['augmentor-maintenance','migrate']).stdout)
    assert migrated['migrated']['shortcutMigrated']
    assert (HOME/'.local/share/augmentor-pi/app/preserved.txt').read_text()=='Legacy app must remain available'
    assert not (HOME/'.local/share/applications/com.augmentor.LinuxPi.desktop').exists()
    assert 'X-KDE-Shortcuts=Ctrl+Alt+J' in (HOME/'.local/share/applications/com.augmentor.Agent.desktop').read_text()
    assert json.loads((HOME/'.config/chromium/NativeMessagingHosts/com.augmentor.agent.json').read_text())['path']=='/usr/bin/augmentor-browser-host'
    assert call('host.describe')
    assert_prompts_preserved(prompts)
    removed=prepare(True)
    assert len(removed['removedIntegrations'])==3,removed
    run(['apt-get','remove','-y','augmentor-desktop','augmentor-runtime'])
    assert not Path('/usr/bin/augmentor-browser-host').exists()
    assert (HOME/'.local/share/applications/unrelated.desktop').is_file()
    assert not (HOME/'.local/share/applications/com.augmentor.Agent.desktop').exists()
    assert (HOME/'.local/share/augmentor/prompts.sqlite3').is_file()
    install(current)
    before=len(requests)
    assert call('host.describe')
    assert_history_preserved(events,journal)
    restored=assert_prompts_preserved(prompts)
    assert restored['improvement']==prompts['improvement'],'Rollback or reinstall lost custom improvement instructions'
    assert len(requests)==before,'Reinstallation replayed a model request'
    prepare()
    result={'baseline':json.loads((base/'artifacts.json').read_text())['version'],'candidate':json.loads((current/'artifacts.json').read_text())['version'],
            'inUseUpgradeRefused':True,'activeTaskPreserved':True,'desktopRemovalPreservedActiveCompanion':True,
            'interruptedConfigurationBlocksLaunch':True,'configureRecovery':True,'rollbackPreservedHistoryAndPrompts':True,
            'legacyIntegrationsMigratedWithAppPreserved':True,'ownedIntegrationsRemoved':True,'unrelatedFilesPreserved':True,'reinstallPreservedDataWithoutReplay':True,
            'customImprovementPreservedAcrossRollback':True}
    (HOME/'lifecycle-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
finally:
    server.shutdown();server.server_close()
