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
