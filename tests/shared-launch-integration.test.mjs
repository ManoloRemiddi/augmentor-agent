// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real installed launcher code, Native Messaging host and shared companions;
// independently authored data, no owner profile or model calls.
import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {once} from 'node:events';
import {readFile,writeFile,mkdir} from 'node:fs/promises';import {join} from 'node:path';
import {root,py,exec,sharedFixture,companion,companionCall,query} from './fixtures/shared-profile-runtime.mjs';

test('actual installed Browser launcher reads the selected pair, keeps its lifetime gate through exec and reopens the selected service',{skip:process.platform!=='linux',timeout:45000},async t=>{
 const f=await sharedFixture(t,'target-processed'),dataHome=join(f.base,'installed-data'),home=join(f.base,'home'),config=join(f.base,'config'),state=join(f.base,'os-state');for(const p of [dataHome,home,config,state])await mkdir(p,{mode:0o700});
 const env={PATH:process.env.PATH,LANG:'C.UTF-8',HOME:home,XDG_DATA_HOME:dataHome,XDG_CONFIG_HOME:config,XDG_STATE_HOME:state,XDG_RUNTIME_DIR:join(f.base,'run'),AUGMENTOR_SHARED_STATE:f.source.state,AUGMENTOR_SHARED_DATA:f.source.data,PYTHONDONTWRITEBYTECODE:'1',AUGMENTOR_PYTHON:py,AUGMENTOR_PI_NO_AUTOSTART:'1',AUGMENTOR_DESKTOP_NO_AUTOSTART:'1',DSH_HOME:join(f.base,'dsh'),DSH_AUGMENTOR_URL:'http://127.0.0.1:1',NODE_OPTIONS:'--require /authored-never-load-this-file',NODE_PATH:'/authored-never-load-this-path'};
 const install="import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('authored_launch_installer',Path(sys.argv[1])/'scripts/install-desktop-startup.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.install(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]),enable=False,register_browser=True)";
 await exec(py,['-I','-B','-c',install,root,py,process.execPath],{env});
 const descriptor=join(dataHome,'augmentor','desktop.json'),selection=JSON.parse(await readFile(descriptor));selection.sharedProfile={state:f.target.state,data:f.target.data};await writeFile(descriptor,JSON.stringify(selection),{mode:0o600});
 // A bootstrap refresh must retain the logical user binding even for a source
 // selection. Existing host adoption is separately guarded, so no registration
 // is requested on this refresh.
 await exec(py,['-I','-B','-c',install.replace('register_browser=True','register_browser=False'),root,py,process.execPath],{env});assert.deepEqual(JSON.parse(await readFile(descriptor)).sharedProfile,selection.sharedProfile);
 const prompts=companion(t,f.target,'prompts'),memory=companion(t,f.target,'memory');const service=await prompts.ready();await memory.ready();
 const manifest=JSON.parse(await readFile(join(config,'chromium/NativeMessagingHosts/com.augmentor.agent.json')));assert.equal(manifest.path,join(home,'.local/bin/augmentor-browser-host-managed'));assert(!(await readFile(manifest.path,'utf8')).includes(root));
 let host,closed,serial=0,buffer=Buffer.alloc(0),errors='';const pending=new Map();
 const stop=async()=>{if(host?.exitCode===null&&host.signalCode===null)host.stdin.end();if(closed)await closed;};t.after(stop);
 const open=async()=>{buffer=Buffer.alloc(0);errors='';host=spawn(manifest.path,[],{env,stdio:['pipe','pipe','pipe']});closed=once(host,'close');host.stderr.on('data',b=>errors+=b);host.stdout.on('data',b=>{buffer=Buffer.concat([buffer,b]);while(buffer.length>=4){const n=buffer.readUInt32LE();assert(n<=1024*1024);if(buffer.length<n+4)break;const frame=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);const task=pending.get(frame.id);if(task){pending.delete(frame.id);clearTimeout(task.timer);frame.error?task.reject(Error(frame.error.message)):task.resolve(frame.result);}}});};
 const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial,timer=setTimeout(()=>{pending.delete(id);reject(Error('Managed Native Messaging fixture timeout: '+method+' '+errors));},10000);pending.set(id,{resolve,reject,timer});const body=Buffer.from(JSON.stringify({id,method,params})),header=Buffer.alloc(4);header.writeUInt32LE(body.length);host.stdin.write(Buffer.concat([header,body]));});
 const version=JSON.parse(await readFile(join(root,'apps/browser/extension/manifest.json'))).version;
 await open();assert.equal((await call('augmentor/handshake',{protocol:'augmentor/1',version})).version,version);let response=await call('augmentor/prompts',{action:'list'});assert.equal(response.ok,true,response.error);let library=response.library;assert(library.prompts.some(p=>p.content==='Authored target prompt.'));assert(!library.prompts.some(p=>p.content==='Authored source-only prompt.'));
 const probe="import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('shared_probe',Path(sys.argv[1])/'scripts/shared-launch-profile.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);\nwith m.launch_lease(Path(sys.argv[2]),exclusive=True): print('AUTHORED_WRITER_READY')";
 await assert.rejects(()=>exec(py,['-I','-B','-c',probe,root,join(dataHome,'augmentor')],{env}),e=>e.stderr.includes('managed client is active'));
 assert.equal((await call('augmentor/prompts',{action:'save',name:'selected-browser',content:'AUTHORED_MANAGED_BROWSER_WRITE'})).ok,true);assert((await companionCall(f.target,'prompts','prompts.list')).prompts.some(p=>p.name==='selected-browser'));assert.equal((await query(join(f.source.data,'prompts.sqlite3'),"SELECT id FROM prompts WHERE name='selected-browser'")).length,0);
 assert.equal((await companionCall(f.target,'prompts','host.describe')).pid,service.pid);await stop();assert.equal(host.exitCode,0,errors);assert.equal((await exec(py,['-I','-B','-c',probe,root,join(dataHome,'augmentor')],{env})).stdout.trim(),'AUTHORED_WRITER_READY');
 await prompts.stop();const replacement=companion(t,f.target,'prompts');assert.notEqual((await replacement.ready()).pid,service.pid);await open();await call('augmentor/handshake',{protocol:'augmentor/1',version});response=await call('augmentor/prompts',{action:'list'});assert.equal(response.ok,true,response.error);library=response.library;assert(library.prompts.some(p=>p.name==='selected-browser'));await stop();assert.equal(host.exitCode,0,errors);
 t.diagnostic('Generated managed host, actual version handshake/shared RPC, selected target-only write, inherited reader fence, closed-host release and controlled service/host reopen; no harness selection or model call.');
});

test('an actual companion using another state path is detected by data identity before a binding change',{skip:process.platform!=='linux',timeout:25000},async t=>{
 const f=await sharedFixture(t),alias={state:join(f.base,'legacy-other-state'),data:f.source.data};await mkdir(alias.state,{mode:0o700});const service=companion(t,alias,'prompts');await service.ready();
 const probe="import importlib.util,json,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('known_client_probe',Path(sys.argv[1])/'scripts/shared-launch-profile.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.assert_no_clients(json.loads(sys.argv[2]))";
 await assert.rejects(()=>exec(py,['-I','-B','-c',probe,root,JSON.stringify([f.source,f.target])]),e=>e.stderr.includes('Close existing Native, Browser, Harness and companion callers'));
 await service.stop();await exec(py,['-I','-B','-c',probe,root,JSON.stringify([f.source,f.target])]);
});

test('managed embedding keeps its selected-store reader while idle and serves that library without granting workspace writes',{skip:process.platform!=='linux',timeout:45000},async t=>{
 const {createServer}=await import('node:net'),{WebSocket}=await import('ws');
 const f=await sharedFixture(t,'target-processed'),home=join(f.base,'embed-home'),data=join(f.base,'embed-data'),config=join(f.base,'embed-config'),state=join(f.base,'embed-state'),profiles=join(config,'augmentor/workspaces');
 for(const p of [home,data,config,state,profiles])await mkdir(p,{recursive:true,mode:0o700});
 const env={PATH:process.env.PATH,LANG:'C.UTF-8',HOME:home,XDG_DATA_HOME:data,XDG_CONFIG_HOME:config,XDG_STATE_HOME:state,XDG_RUNTIME_DIR:join(f.base,'embed-run'),AUGMENTOR_SHARED_STATE:f.source.state,AUGMENTOR_SHARED_DATA:f.source.data,AUGMENTOR_WORKSPACE_PROFILES:profiles,AUGMENTOR_PYTHON:py,PYTHONDONTWRITEBYTECODE:'1',NODE_OPTIONS:'--require /authored-never-load-this-file',NODE_PATH:'/authored-never-load-this-path'};
 const install="import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('embedding_launch_installer',Path(sys.argv[1])/'scripts/install-desktop-startup.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.install(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]),enable=False)";
 await exec(py,['-I','-B','-c',install,root,py,process.execPath],{env});
 const descriptor=join(data,'augmentor/desktop.json'),selected=JSON.parse(await readFile(descriptor));selected.sharedProfile={state:f.target.state,data:f.target.data};await writeFile(descriptor,JSON.stringify(selected),{mode:0o600});
 const token='AUTHORED_EMBED_PROXY_'.repeat(3),origin='http://127.0.0.1:9999',profile={id:'fixture',name:'Authored fixture',preset:'augmentor-fixture',cwd:f.base,memory:{person:'fixture-owner',project:f.base},parentOrigin:origin,publicPath:'/augmentor/',accessTokenFile:join(profiles,'token'),sdkProtocol:'augmentor-app/1',schemaVersion:1,policy:{tools:[],voice:false,sharedSettings:false}};
 await writeFile(profile.accessTokenFile,token,{mode:0o600});await writeFile(join(profiles,'fixture.json'),JSON.stringify(profile),{mode:0o600});await writeFile(join(profiles,'index.json'),'["fixture"]',{mode:0o600});
 const prompts=companion(t,f.target,'prompts');await prompts.ready();
 const reservation=createServer();reservation.listen(0,'127.0.0.1');await once(reservation,'listening');env.AUGMENTOR_EMBED_PORT=String(reservation.address().port);await new Promise(r=>reservation.close(r));
 let errors='',output='';const child=spawn(py,['-I','-B',join(data,'augmentor/embed-launch.py')],{env,stdio:['ignore','pipe','pipe']}),closed=once(child,'close');child.stderr.on('data',b=>errors+=b);child.stdout.on('data',b=>output+=b);
 const stop=async()=>{if(child.exitCode===null&&child.signalCode===null)child.kill('SIGTERM');await closed;};t.after(stop);
 const deadline=Date.now()+10000;while(!output.includes('Augmentor embedding service ready')){assert.equal(child.exitCode,null,errors);assert(Date.now()<deadline,'Authored embedding startup deadline: '+errors);await new Promise(r=>setTimeout(r,20));}
 const probe="import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('embed_reader_probe',Path(sys.argv[1])/'scripts/shared-launch-profile.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);\nwith m.launch_lease(Path(sys.argv[2]),exclusive=True):print('AUTHORED_WRITER_READY')";
 // An idle server is already a potential writer: it must fence a binding change
 // even before the first websocket starts a Native Messaging child.
 await assert.rejects(()=>exec(py,['-I','-B','-c',probe,root,join(data,'augmentor')],{env}),e=>e.stderr.includes('managed client is active'));
 const inspectIdle="import importlib.util,json,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('idle_embed_probe',Path(sys.argv[1])/'scripts/shared-launch-profile.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.assert_no_clients(json.loads(sys.argv[2]))";
 await assert.rejects(()=>exec(py,['-I','-B','-c',inspectIdle,root,JSON.stringify([f.target])],{env}),e=>e.stderr.includes('Close existing Native, Browser, Harness and companion callers'));
 const headers={authorization:'Bearer '+token,origin},base='http://127.0.0.1:'+env.AUGMENTOR_EMBED_PORT+'/embed/fixture/';assert.equal((await fetch(base+'config.json')).status,403);assert.equal((await fetch(base+'config.json',{headers})).status,200);
 const ws=new WebSocket(base.replace('http:','ws:')+'native',{headers});t.after(()=>ws.terminate());await once(ws,'open');let id=0;const call=async(method,params={})=>{const message=once(ws,'message');ws.send(JSON.stringify({id:++id,method,params}));return JSON.parse((await message)[0]);};
 const version=JSON.parse(await readFile(join(root,'apps/browser/extension/manifest.json'))).version;assert.equal((await call('augmentor/handshake',{protocol:'augmentor/1',version})).result.version,version);
 const response=await call('augmentor/prompts',{action:'list'});assert.equal(response.result.ok,true,JSON.stringify(response.error));assert(response.result.library.prompts.some(p=>p.content==='Authored target prompt.'));assert(!response.result.library.prompts.some(p=>p.content==='Authored source-only prompt.'));
 assert.equal((await call('augmentor/prompts',{action:'save',name:'denied-workspace-write',content:'MUST_NOT_BE_SAVED'})).error.code,'PERMISSION_DENIED');assert.equal((await call('augmentor/memory',{action:'dual.settings'})).error.code,'PERMISSION_DENIED');
 for(const pair of [f.source,f.target])assert.equal((await query(join(pair.data,'prompts.sqlite3'),"SELECT id FROM prompts WHERE name='denied-workspace-write'")).length,0);
 ws.close();await once(ws,'close');await stop();assert.equal(child.exitCode,0,errors);assert.equal((await exec(py,['-I','-B','-c',probe,root,join(data,'augmentor')],{env})).stdout.trim(),'AUTHORED_WRITER_READY');
 t.diagnostic('Actual copied embedding launcher → SDK adapter → server → Native host; selected library, idle reader gate, proxy authentication and unchanged SDK write restrictions. No DSH/harness/model selection.');
});
