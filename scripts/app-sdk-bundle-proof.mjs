// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Synthetic registration/native protocol proof. No service start or provider request.
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,rmSync,realpathSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve,isAbsolute} from 'node:path';
import {spawn,execFileSync} from 'node:child_process';
import {randomUUID} from 'node:crypto';

const product=process.argv[2]&&resolve(process.argv[2]);
if(!product||!existsSync(join(product,'scripts/app-sdk-launch.py')))throw Error('Provide a compatible built Augmentor runtime root');
if(process.platform==='win32'&&process.env.AUGMENTOR_EPHEMERAL_WINDOWS_RUNNER!=='1')throw Error('Windows bundle qualification requires a disposable runner');
const bundled=join(product,process.platform==='win32'?'python/python.exe':'python/bin/python3');
const python=existsSync(bundled)?bundled:process.env.AUGMENTOR_PYTHON||execFileSync('python3',['-I','-B','-c','import sys; print(sys.executable)'],{encoding:'utf8'}).trim();
assert.ok(isAbsolute(python));
const work=realpathSync(mkdtempSync(join(tmpdir(),'sdk-bundle-'))),app=join(work,'application with spaces'),data=join(work,'data');
const profiles=join(work,'profiles'),dsh=join(work,'dsh');
const env={...process.env,AUGMENTOR_PYTHON:python,AUGMENTOR_PI_NODE:process.execPath,AUGMENTOR_WORKSPACE_PROFILES:profiles,
 DSH_HOME:dsh,XDG_CONFIG_HOME:join(work,'config'),XDG_DATA_HOME:data,XDG_STATE_HOME:join(work,'state'),XDG_RUNTIME_DIR:join(work,'run'),PYTHONDONTWRITEBYTECODE:'1'};
const run=(script,args=[])=>execFileSync(python,['-I','-B',join(product,'scripts',script),...args],{env,encoding:'utf8',timeout:20000,windowsHide:true});
let child,closed;
try{
 mkdirSync(app);mkdirSync(join(data,'augmentor'),{recursive:true});
 writeFileSync(join(data,'augmentor/desktop.json'),JSON.stringify({root:product,node:process.execPath,python}));
 const runtime=JSON.parse(run('app-sdk-runtime.py',['--describe']));
 assert.equal(realpathSync(runtime.root),realpathSync(product));assert.ok(isAbsolute(runtime.node));assert.equal(runtime.platform,process.platform);
 const token=join(profiles,'fixture.token');run('app-sdk-private.py',['token',token]);const before=readFileSync(token);run('app-sdk-private.py',['token',token]);assert.deepEqual(readFileSync(token),before);
 const role=join(app,'role.md'),module=join(app,'tools.mjs');writeFileSync(role,'SYNTHETIC_SDK_BUNDLE_ROLE');writeFileSync(module,'export async function apply() {}\n');
 const preset=join(dsh,'.agent-presets/augmentor-browser-product');mkdirSync(preset,{recursive:true});
 writeFileSync(join(preset,'agent.cordis.yml'),JSON.stringify([{id:'persona',name:'fixture-persona',config:{prefix:'SYNTHETIC_BASE_ROLE'}}]));
 const profile={schemaVersion:1,sdkProtocol:'augmentor-app/1',harness:'dsh',id:'bundle-fixture',name:'Synthetic bundle fixture',preset:'augmentor-bundle-fixture',cwd:app,
  memory:{person:'synthetic-owner',project:'synthetic-project'},parentOrigin:'http://127.0.0.1:9876',publicPath:'/augmentor/',accessTokenFile:token,
  instructions:[role],tools:[{id:'fixture-tools',module,names:['fixture_read'],config:{}}],policy:{tools:['fixture_read'],voice:false,sharedSettings:false}};
 const input=join(app,'profile.json');writeFileSync(input,JSON.stringify(profile));run('app-sdk-launch.py',['register',input]);
 const installed=JSON.parse(readFileSync(join(profiles,profile.id+'.json')));assert.equal(installed.cwd,app);assert.equal(installed.harness,'dsh');
 const composition=JSON.parse(readFileSync(join(dsh,'.agent-presets',profile.preset,'agent.cordis.yml')));
 assert.match(composition.find(row=>row.id==='persona').config.prefix,/SYNTHETIC_SDK_BUNDLE_ROLE/);
 assert.ok(composition.some(row=>row.id==='augmentor-workspace-policy'));
 child=spawn(python,['-I','-B',join(product,'scripts/app-sdk-launch.py'),'native'],{env:{...env,AUGMENTOR_WORKSPACE_PROFILE:profile.id},stdio:['pipe','pipe','pipe'],windowsHide:true});
 let nativeErrors='';child.stderr.on('data',chunk=>{nativeErrors=(nativeErrors+String(chunk)).slice(-8192)});
 closed=new Promise((resolve,reject)=>{child.on('error',reject);child.on('exit',code=>resolve(code));});
 let buffer=Buffer.alloc(0);const pending=new Map();
 child.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const n=buffer.readUInt32LE(0);assert.ok(n>0&&n<=20*1024*1024);if(buffer.length<n+4)return;const frame=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);pending.get(frame.id)?.(frame);pending.delete(frame.id);}});
 const call=(method,params={})=>new Promise((resolve,reject)=>{
  const id=randomUUID(),timer=setTimeout(()=>{pending.delete(id);reject(Error('Native response was lost; no request was replayed. '+nativeErrors));},10000);
  pending.set(id,frame=>{clearTimeout(timer);resolve(frame);});const body=Buffer.from(JSON.stringify({id,method,params})),header=Buffer.alloc(4);header.writeUInt32LE(body.length);child.stdin.write(Buffer.concat([header,body]));
 });
 const description=(await call('workspace.describe',{protocol:'augmentor-app/1'})).result;
 assert.equal(description.profile,profile.id);assert.equal(description.harness,'dsh');assert.deepEqual(description.tools,['fixture_read']);assert.equal(description.features['shared-settings'].state,'denied');
 assert.ok((await call('augmentor/handshake',{protocol:description.productProtocol,version:description.productVersion})).result);
 assert.equal((await call('augmentor/codex',{action:'profiles'})).error.code,'PERMISSION_DENIED');
 assert.ok((await call('harness.select',{harness:'codex'})).error);
 child.stdin.end();const timeout=setTimeout(()=>child.kill(),5000);let code;try{code=await closed;}finally{clearTimeout(timeout);}assert.equal(code,0);child=null;
 console.log(JSON.stringify({passed:true,platform:process.platform,packagedRuntime:existsSync(join(product,'release.json')),registration:true,role:true,privateTokenPreserved:true,nativeDescription:true,sharedAdministrationDenied:true,explicitHarness:true,naturalExit:true,providerRequests:0}));
}finally{
 if(child){child.kill();await closed.catch(()=>{});}
 rmSync(work,{recursive:true,force:true});
}
