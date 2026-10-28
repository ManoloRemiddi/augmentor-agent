// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {mkdtemp,cp,mkdir,readFile,writeFile,readdir,stat,readlink,rm} from 'node:fs/promises';import {join,resolve,relative,dirname} from 'node:path';import {tmpdir} from 'node:os';import {createHash} from 'node:crypto';import {execFile} from 'node:child_process';import {promisify} from 'node:util';
import {planFixture,until} from './plans.mjs';
import {pythonExecutable} from '../../dist/platform/src/index.js';
const exec=promisify(execFile),source=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.'),hash=b=>createHash('sha256').update(b).digest('hex');
export async function managedReviewFixture(t){
 const base=await mkdtemp(join(tmpdir(),'augmentor-review-seal-')),release=join(base,'releases','authored');await mkdir(release,{recursive:true,mode:0o700});
 let f;const hooks=[];t.after(async()=>{
  if(f){await f.stop();const owned=async()=>{const ids=[];for(const id of await readdir('/proc')){if(!/^\d+$/.test(id))continue;try{const env=Object.fromEntries((await readFile('/proc/'+id+'/environ','utf8')).split('\0').filter(s=>s.includes('=')).map(s=>[s.slice(0,s.indexOf('=')),s.slice(s.indexOf('=')+1)]));if(env.AUGMENTOR_PI_STATE===f.state||env.AUGMENTOR_SHARED_STATE===f.env.AUGMENTOR_SHARED_STATE){if(!(await readFile('/proc/'+id+'/stat','utf8')).includes(') Z '))ids.push(Number(id));}}catch(error){if(!['ENOENT','ESRCH','EACCES'].includes(error.code))throw error;}}return ids;};
   // Only independently authored temporary profiles belong to this cleanup.
   for(const id of await owned())try{process.kill(id,'SIGTERM');}catch(error){if(error.code!=='ESRCH')throw error;}await until(async()=>!(await owned()).length,'temporary review and companion processes stopped');
  }for(const hook of hooks)await hook();await rm(base,{recursive:true,force:true,maxRetries:5,retryDelay:100});
 });
 for(const name of ['dist','apps','services','scripts','config','release','adapters'])await cp(join(source,name),join(release,name),{recursive:true,verbatimSymlinks:true,filter:p=>!p.split('/').some(segment=>['node_modules','__pycache__','.git'].includes(segment))});
 for(const name of ['package.json','package-lock.json'])await cp(join(source,name),join(release,name));
 const lock=JSON.parse(await readFile(join(source,'package-lock.json'))),top=new Set();
 for(const [name,pkg] of Object.entries(lock.packages)){if(!name.startsWith('node_modules/')||pkg.dev)continue;const parts=name.split('/');top.add(parts.slice(1,parts[1].startsWith('@')?3:2).join('/'));}
 for(const name of top){try{await stat(join(source,'node_modules',name));}catch(error){if(error.code==='ENOENT')continue;throw error;}const target=join(release,'node_modules',name);await mkdir(dirname(target),{recursive:true});await cp(join(source,'node_modules',name),target,{recursive:true,verbatimSymlinks:true});}
 await mkdir(join(release,'node/bin'),{recursive:true});await cp(process.execPath,join(release,'node/bin/node'));await writeFile(join(release,'node/NOTICE'),'Authored internal qualification copy; not a distribution.\n');
 const files={};async function inventory(dir){for(const name of (await readdir(dir)).sort()){const path=join(dir,name),s=await (await import('node:fs/promises')).lstat(path);if(s.isSymbolicLink())files[relative(release,path)]='link:'+await readlink(path);else if(s.isDirectory())await inventory(path);else files[relative(release,path)]=hash(await readFile(path));}}await inventory(release);
 // Python's JSON separators own the normal deployment inventory identity.
 const python=pythonExecutable(),encoded=JSON.stringify(files);
 // execFile has no stdin option; use a short private file for this exact map.
 const inventoryPath=join(base,'inventory.json');await writeFile(inventoryPath,encoded,{mode:0o600});const {stdout}=await exec(python,['-c','import json,hashlib,sys;print(hashlib.sha256(json.dumps(json.load(open(sys.argv[1])),sort_keys=True).encode()).hexdigest())',inventoryPath]);
 const deployment={root:release,node:join(release,'node/bin/node'),python,version:JSON.parse(await readFile(join(source,'release/product.json'))).version,releaseId:'authored-review-seal',sourceRef:'independently-authored-test-assembly',artifactSha256:stdout.trim()};
 await writeFile(join(release,'desktop-release.json'),JSON.stringify({deployment,files,artifactSha256:deployment.artifactSha256}),{mode:0o600});
 const prior=process.env.AUGMENTOR_PI_TEST_ROOT;process.env.AUGMENTOR_PI_TEST_ROOT=release;try{f=await planFixture({after:fn=>hooks.push(fn)},{policy:'read-only'});}finally{if(prior===undefined)delete process.env.AUGMENTOR_PI_TEST_ROOT;else process.env.AUGMENTOR_PI_TEST_ROOT=prior;}
 const profile={config:f.config,state:f.state,socket:join(f.state,'runtime.sock'),sharedState:f.env.AUGMENTOR_SHARED_STATE,sharedData:f.env.AUGMENTOR_SHARED_DATA,workspace:f.workspace,runtimeDir:f.env.XDG_RUNTIME_DIR,xdgConfigHome:f.env.XDG_CONFIG_HOME,xdgDataHome:f.env.XDG_DATA_HOME,xdgStateHome:f.env.XDG_STATE_HOME,port:0,llamaCppProviders:'',linuxTools:false};
 const input=join(f.root,'review-profile.json'),registry=join(f.root,'reviews');await writeFile(input,JSON.stringify(profile),{mode:0o600});
 const invoke=(tool,args,env)=>exec(python,[tool,'--registry',registry,...args],{env:{...f.env,...env},timeout:85000});
 const run=(args,env={})=>invoke(join(source,'scripts/harness-review.py'),args,env),runSealed=(args,env={})=>invoke(join(release,'scripts/harness-review.py'),args,env);
 return {...f,base,release,deployment,profile,input,registry,run,runSealed};
}
