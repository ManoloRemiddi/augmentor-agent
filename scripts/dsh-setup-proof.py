#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Fresh DSH integration through the actual Qt setup form and running DSH SDK."""
import hashlib
import http.server
import json
import os
import re
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import yaml

ROOT=Path(__file__).resolve().parents[1]
(ROOT/'outputs').mkdir(parents=True,exist_ok=True)
APP=Path(os.environ.get('AUGMENTOR_PROOF_APP_ROOT',ROOT)).resolve()
BROWSER_ONLY=os.environ.get('AUGMENTOR_PROOF_COMPANION_DSH')=='1'
work=Path(tempfile.mkdtemp(prefix='augmentor-dsh-setup-',dir='/tmp' if sys.platform=='darwin' else None)).resolve()
os.environ.update(AUGMENTOR_SHARED_STATE=str(work/'shared-state'),AUGMENTOR_SHARED_DATA=str(work/'shared-data'),AUGMENTOR_SHARED_CONFIG=str(work/'shared-config'),AUGMENTOR_PI_CONFIG=str(work/'pi-config'),AUGMENTOR_PI_STATE=str(work/'pi-state'),AUGMENTOR_DSH_WORKSPACE_ROOT=str(work),QT_QPA_PLATFORM=os.environ.get('AUGMENTOR_PROOF_QT_PLATFORM','offscreen'))
sys.path[:0]=[str(APP/'apps/native'),str(APP/'services')]
from augmentor_linux.prompt_client import PromptClient
import augmentor_linux.prompt_client as loaded_prompts
assert Path(loaded_prompts.__file__).resolve().is_relative_to(APP)
if BROWSER_ONLY:
    # Source adapter is test instrumentation only; service startup stays installed.
    import augmentor_linux
    augmentor_linux.__path__.append(str(ROOT/'apps/native/augmentor_linux'))
from augmentor_linux.adapters.dsh import DshAdapter
import augmentor_linux.adapters.dsh as loaded_adapter
if not BROWSER_ONLY:
    assert Path(loaded_adapter.__file__).resolve().is_relative_to(APP),loaded_adapter.__file__
    from augmentor_linux.dsh_setup import DshSetupDialog
    from PySide6.QtWidgets import QApplication,QWidget
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    app=QApplication([])
    class Owner(QWidget):
        controller=None;editing=False;selected=None
        def switch_harness(self,harness,reconnect=False):self.selected=(harness,reconnect)
    owner=Owner()
else:app=None
received=[]
class Model(http.server.BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['content-length'])));received.append(body)
        self.send_response(200);self.send_header('content-type','text/event-stream');self.end_headers()
        user=next((str(m['content']) for m in reversed(body['messages']) if m['role']=='user'),'')
        if any(m['role']=='user' and 'desktop free search fixture' in str(m['content']) for m in body['messages']):
            if not any(m['role']=='tool' for m in body['messages']):
                delta={'role':'assistant','tool_calls':[{'index':0,'id':'free-search','type':'function','function':{'name':'web_search','arguments':json.dumps({'queries':['Debian official documentation']})}}]};reason='tool_calls'
            else:delta={'role':'assistant','content':'Free search fixture completed.'};reason='stop'
        elif any(m['role']=='user' and 'desktop wiki parity fixture' in str(m['content']) for m in body['messages']):
            done=sum(m['role']=='tool' for m in body['messages'])
            actions=[('wiki_query',{'query':'AUGMENTOR WIKI PARITY','mode':'quick'}),('skill',{'name':'wiki-query'})]
            if os.environ.get('AUGMENTOR_PROOF_WIKI_MUTATIONS'):
                actions.extend([
                    ('wiki_write',{'title':'Acceptance Page','type':'concept','content':'AUGMENTOR WRITTEN PAGE','source_path':'.raw/acceptance.txt'}),
                    ('wiki_write',{'title':'Acceptance Link','type':'concept','content':'See [[Acceptance Page]].'}),
                    ('wiki_rename',{'title':'Acceptance Page','new_title':'Renamed Acceptance Page'}),
                    ('wiki_archive',{'source_path':'.raw/acceptance.txt'}),
                ])
            if done<len(actions):
                name,args=actions[done];delta={'role':'assistant','tool_calls':[{'index':0,'id':'wiki-'+str(done),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]};reason='tool_calls'
            else:delta={'role':'assistant','content':'Wiki parity fixture completed.'};reason='stop'
        elif 'DSH browser fixture' in user:
            done=sum(m['role']=='tool' for m in body['messages'])
            url=re.search(r'http://127\.0\.0\.1:\d+/fixture',user).group()
            actions=[('browser_navigate',{'url':url}),('browser_snapshot',{}),('browser_type',{'selector':'#entry','text':'DSH VERIFIED BROWSER'}),('browser_click',{'selector':'#apply'}),('browser_snapshot',{})]
            if done<len(actions):
                name,args=actions[done];delta={'role':'assistant','tool_calls':[{'index':0,'id':'browser-'+str(done),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]};reason='tool_calls'
            else:delta={'role':'assistant','content':'DSH VERIFIED BROWSER'};reason='stop'
        elif 'native approval fixture' in user and body['messages'][-1]['role']!='tool':
            delta={'role':'assistant','tool_calls':[{'index':0,'id':'native-approval','type':'function','function':{'name':'fixture_approval','arguments':'{}'}}]};reason='tool_calls'
        elif 'native question fixture' in user and body['messages'][-1]['role']!='tool':
            delta={'role':'assistant','tool_calls':[{'index':0,'id':'native-question','type':'function','function':{'name':'ask_user_question','arguments':json.dumps({'questions':[{'id':'choice','question':'Choose a fixture value','options':[{'label':'Alpha'},{'label':'Beta'}]}]})}}]};reason='tool_calls'
        elif 'shared capabilities fixture' in user and body['messages'][-1]['role']!='tool':
            delta={'role':'assistant','tool_calls':[{'index':0,'id':'shared-read','type':'function','function':{'name':'read','arguments':json.dumps({'file_path':str(work/'shared-capabilities.txt')})}}]};reason='tool_calls'
        else:delta={'role':'assistant','content':'DSH EDIT VERIFIED' if 'DSH EDIT VERIFIED' in user else 'DSH BRANCH CONTINUED' if 'DSH BRANCH CONTINUED' in user else 'Fixture reply.'};reason='stop'
        chunks=[(delta,None),({},reason)]
        streaming='Display regression test:' in user
        if streaming:
            chunks=[({'role':'assistant','content':'The final '},None),({'content':'answer stays '},None),({'content':'visible.'},None),({},'stop')]
        for d,r in chunks:
            self.wfile.write(('data: '+json.dumps({'id':'proof','object':'chat.completion.chunk','created':1,'model':'fixture','choices':[{'index':0,'delta':d,'finish_reason':r}]})+'\n\n').encode())
            self.wfile.flush()
            if streaming:time.sleep(.3)
        self.wfile.write(b'data: [DONE]\n\n')
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Model);threading.Thread(target=server.serve_forever,daemon=True).start()
def until(check,seconds=45):
    end=time.monotonic()+seconds;last=None
    while time.monotonic()<end:
        if app is not None:app.processEvents()
        try:
            result=check()
            if result:return result
        except (OSError,RuntimeError) as e:last=e
        time.sleep(.05)
    raise AssertionError('DSH proof timed out: '+str(last))
modules=Path(os.environ['DSH_TEST_MODULES']).resolve();assert modules.is_dir()
home=work/'dsh';profile=home/'profiles/web';profile.mkdir(parents=True);(profile/'node_modules').symlink_to(modules,target_is_directory=True)
(profile/'package.json').write_text(json.dumps({'name':'augmentor-setup-proof','private':True,'type':'module','dsh':{'profile':{'bundles':['@deepseek-ai/dsh-base','@deepseek-ai/dsh-web-app']}}}))
(profile/'cordis.yml').write_text('[]\n');original='# Existing user customization\n- id: session-title-llm\n  disabled: true\n'
if os.environ.get('AUGMENTOR_PROOF_EXISTING_PROMPTS'):
    original+=yaml.safe_dump([{'insert':[{'id':'existing-prompts','name':str(APP/'adapters/dsh-prompt-library/lib/index.js')}]}])
web_provider=os.environ.get('AUGMENTOR_PROOF_WEB_PROVIDER')
if web_provider:
    web_provider=Path(web_provider).resolve()
    assert json.loads((web_provider/'package.json').read_text())['version']=='0.1.0'
    original+=yaml.safe_dump([{'id':'web','config':{'searchProvider':'web-search-free'}},{'insert':[{'id':'free-search-proof','name':str(web_provider/'index.js')}]}])
host_plugins=os.environ.get('AUGMENTOR_PROOF_HOST_PLUGIN_MODULES')
if host_plugins:
    host_plugins=Path(host_plugins).resolve()
    for name,version in [('dsh-context','0.48.0'),('dsh-adaptive-reasoning','0.2.0')]:
        assert json.loads((host_plugins/name/'package.json').read_text())['version']==version
    original+=yaml.safe_dump([{'insert':[
        {'id':'context-proof','name':str(host_plugins/'dsh-context/lib/index.js')},
        {'id':'adaptive-proof','name':str(host_plugins/'dsh-adaptive-reasoning/src/index.js'),'config':{
            'presets':['augmentor-linux-product'],'textOnly':True,
            'routes':[{'provider':'fixture','model':'fixture','efforts':{'off':'off','low':'low','medium':'medium','high':'high'}}]}},
    ]}])
wiki_modules=os.environ.get('AUGMENTOR_PROOF_WIKI_MODULES')
if wiki_modules:
    wiki_modules=Path(wiki_modules).resolve()
    for name,version in [('dsh-plugin-wiki-tools','0.14.0'),('dsh-plugin-wiki-skills','0.2.1')]:
        assert json.loads((wiki_modules/name/'package.json').read_text())['version']==version
    vault=work/'wiki-vault';(vault/'wiki').mkdir(parents=True)
    (vault/'wiki/hot.md').write_text('# Hot cache\nAUGMENTOR WIKI PARITY\n')
    (vault/'wiki/index.md').write_text('# Index\nTemporary acceptance vault.\n')
    if os.environ.get('AUGMENTOR_PROOF_WIKI_MUTATIONS'):
        (vault/'.raw').mkdir()
        (vault/'.raw/acceptance.txt').write_text('AUGMENTOR RAW SOURCE\n')
    original+=yaml.safe_dump([{'insert':[
        {'id':'wiki-tools','name':str(wiki_modules/'dsh-plugin-wiki-tools/index.js'),'config':{'vaultPath':str(vault)}},
        {'id':'wiki-skills','name':str(wiki_modules/'dsh-plugin-wiki-skills/index.js')},
    ]}])
if picker:=os.environ.get('AUGMENTOR_PROOF_MODEL_PICKER'):
    original+=yaml.safe_dump([{'insert':[{'id':'model-picker-augmented','name':str(Path(picker).resolve()/'lib/index.js')}]}])
if os.environ.get('AUGMENTOR_PROOF_APPROVALS'):
    original+=yaml.safe_dump([{'insert':[{'id':'approval-proof','name':str(ROOT/'tests/fixtures/dsh-approval.mjs')}]}])
(profile/'cordis.patch.yml').write_text(original)
(home/'settings.yaml').write_text(yaml.safe_dump({'llm-pi-ai':{'providers':{'fixture':{'api':'openai-completions','baseURL':f'http://127.0.0.1:{server.server_port}/v1','apiKeyEnv':'AUGMENTOR_FIXTURE_KEY','models':[{'id':'fixture','name':'Fixture','contextWindow':32000,'maxTokens':1024,'reasoning':False,'input':['text']}]}}},'agent-default-model':{'provider':'fixture','model':'fixture'}}))
if host_plugins:
    settings=yaml.safe_load((home/'settings.yaml').read_text())
    settings['llm-pi-ai']['providers']['fixture']['models'][0]['reasoningEfforts']={'off':None,'low':'low','medium':'medium','high':'high'}
    (home/'settings.yaml').write_text(yaml.safe_dump(settings))
if picker:
    settings=yaml.safe_load((home/'settings.yaml').read_text())
    models=settings['llm-pi-ai']['providers']['fixture']['models']
    models.append({**models[0],'id':'hidden-fixture','name':'Hidden Fixture'})
    (home/'settings.yaml').write_text(yaml.safe_dump(settings))
with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
base=f'http://127.0.0.1:{port}';process=None;log=(work/'dsh.log').open('w');prompts=PromptClient()
def start():
    global process
    log_offset=(work/'dsh.log').stat().st_size
    env={**os.environ,'DSH_HOME':str(home),'DSH_TELEMETRY_MODE':'DISABLED','AUGMENTOR_FIXTURE_KEY':'fixture'}
    process=subprocess.Popen(['dsh','web','--no-open','--host','127.0.0.1','--port',str(port)],env=env,stdout=log,stderr=log,start_new_session=True)
    def authenticated():
        # A product API may become ready before the new launch URL is logged.
        # Never accept a token left by the previous process in the shared log.
        with (work/'dsh.log').open('rb') as stream:
            stream.seek(log_offset)
            current_log=stream.read().decode(errors='replace')
        hits=re.findall(r'token=([A-Za-z0-9_-]+)',current_log)
        if not hits:return False
        os.environ['AUGMENTOR_DSH_AUTH_TOKEN']=hits[-1]
        return DshAdapter(base=base,home=home).call('host.describe')
    until(authenticated)
def stop():
    global process
    if process:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        process=None

def click(button):assert button.isEnabled();QTest.mouseClick(button,Qt.MouseButton.LeftButton);until(lambda:not dialog.busy)
try:
    print('Fixture: '+str(work),flush=True);start()
    if BROWSER_ONLY:
        checked=prompts.call('dsh.check',{'endpoint':base,'home':str(home)})
        assert not checked['installed']
        prompts.call('dsh.install',{'token':checked['token']})
        assert next(profile.glob('cordis.patch.yml.before-augmentor-*')).read_text()==original
        stop();start()
        checked=prompts.call('dsh.check',{'endpoint':base,'home':str(home)})
        assert checked['installed'],checked
        prompts.call('dsh.save',{'token':checked['token']})
        adapter=DshAdapter()
        if picker:
            adapter.call('models.pin',{'provider':'fixture','model':'fixture','pinned':True})
            section=adapter.setting('model-picker-augmented')
            adapter.call('settings.mutate',{'ns':'model-picker-augmented','expectedRevision':section['revision'],'ops':[{'op':'set','path':['hidden'],'value':{'fixture/hidden-fixture':True}}]})
        adapter.call('session.create',{'sessionId':'setup-linux','agentPreset':'augmentor-linux-product','cwd':str(work)})
        browser_env={**os.environ,'AUGMENTOR_PROOF_DSH_SETUP_ONLY':'1'}
        subprocess.run([sys.executable,str(ROOT/'scripts/browser-composable-proof.py')],env=browser_env,check=True,timeout=180)
        evidence={'fixture':str(work),'appRoot':str(APP),'promptClientFile':loaded_prompts.__file__,
                  'instrumentationAdapterFile':loaded_adapter.__file__,'qtInstall':False,
                  'installedServiceSetup':True,'profilePreserved':True,'modelRequests':len(received),'wikiToolAndSkillWorkflow':bool(wiki_modules),'contextAndAdaptiveWorkflow':bool(host_plugins),'freeWebSearchWorkflow':bool(web_provider),
                  'browser':json.loads((ROOT/'outputs/browser-dsh-setup-proof.json').read_text())}
        (ROOT/'outputs/companion-dsh-proof.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print(json.dumps(evidence),flush=True)
        raise SystemExit(0)
    dialog=DshSetupDialog(owner);dialog.show();until(lambda:not dialog.busy)
    dialog.endpoint.setText(base);dialog.home.setText(str(home));click(dialog.check)
    assert dialog.token and not dialog.installed,dialog.note.text()
    click(dialog.install);assert 'Restart DSH' in dialog.note.text(),dialog.note.text()
    assert (profile/'cordis.patch.yml').read_text().startswith(original.rstrip())
    assert next(profile.glob('cordis.patch.yml.before-augmentor-*')).read_text()==original
    assert all((home/'.agent-presets'/('augmentor-'+s+'-product')/'agent.cordis.yml').exists() for s in ('linux','browser'))
    if os.environ.get('AUGMENTOR_PROOF_EXISTING_PROMPTS'):
        installed_patch=(profile/'cordis.patch.yml').read_text()
        assert installed_patch.count('existing-prompts')==1
        assert 'augmentor-product-prompts' not in installed_patch
        print('Existing prompt library retained without a duplicate product entry',flush=True)
    print('Actual Qt install: original profile preserved, roles installed',flush=True)
    checked=prompts.call('dsh.check',{'endpoint':base,'home':str(home)})
    before_patch=(profile/'cordis.patch.yml').read_text()
    prompts.call('dsh.install',{'token':checked['token']})
    assert (profile/'cordis.patch.yml').read_text()==before_patch
    assert len(list(profile.glob('augmentor-product.before-*')))==1
    custom=home/'.agent-presets/augmentor-linux-product/agent.cordis.yml';preserved=custom.read_text();custom.write_text(preserved+'# user customization\n')
    checked=prompts.call('dsh.check',{'endpoint':base,'home':str(home)})
    try:
        prompts.call('dsh.install',{'token':checked['token']});raise AssertionError('Customized preset overwritten')
    except Exception as e:assert not isinstance(e,AssertionError) and 'edited' in str(e),e
    assert custom.read_text()==preserved+'# user customization\n';custom.write_text(preserved)
    print('Owned integration refresh preserves the patch; customized preset replacement refused',flush=True)
    if os.environ.get('AUGMENTOR_PROOF_CUSTOM_COMPACTION'):
        entries=yaml.safe_load(custom.read_text())
        group=next(row for row in entries if row['id']=='compaction')
        basic=next(row for row in group['config'] if row['id']=='compaction-basic')
        basic['config']={'thresholdRatio':0.5,'retainTokens':0,'maxTokens':8192}
        pruner=next(row for row in group['config'] if row['id']=='tool-result-pruner')
        pruner['config']={'thresholdChars':4096,'headChars':2048,'tailChars':512}
        custom.write_text(json.dumps(entries,indent=2)+'\n')
        print('Testing preserved reference compaction with expanded desktop capabilities',flush=True)
    stop();start();click(dialog.check);assert dialog.installed,dialog.note.text()
    click(dialog.save);until(lambda:owner.selected);assert owner.selected==('dsh',True)
    saved=json.loads((work/'shared-config/harnesses.json').read_text())['dsh'];assert saved['endpoint']==base and saved['home']==str(home)
    assert (work/'shared-config/harnesses.json').stat().st_mode&0o777==0o600
    adapter=DshAdapter();assert adapter.product and adapter.preset=='augmentor-linux-product'
    adapter.call('host.describe');print('Checked DSH integration saved and reconnected',flush=True)
    if picker:
        adapter.call('models.pin',{'provider':'fixture','model':'fixture','pinned':True})
        section=adapter.setting('model-picker-augmented')
        adapter.call('settings.mutate',{'ns':'model-picker-augmented','expectedRevision':section['revision'],'ops':[{'op':'set','path':['hidden'],'value':{'fixture/hidden-fixture':True}}]})
        curated=adapter.model_catalog();assert 'fixture/fixture' in curated['pinned'] and 'fixture/hidden-fixture' in curated['hidden'],curated
        print('Model Picker pins and visibility verified through the native adapter',flush=True)
        if os.environ.get('AUGMENTOR_PROOF_PICKER_UI'):
            from augmentor_linux.surfaces import ModelPicker
            from PySide6.QtCore import QTimer
            widget=ModelPicker();widget.set_catalog(curated);widget.show()
            selected=[];failures=[];widget.selected.connect(selected.append)
            def inspect_picker():
                try:
                    rows=[widget.rows.item(i) for i in range(widget.rows.count())]
                    models=[r.data(Qt.ItemDataRole.UserRole) for r in rows if r.data(Qt.ItemDataRole.UserRole)]
                    assert [m['model'] for m in models if m['provider']=='fixture']==['fixture'],models
                    assert widget.popup.windowTitle()=='Models'
                    widget.search.setText('Hidden Fixture')
                    assert widget.rows.count()==0
                    widget.search.clear()
                    row=next(widget.rows.item(i) for i in range(widget.rows.count()) if widget.rows.item(i).data(Qt.ItemDataRole.UserRole))
                    QTest.mouseClick(widget.rows.viewport(),Qt.MouseButton.LeftButton,pos=widget.rows.visualItemRect(row).center())
                except Exception as error:
                    failures.append(error);widget.popup.reject()
            QTimer.singleShot(150,inspect_picker)
            try:QTest.mouseClick(widget,Qt.MouseButton.LeftButton)
            finally:widget.close()
            assert not failures,failures
            assert len(selected)==1 and selected[0]['model']=='fixture',selected
            print('Actual Qt picker hides configured hidden model in provider/search rows and selects visible pinned model',flush=True)

    if web_provider:
        sid='desktop-free-search';before=len(received)
        adapter.call('session.create',{'sessionId':sid,'agentPreset':'augmentor-linux-product','cwd':str(work)})
        adapter.call('session.selectModel',{'sessionId':sid,'provider':'fixture','model':'fixture'})
        adapter.call('session.prompt',{'sessionId':sid,'mode':'queue','content':[{'type':'text','text':'desktop free search fixture'}]})
        until(lambda:len(received)>=before+2 and not next(r for r in adapter.call('session.list')['items'] if r['sessionId']==sid)['running'],90)
        replies=[m for m in received[-1]['messages'] if m['role']=='tool']
        assert len(replies)==1
        text=str(replies[0]['content'])
        assert 'https://' in text and 'debian.org' in text.lower(),text
        print('Free web search returns live Debian results through the desktop model tool',flush=True)
    if wiki_modules:
        sid='desktop-wiki-parity';before=len(received)
        adapter.call('session.create',{'sessionId':sid,'agentPreset':'augmentor-linux-product','cwd':str(work)})
        adapter.call('session.selectModel',{'sessionId':sid,'provider':'fixture','model':'fixture'})
        adapter.call('session.prompt',{'sessionId':sid,'mode':'queue','content':[{'type':'text','text':'desktop wiki parity fixture'}]})
        expected_tools=6 if os.environ.get('AUGMENTOR_PROOF_WIKI_MUTATIONS') else 2
        until(lambda:len(received)>=before+expected_tools+1 and not next(r for r in adapter.call('session.list')['items'] if r['sessionId']==sid)['running'])
        tool_catalog={t['function']['name'] for t in received[before]['tools']}
        assert {'wiki_query','wiki_write','wiki_lint','skill'}<=tool_catalog
        replies=[m for m in received[-1]['messages'] if m['role']=='tool']
        assert len(replies)==expected_tools
        assert 'AUGMENTOR WIKI PARITY' in str(replies[0]['content']),replies[0]
        skill_body=(wiki_modules/'dsh-plugin-wiki-skills/skills/wiki-query/SKILL.md').read_text().split('---',2)[-1].strip()
        assert skill_body[:80] in str(replies[1]['content']),replies[1]
        print('Desktop Wiki Tools query and Wiki Skills body reached the model from a temporary vault',flush=True)
        if os.environ.get('AUGMENTOR_PROOF_WIKI_MUTATIONS'):
            pages={}
            for path in (vault/'wiki').rglob('*.md'):
                content=path.read_text()
                if content.startswith('---\n'):
                    metadata=yaml.safe_load(content.split('---',2)[1])
                    if isinstance(metadata,dict):pages[metadata.get('title')]=content
            assert 'Acceptance Page' not in pages and 'Renamed Acceptance Page' in pages
            assert 'AUGMENTOR WRITTEN PAGE' in pages['Renamed Acceptance Page']
            assert '[[Renamed Acceptance Page]]' in pages['Acceptance Link']
            assert '[[Acceptance Page]]' not in pages['Acceptance Link']
            assert not (vault/'.raw/acceptance.txt').exists()
            assert (vault/'.archive/acceptance.txt').read_text()=='AUGMENTOR RAW SOURCE\n'
            assert not json.loads((vault/'.raw/.manifest.json').read_text())['sources']
            assert 'wiki_write: created' in str(replies[2]['content'])
            assert 'wiki_rename:' in str(replies[4]['content']) and 'wiki_archive:' in str(replies[5]['content'])
            print('Wiki write, inbound-link rename and raw-source archive verified independently on disk',flush=True)
    (work/'shared-capabilities.txt').write_text('SHARED SURFACE VERIFIED')
    desktop_tools=None
    for surface in ('linux','browser'):
        sid='setup-'+surface;before=len(received)
        adapter.call('session.create',{'sessionId':sid,'agentPreset':'augmentor-'+surface+'-product','cwd':str(work)})
        adapter.call('session.selectModel',{'sessionId':sid,'provider':'fixture','model':'fixture'})
        adapter.call('session.prompt',{'sessionId':sid,'mode':'queue','content':[{'type':'text','text':'shared capabilities fixture' if surface=='browser' else 'Reply to this setup fixture.'}]})
        until(lambda:len(received)>before and not next(r for r in adapter.call('session.list')['items'] if r['sessionId']==sid)['running'])
        tools={t['function']['name'] for t in received[before]['tools']};assert 'memory_recall' in tools,tools
        if surface=='linux':
            desktop_tools=tools
            assert 'linux_desktop_snapshot' in tools,tools
            required={'glob','grep','job_list','job_output','job_kill','skill','create_goal','get_goal','update_goal','exit_plan_mode','list_agents','subagent','subagent_fork','interrupt_agent','send_message','workflow','ralph','todo_write','web_search'}
            assert required <= tools, 'Missing desktop capabilities: '+str(sorted(required-tools))
            print('Desktop model-facing tools: '+json.dumps(sorted(tools)),flush=True)
            if host_plugins:
                from dsh.remote import client as parity_remote
                opening=parity_remote(base,home).snapshot(sid)
                values=opening['projections']['values']
                assert values['contextHeaders']['headers'],values.keys()
                assert values.get('contextTimeline'),values.keys()
                # The chat history API omits plugin bookkeeping events. Inspect
                # only this isolated fixture's persisted log for the decision.
                session_file=next((home/'sessions').glob('*/'+sid+'/session.v3.jsonl.zstd'))
                raw=subprocess.check_output(['zstd','-dc',str(session_file)],text=True)
                events=[json.loads(line) for line in raw.splitlines()]
                decisions=[e['data'] for e in events if e['type']=='adaptive-reasoning/decision']
                assert decisions and decisions[-1]['provider']=='fixture' and decisions[-1]['model']=='fixture'
                headers=[e['data']['header']['config'] for e in events if e['type']=='request/header']
                assert headers[-1]['reasoningEffort']==decisions[-1]['effort']
                assert received[before]['reasoning_effort']==decisions[-1]['effort']
                print('Desktop session preserves Context projections and Adaptive Reasoning request effort',flush=True)

            assert sid in adapter.saved_chats('save',sid)
            assert sid not in adapter.saved_chats('unsave',sid)
            try:adapter.saved_chats('save','not-a-personal-chat');raise AssertionError('Wrong role accepted')
            except Exception as e:assert not isinstance(e,AssertionError)
            print('Actual desktop preset and saved-chat operations verified',flush=True)
            assert adapter.native_interactions,'Current product descriptor must advertise native interactions'
            interaction_frames=[];interaction_failures=[]
            stream=adapter.stream_type(adapter,sid,interaction_frames.append,interaction_failures.append)
            stream.start()
            try:
                assert stream.interactions is not None
                stream.interactions.poll()
                assert adapter.interactions is stream.interactions
                assert not interaction_failures,interaction_failures
            finally:stream.close()
            assert adapter.interactions is None
            # The same session must be claimable immediately after clean release.
            stream=adapter.stream_type(adapter,sid,interaction_frames.append,interaction_failures.append)
            stream.start();stream.close()
            assert not interaction_failures,interaction_failures
            print('Native DSH interaction stream claimed, polled, released and reconnected',flush=True)
            if os.environ.get('AUGMENTOR_PROOF_APPROVALS'):
                from proof_dsh_approvals import prove
                prove(adapter,sid,until)
            if os.environ.get('AUGMENTOR_PROOF_INTERACTIONS'):
                frames=[];failures=[]
                stream=adapter.stream_type(adapter,sid,frames.append,failures.append);stream.start()
                try:
                    before_question=len(received)
                    adapter.call('session.prompt',{'sessionId':sid,'mode':'queue','content':[{'type':'text','text':'native question fixture'}]})
                    until(lambda:any(f.get('method')=='question/requested' for f in frames) or failures)
                    assert not failures,failures
                    question=next(f for f in frames if f.get('method')=='question/requested')
                    assert question['payload']['questions'][0]['id']=='choice',question
                    from augmentor_linux.window import Window
                    from PySide6.QtWidgets import QDialogButtonBox
                    from augmentor_linux.question_dialog import QuestionDialog
                    from PySide6.QtCore import QTimer
                    from types import SimpleNamespace
                    question_window=Window();question_window.show()
                    answers=[]
                    def answer_question(frame,value):
                        answers.append(value);adapter.respond(frame['rpcId'],value)
                    question_window.controller=SimpleNamespace(answer=answer_question,stop=lambda:None)
                    def fill_question():
                        active=app.activeModalWidget()
                        if not isinstance(active,QuestionDialog):return
                        active.options.item(1).setSelected(True)
                        active.grab().save(str(ROOT/'outputs/dsh-question-dialog.png'))
                        buttons=active.findChild(QDialogButtonBox)
                        QTest.mouseClick(buttons.button(QDialogButtonBox.StandardButton.Ok),Qt.MouseButton.LeftButton)
                    question_timer=QTimer();question_timer.setInterval(50);question_timer.timeout.connect(fill_question);question_timer.start()
                    watchdog=QTimer();watchdog.setSingleShot(True)
                    watchdog.timeout.connect(lambda:app.activeModalWidget().reject() if app.activeModalWidget() else None)
                    watchdog.start(5000)
                    try:question_window.on_interaction(question)
                    finally:
                        question_timer.stop();watchdog.stop();question_window.controller=None;question_window.close()
                    assert len(answers)==1 and answers[0]['answer']['answers'][0]['selected']==['Beta'],answers
                    until(lambda:len(received)>before_question+1 and not next(r for r in adapter.call('session.list')['items'] if r['sessionId']==sid)['running'])
                    assert any('Beta' in str(m) for m in received[-1]['messages'] if m['role']=='tool'),received[-1]
                    print('Actual DSH question answered through Qt dialog and returned to model',flush=True)
                finally:stream.close()
        else:
            assert tools==desktop_tools, 'Personal surfaces must have identical tools'
            assert len(received)>before+1
            assert any('SHARED SURFACE VERIFIED' in str(m) for m in received[-1]['messages'] if m['role']=='tool'),received[-1]
            assert adapter.saved_chats('save',sid) and sid in adapter.saved_chats()
            adapter.saved_chats('unsave',sid)
            assert (home/'.agent-presets/augmentor-linux-product/agent.cordis.yml').read_text()==(home/'.agent-presets/augmentor-browser-product/agent.cordis.yml').read_text()
            print('Both surfaces share the exact preset composition, model-facing tools and saved chats; Browser read a workspace file',flush=True)
    if os.environ.get('AUGMENTOR_PROOF_APPROVALS'):
        subprocess.run(['node',str(ROOT/'tests/fixtures/shared-browser-client.mjs')],env={**os.environ,'DSH_AUGMENTOR_URL':base},check=True,timeout=90)
    if os.environ.get('AUGMENTOR_PROOF_EXACT_FORK'):
        from dsh.branch import history
        from dsh.setup import http
        source='setup-linux'
        first=history(adapter.call,source)
        cutoff=next(e['seq'] for e in reversed(first) if e['type']=='turn/end')
        before=len(received)
        adapter.call('session.prompt',{'sessionId':source,'mode':'queue','content':[{'type':'text','text':'Input to replace in an exact edit.'}]})
        until(lambda:len(received)>before and not next(r for r in adapter.call('session.list')['items'] if r['sessionId']==source)['running'])
        parent=history(adapter.call,source)
        message=next(e for e in reversed(parent) if e['type']=='user/message' and e['data'].get('source',{}).get('kind','user')=='user')
        result=adapter.call('session.branch',{'sessionId':source,'newSessionId':'exact-edit-fixture','messageSeq':message['seq'],'mode':'edit'})
        child=result['sessionId'];child_events=history(adapter.call,child)
        assert child_events[:cutoff+1]==parent[:cutoff+1]
        assert not any('Input to replace' in str(e) for e in child_events)
        assert history(adapter.call,source)==parent
        adapter.call('session.selectModel',{'sessionId':child,'provider':'fixture','model':'fixture'})
        before=len(received)
        adapter.call('session.prompt',{'sessionId':child,'mode':'queue','content':[{'type':'text','text':'Exact edited replacement.'}]})
        until(lambda:len(received)>before and not next(r for r in adapter.call('session.list')['items'] if r['sessionId']==child)['running'])
        assert 'Exact edited replacement.' in str(received[-1]['messages'])
        assert 'Input to replace' not in str(received[-1]['messages'])
        print('Exact DSH prefix fork and subsequent model continuation verified',flush=True)
        from dsh.branch import branch,product_exact_fork,BranchError
        create=product_exact_fork(base,home);created=[]
        def lose_ack(params):
            result=create(params);created.append(result['sessionId'])
            raise TimeoutError('Injected lost acknowledgement after real child creation')
        for target in ('lost-exact-fixture','lost-exact-fixture-retry'):
            try:
                branch(adapter.call,{'sessionId':source,'newSessionId':target,'messageSeq':message['seq'],'mode':'edit'},
                       surface='linux',endpoint=base,exact_fork=lose_ack)
                raise AssertionError('Unknown outcome was accepted or replayed')
            except BranchError as error:
                assert 'not be replayed' in str(error) or 'unknown' in str(error),error
        assert len(created)==1
        assert created[0] in {row['sessionId'] for row in adapter.call('session.list')['items']}
        assert history(adapter.call,source)==parent
        print('Lost acknowledgement after real exact child creation was not replayed',flush=True)
    if os.environ.get('AUGMENTOR_PROOF_BROWSER'):
        browser_env={**os.environ,'AUGMENTOR_PROOF_DSH_SETUP_ONLY':'1'}
        with (ROOT/'outputs/browser-dsh-setup-proof.log').open('w') as browser_log:
            subprocess.run([sys.executable,str(ROOT/'scripts/browser-composable-proof.py')],env=browser_env,stdout=browser_log,stderr=browser_log,check=True,timeout=150)
        print('Actual Chromium DSH setup and shared browser features verified',flush=True)
    if os.environ.get('AUGMENTOR_PROOF_NATIVE_REPLY'):
        reply_env={**os.environ,'AUGMENTOR_PROOF_REQUIRE_STREAM':'1'};reply_env.pop('AUGMENTOR_DSH_AUTH_TOKEN',None)
        with (ROOT/'outputs/dsh-native-reply-proof.log').open('w') as reply_log:
            subprocess.run([sys.executable,str(ROOT/'scripts/dsh-reply-proof.py')],env=reply_env,stdout=reply_log,stderr=reply_log,check=True,timeout=200)
        print('Native Qt saved/final reply recovery verified without a login URL; inspect streamObserved separately',flush=True)
    evidence={'fixture':str(work),'appRoot':str(APP),'adapterFile':loaded_adapter.__file__,'platform':sys.platform,'model':'deterministic local fixture','qtInstall':True,'modelPickerAdapter':bool(picker),'modelPickerUi':bool(picker and os.environ.get('AUGMENTOR_PROOF_PICKER_UI')),'checkedSave':True,'profilePreserved':True,'linuxSavedChats':True,'sharedPersonalAgent':True,'modelRequests':len(received),'wikiToolAndSkillWorkflow':bool(wiki_modules),'contextAndAdaptiveWorkflow':bool(host_plugins),'freeWebSearchWorkflow':bool(web_provider)}
    (ROOT/'outputs/dsh-setup-proof.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence),flush=True)
finally:
    stop();log.close();server.shutdown();server.server_close()
    try:
        descriptor=prompts.call('host.describe');os.kill(descriptor['pid'],signal.SIGTERM)
    except Exception:pass
