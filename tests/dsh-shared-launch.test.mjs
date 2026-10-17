// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {test} from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {once} from 'node:events';
import {mkdir,readFile,writeFile} from 'node:fs/promises';import {join} from 'node:path';import {createHash} from 'node:crypto';
import {root,py,exec,sharedFixture} from './fixtures/shared-profile-runtime.mjs';

async function fixture(t){
 const f=await sharedFixture(t,'target-processed'),home=join(f.base,'home'),data=join(f.base,'data'),config=join(f.base,'config'),state=join(f.base,'os-state'),cwd=join(f.base,'working folder with spaces');
 for(const p of [home,data,config,state,cwd])await mkdir(p,{mode:0o700});
 const preload=join(f.base,'privacy-preload.cjs');await writeFile(preload,"global.__authoredDshPrivacyPreload='KEPT';\n");
 const env={PATH:process.env.PATH,LANG:'C.UTF-8',HOME:home,XDG_DATA_HOME:data,XDG_CONFIG_HOME:config,XDG_STATE_HOME:state,XDG_RUNTIME_DIR:join(f.base,'run'),AUGMENTOR_SHARED_STATE:f.source.state,AUGMENTOR_SHARED_DATA:f.source.data,DSH_HOME:join(f.base,'existing-dsh-home'),DSH_TELEMETRY_MODE:'DISABLED',AUGMENTOR_PYTHON:py,PYTHONDONTWRITEBYTECODE:'1',NODE_OPTIONS:'--require '+JSON.stringify(preload),AUTHORED_SERVICE_SETTING:'KEEP_EXISTING_SERVICE_SETTING',PYTHONPATH:'/authored/keep-original-pythonpath'};
 const install="import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('dsh_launch_installer',Path(sys.argv[1])/'scripts/install-desktop-startup.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.install(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]),enable=False)";
 await exec(py,['-I','-B','-c',install,root,py,process.execPath],{env});
 const descriptor=join(data,'augmentor/desktop.json'),selected=JSON.parse(await readFile(descriptor));selected.sharedProfile={state:f.target.state,data:f.target.data};await writeFile(descriptor,JSON.stringify(selected),{mode:0o600});
 const command=join(f.base,'dsh');await writeFile(command,`// Independently authored process fixture, not DSH or private source.
console.log(JSON.stringify({argv:process.argv.slice(2),cwd:process.cwd(),data:process.env.AUGMENTOR_SHARED_DATA,state:process.env.AUGMENTOR_SHARED_STATE,python:process.env.AUGMENTOR_PYTHON,node:process.env.AUGMENTOR_PI_NODE,dshHome:process.env.DSH_HOME,telemetry:process.env.DSH_TELEMETRY_MODE,path:process.env.PATH,pythonPath:process.env.PYTHONPATH,preload:global.__authoredDshPrivacyPreload,custom:process.env.AUTHORED_SERVICE_SETTING}));
process.stdin.resume();process.stdin.on('end',()=>process.exit(0));
`);
 const probe="import importlib.util,json,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('dsh_launch_probe',Path(sys.argv[1])/'scripts/shared-launch-profile.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);\nif sys.argv[2]=='clients':m.assert_no_clients(json.loads(sys.argv[3]))\nelse:\n with m.launch_lease(Path(sys.argv[3]),exclusive=True):print('AUTHORED_WRITER_READY')";
 const inspect=(kind,value)=>exec(py,['-I','-B','-c',probe,root,kind,typeof value==='string'?value:JSON.stringify(value)],{env});
 const start=async(managed=true,desktop=false)=>{
  const args=[process.execPath,command,'web','--host','127.0.0.1','--port','1','--no-open','--authored','one argument with spaces'];
  const child=managed?spawn(py,['-I','-B',join(data,desktop?'augmentor/desktop-launch.py':'augmentor/desktop-dsh-launch.py'),...(desktop?['--dsh']:[]),...args],{cwd,env,stdio:['pipe','pipe','pipe']}):spawn(args[0],args.slice(1),{cwd,env,stdio:['pipe','pipe','pipe']});
  let errors='',buffer='';child.stderr.on('data',b=>errors+=b);const closed=once(child,'close');
  const stop=async()=>{if(child.exitCode===null&&child.signalCode===null)child.stdin.end();await closed;};t.after(stop);
  const ready=new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Authored DSH wrapper readiness: '+errors)),10000);child.stdout.on('data',b=>{buffer+=b;if(!buffer.includes('\n'))return;clearTimeout(timer);resolve(JSON.parse(buffer.slice(0,buffer.indexOf('\n'))));});child.once('exit',code=>{clearTimeout(timer);if(!buffer.includes('\n'))reject(Error('Authored DSH wrapper exited '+code+': '+errors));});});
  return {child,args,report:await ready,stop,errors:()=>errors};
 };
 const fingerprints=async()=>{const rows=[];for(const pair of [f.source,f.target])for(const name of ['prompts.sqlite3','memory.sqlite3','dual-memory.sqlite3'])rows.push(createHash('sha256').update(await readFile(join(pair.data,name))).digest('hex'));return rows;};
 return {...f,home,data,env,cwd,inspect,start,fingerprints};
}

test('managed DSH wrapper preserves the explicit command, privacy preload and service environment while selecting the shared pair',{skip:process.platform!=='linux',timeout:25000},async t=>{
 const f=await fixture(t),before=await f.fingerprints();
 for(const desktop of [false,true]){
 const peer=await f.start(true,desktop);
 assert.deepEqual(peer.report.argv,peer.args.slice(2));assert.equal(peer.report.cwd,f.cwd);assert.equal(peer.report.preload,'KEPT');assert.equal(peer.report.dshHome,f.env.DSH_HOME);assert.equal(peer.report.telemetry,'DISABLED');assert.equal(peer.report.path,f.env.PATH);assert.equal(peer.report.pythonPath,f.env.PYTHONPATH);assert.equal(peer.report.custom,f.env.AUTHORED_SERVICE_SETTING);assert.equal(peer.report.python,py);assert.equal(peer.report.node,process.execPath);assert.equal(peer.report.state,f.target.state);assert.equal(peer.report.data,f.target.data);
 await assert.rejects(()=>f.inspect('writer',join(f.data,'augmentor')),e=>e.stderr.includes('managed client is active'));
 await assert.rejects(()=>f.inspect('clients',[f.target]),e=>e.stderr.includes('Close existing Native, Browser, Harness and companion callers'));
 await peer.stop();assert.equal(peer.child.exitCode,0,peer.errors());assert.equal((await f.inspect('writer',join(f.data,'augmentor'))).stdout.trim(),'AUTHORED_WRITER_READY');assert.deepEqual(await f.fingerprints(),before);
 }
 t.diagnostic('Real generated direct and desktop-delegated Python wrapper/exec/leases; independently authored idle process identity, not an actual upstream DSH backend. Both store byte sets unchanged.');
});

test('cold scanner refuses an unmanaged idle DSH web identity without any companion, and releases after that process exits',{skip:process.platform!=='linux',timeout:25000},async t=>{
 const f=await fixture(t),peer=await f.start(false);assert.equal(peer.report.data,f.source.data);
 await assert.rejects(()=>f.inspect('clients',[f.source]),e=>e.stderr.includes('Close existing Native, Browser, Harness and companion callers'));
 // A legacy server does not inherit the managed launch reader. The process
 // scan is necessary; a successful reader probe alone cannot prove coldness.
 assert.equal((await f.inspect('writer',join(f.data,'augmentor'))).stdout.trim(),'AUTHORED_WRITER_READY');
 await peer.stop();await f.inspect('clients',[f.source]);assert.equal(peer.child.exitCode,0,peer.errors());
});

test('invalid managed DSH commands fail without echoing private argv or changing either store',{skip:process.platform!=='linux',timeout:15000},async t=>{
 const f=await fixture(t),before=await f.fingerprints(),selected=await readFile(join(f.data,'augmentor/desktop.json'));
 for(const command of ['relative-private-command',join(f.base,'private-missing-command')]){
  await assert.rejects(()=>exec(py,['-I','-B',join(f.data,'augmentor/desktop-dsh-launch.py'),command,'web','--token','AUTHORED_DO_NOT_LOG'],{env:f.env}),e=>e.stdout===''&&e.stderr.includes('Augmentor DSH launch failed')&&!e.stderr.includes(command)&&!e.stderr.includes('AUTHORED_DO_NOT_LOG'));
 }
 assert.deepEqual(await readFile(join(f.data,'augmentor/desktop.json')),selected);assert.deepEqual(await f.fingerprints(),before);
});

test('managed DSH lifetime blocks profile maintenance after exec and refuses an unfinished configuration fence',{skip:process.platform!=='linux',timeout:15000},async t=>{
 const f=await fixture(t),peer=await f.start(true),before=await f.fingerprints();
 const code="import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('authored_profile_gate',Path(sys.argv[1])/'dsh-profile-gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);\nwith m.lease(Path(sys.argv[2]),exclusive=True):print('AUTHORED_WRITER_READY')";
 const gate=()=>exec(py,['-I','-B','-c',code,join(f.data,'augmentor'),f.env.DSH_HOME],{env:f.env});
 await assert.rejects(gate,e=>e.stderr.includes('managed DSH host or configuration maintenance is active'));
 await peer.stop();assert.equal((await gate()).stdout.trim(),'AUTHORED_WRITER_READY');
 await writeFile(join(f.env.DSH_HOME,'.augmentor-preservation.json'),'{"authored":"UNFINISHED_PRIVATE_TRANSACTION"}',{mode:0o600});
 await assert.rejects(()=>f.start(true),e=>e.message.includes('Augmentor DSH launch failed')&&!e.message.includes('UNFINISHED_PRIVATE_TRANSACTION'));
 assert.deepEqual(await f.fingerprints(),before);
});
