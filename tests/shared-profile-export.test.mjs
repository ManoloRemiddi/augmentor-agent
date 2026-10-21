// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import fs from 'node:fs';import {syncBuiltinESMExports} from 'node:module';
import {mkdir,writeFile,readFile,readdir,chmod,rm,symlink,link} from 'node:fs/promises';
import {join} from 'node:path';
import {createServer} from 'node:http';import {once} from 'node:events';
import {sharedFixture,modules,companion,companionCall,py,exec,root,query} from './fixtures/shared-profile-runtime.mjs';
const {inspectLegacySharedProfile,exportLegacySharedProfile}=await modules('shared-profile-export');
const {inspectSharedProfile,importSharedProfile}=await modules('shared-profile-import');
const {stateInventory,recoverStateTransaction}=await modules('profile-transaction');
const {acquireProfileLease}=await modules('profile-lease');
const options={skip:process.platform!=='linux',timeout:30000};
async function destination(f,name='dedicated'){const state=join(f.base,name+'-state'),data=join(f.base,name+'-data');await mkdir(state,{mode:0o700});return {state,data};}

test('cold export selects exact shared components from a populated mixed application root and preserves it through subsequent review consolidation',options,async t=>{
 const f=await sharedFixture(t,'target-processed'),source=f.target,target=await destination(f);
 await writeFile(join(source.data,'desktop.json'),'{"authored":"selected immutable application"}',{mode:0o600});
 await mkdir(join(source.data,'releases'),{mode:0o700});await writeFile(join(source.data,'releases','application.bin'),'AUTHORED_APPLICATION_BYTES');
 await writeFile(join(source.data,'unrelated-application.sqlite3'),'AUTHORED_NOT_A_SHARED_DATABASE');
 await writeFile(join(source.data,'hindsight-installation.json'),JSON.stringify({engineVolume:'/authored/external-volume',managedRelease:'authored-release'}),{mode:0o600});
 await chmod(join(f.base,'target'),0o755); // Legacy data may have an owned 0755 parent.
 const before=stateInventory(source.data),inspected=await inspectLegacySharedProfile(source),result=await exportLegacySharedProfile(source,target,inspected.sha256);
 assert.equal(result.transaction.backup,null,'An absent dedicated destination never replaces the mixed source');
 assert.equal(result.result.sourceRetained,true);assert.equal(result.result.applicationFilesCopied,false);assert.equal(result.result.externalEngineCopiedOrCalled,false);assert.equal(result.result.modelWorkSubmitted,false);
 assert.deepEqual((await readdir(target.data)).sort(),inspected.components.map(v=>v.name).sort());
 for(const row of inspected.components)assert.deepEqual(await readFile(join(target.data,row.name)),await readFile(join(source.data,row.name)));
 assert.equal(stateInventory(source.data).sha256,before.sha256);assert.equal((await inspectLegacySharedProfile(source)).sha256,inspected.sha256);
 const oldBanks=await query(join(target.data,'dual-memory.sqlite3'),'SELECT * FROM hindsight_banks'),oldJobs=await query(join(target.data,'dual-memory.sqlite3'),'SELECT * FROM memory_jobs');
 await importSharedProfile(f.source,target,inspectSharedProfile(f.source).sha256,{mapDefaultPerson:true});
 assert.deepEqual(await query(join(target.data,'dual-memory.sqlite3'),'SELECT * FROM hindsight_banks'),oldBanks);assert.deepEqual(await query(join(target.data,'dual-memory.sqlite3'),'SELECT * FROM memory_jobs'),oldJobs);
 assert.equal((await query(join(target.data,'dual-memory.sqlite3'),'SELECT * FROM settings'))[0].person,'target-person');assert.equal(stateInventory(source.data).sha256,before.sha256);
});

test('legacy export refuses active owners, changed components, journals and existing or overlapping destinations before publication',options,async t=>{
 const f=await sharedFixture(t),source=f.source,target=await destination(f),inspected=await inspectLegacySharedProfile(source);
 for(const kind of ['prompts','memory']){const peer=companion(t,source,kind);await peer.ready();await assert.rejects(()=>inspectLegacySharedProfile(source),/already owned/);await assert.rejects(()=>exportLegacySharedProfile(source,target,inspected.sha256),/already owned/);await peer.stop();}
 const held=acquireProfileLease(source.data,{maintenance:true});try{await assert.rejects(()=>inspectLegacySharedProfile(source),/already owned/);}finally{held.close();}
 // Service startup is allowed to add its own schema; take a new cold inspection.
 const cold=await inspectLegacySharedProfile(source);await writeFile(join(source.data,'hindsight.json'),'{}',{mode:0o600});
 await assert.rejects(()=>exportLegacySharedProfile(source,target,cold.sha256),/changed since inspection/);await rm(join(source.data,'hindsight.json'));
 await writeFile(join(source.data,'dual-memory.sqlite3-wal'),'AUTHORED_UNFLUSHED_JOURNAL');await assert.rejects(()=>inspectLegacySharedProfile(source),/cleanly stop SQLite/);await rm(join(source.data,'dual-memory.sqlite3-wal'));
 await assert.rejects(()=>exportLegacySharedProfile(source,{...target,data:join(source.data,'nested')},cold.sha256),/overlap/);
 await mkdir(target.data,{mode:0o700});const before=stateInventory(target.data);await assert.rejects(()=>exportLegacySharedProfile(source,target,cold.sha256),/new absent/);assert.equal(stateInventory(target.data).sha256,before.sha256);
});

test('legacy export rejects linked components, invalid schemas/configuration and evidence roots without copying application data',options,async t=>{
 const f=await sharedFixture(t),source=f.source,target=await destination(f),path=join(source.data,'hindsight.json');
 await symlink(join(source.data,'prompts.sqlite3'),path);await assert.rejects(()=>inspectLegacySharedProfile(source),/regular unlinked/);await rm(path);
 await link(join(source.data,'prompts.sqlite3'),path);await assert.rejects(()=>inspectLegacySharedProfile(source),/regular unlinked/);await rm(path);
 await writeFile(path,'{}',{mode:0o600});await chmod(path,0o644);await assert.rejects(()=>inspectLegacySharedProfile(source),/private owned/);await chmod(path,0o600);
 await writeFile(path,'[]',{mode:0o600});await assert.rejects(()=>inspectLegacySharedProfile(source),/JSON object/);await rm(path);
 await exec(py,['-I','-B','-c',"import sqlite3,sys;db=sqlite3.connect(sys.argv[1]);db.execute('CREATE TABLE future_source_table (id TEXT)');db.commit()",join(source.data,'dual-memory.sqlite3')]);
 await assert.rejects(()=>inspectLegacySharedProfile(source),/explicit migration adapter/);assert.equal(fs.existsSync(target.data),false);
 const archive=join(f.base,'shared-imports','a'.repeat(64),'data');await mkdir(archive,{recursive:true,mode:0o700});await assert.rejects(()=>inspectLegacySharedProfile({...source,data:archive}),/Evidence/);
});

test('a destination created during validation and source changed during copying both refuse publication without replacing new owner data',options,async t=>{
 const f=await sharedFixture(t),source=f.source,target=await destination(f),inspected=await inspectLegacySharedProfile(source);
 const operation=exportLegacySharedProfile(source,target,inspected.sha256);
 await mkdir(target.data,{mode:0o700});await writeFile(join(target.data,'another-owner.json'),'AUTHORED_NEW_OWNER',{mode:0o600});const fresh=stateInventory(target.data);
 await assert.rejects(operation,/new absent/);assert.equal(stateInventory(target.data).sha256,fresh.sha256);
 const other=await destination(f,'changed-source'),copy=fs.cpSync;let changed=false;
 fs.cpSync=(a,b,...args)=>{const result=copy(a,b,...args);if(String(b).endsWith('prompts.sqlite3')&&!changed){changed=true;fs.writeFileSync(join(source.data,'hindsight.json'),'{}',{mode:0o600});}return result;};syncBuiltinESMExports();
 try{await assert.rejects(()=>exportLegacySharedProfile(source,other,inspected.sha256),/changed before export publication/);}finally{fs.cpSync=copy;syncBuiltinESMExports();}
 assert(changed);assert.equal(fs.existsSync(other.data),false);assert.equal(stateInventory(target.data).sha256,fresh.sha256);
});

test('interrupted creation fences current startup and explicit recovery publishes verified export bytes without redoing extraction',options,async t=>{
 const f=await sharedFixture(t,'target-processed'),source=f.target,target=await destination(f),before=stateInventory(source.data),inspected=await inspectLegacySharedProfile(source),rename=fs.renameSync;
 fs.renameSync=(a,b)=>{if(b===target.data&&String(a).endsWith('.stage'))throw Error('Authored export publication interruption');return rename(a,b);};syncBuiltinESMExports();
 try{await assert.rejects(()=>exportLegacySharedProfile(source,target,inspected.sha256),/publication interruption/);}finally{fs.renameSync=rename;syncBuiltinESMExports();}
 assert.equal(fs.existsSync(target.data),false);const refused=companion(t,target,'memory');await refused.exit;assert.notEqual(refused.child.exitCode,0);assert.match(refused.errors(),/unfinished shared-profile migration/);assert.equal(fs.existsSync(target.data),false);
 assert.equal(recoverStateTransaction(target.data,'inspect').phase,'prepared');recoverStateTransaction(target.data,'finish');
 for(const row of inspected.components)assert.deepEqual(await readFile(join(target.data,row.name)),await readFile(join(source.data,row.name)));
 assert.equal(stateInventory(source.data).sha256,before.sha256);assert(inspectSharedProfile(target).sha256);
});

test('the actual CLI validates and exports cold authored databases without any IP networking or service startup',options,async t=>{
 const f=await sharedFixture(t,'target-processed'),source=f.target,target=await destination(f),manifest=join(f.base,'manifest.json'),trace=join(f.base,'network.log'),before=stateInventory(source.data);
 await writeFile(manifest,JSON.stringify({schema:'augmentor-shared-profile-input/1',source,target}),{mode:0o600});
 const command=['-f','-qq','-s','0','-e','trace=network','-o',trace,process.execPath,join(root,'scripts/import-shared-profile.mjs')];
 const inspection=JSON.parse((await exec('strace',[...command,'inspect-legacy',manifest],{env:{...process.env,AUGMENTOR_PYTHON:py,PYTHONDONTWRITEBYTECODE:'1'}})).stdout);
 await writeFile(manifest,JSON.stringify({schema:'augmentor-shared-profile-input/1',source,target,sourceSha256:inspection.sha256}),{mode:0o600});
 const exported=JSON.parse((await exec('strace',[...command,'export-legacy',manifest],{env:{...process.env,AUGMENTOR_PYTHON:py,PYTHONDONTWRITEBYTECODE:'1'}})).stdout);
 assert.equal(exported.result.sourceSha256,inspection.sha256);assert.equal(exported.result.modelWorkSubmitted,false);assert.equal(stateInventory(source.data).sha256,before.sha256);
 const network=await readFile(trace,'utf8');assert(!network.includes('AF_INET'),'Offline export must make no IPv4/IPv6 calls');assert(!network.includes('connect('),'Offline export must not call any companion or engine');
});

test('an exported populated store retains cached bank identity across actual Native reads, engine outage and companion restart',options,async t=>{
 const f=await sharedFixture(t,'target-processed'),source=f.target,target=await destination(f),requests=[];
 const engine=createServer((request,response)=>{requests.push({method:request.method,path:request.url});request.resume();response.writeHead(503,{'content-type':'application/json'}).end('{"error":"Authored unavailable engine"}');});
 engine.listen(0,'127.0.0.1');await once(engine,'listening');t.after(async()=>{engine.closeAllConnections();await new Promise(done=>engine.close(done));});
 const endpoint='http://127.0.0.1:'+engine.address().port;
 await writeFile(join(source.data,'hindsight.json'),JSON.stringify({endpoint,apiKey:'authored-not-a-secret'}),{mode:0o600});
 await exec(py,['-I','-B','-c',"import sqlite3,sys;db=sqlite3.connect(sys.argv[1]);db.execute('UPDATE hindsight_destination SET endpoint=?',(sys.argv[2],));db.commit()",join(source.data,'dual-memory.sqlite3'),endpoint]);
 const before=stateInventory(source.data),inspected=await inspectLegacySharedProfile(source);await exportLegacySharedProfile(source,target,inspected.sha256);
 const db=join(target.data,'dual-memory.sqlite3'),tables=['hindsight_banks','hindsight_outbox','hindsight_destination','memory_jobs','memory_budgets','memory_processing','events','sessions'],saved={};for(const table of tables)saved[table]=await query(db,'SELECT * FROM '+table);
 let memory=companion(t,target,'memory');const first=await memory.ready();assert.equal(first.person,'target-person');assert.equal(first.enabled,0);assert.equal(first.processing.paused,true);
 assert.deepEqual(await companionCall(target,'memory','memory.dual.recall',{session:'pi:target-chat'}),{enabled:false});
 // Explicit synthetic-only capture choice on the exported copy; source is retained.
 await companionCall(target,'memory','memory.dual.configure',{enabled:true,expectedEnabled:false});
 const recall=await companionCall(target,'memory','memory.dual.recall',{session:'pi:target-chat'});assert.equal(recall.person,'target-person');assert.equal(recall.project,'/authored/target-project');assert.match(recall.relationship.summary,/Authored cached relationship/);assert.match(recall.work.summary,/Authored cached work/);assert.equal(recall.work.items[0].document_id,'transcript-1-original');
 const env={PATH:process.env.PATH,HOME:f.base,AUGMENTOR_SHARED_STATE:target.state,AUGMENTOR_SHARED_DATA:target.data,AUGMENTOR_PI_CONFIG:join(f.base,'private-pi-config'),XDG_CONFIG_HOME:join(f.base,'private-config'),PYTHONDONTWRITEBYTECODE:'1'};
 const native=JSON.parse((await exec(py,['-I','-B','-c',"import sys,json;sys.path.insert(0,sys.argv[1]);from augmentor_linux.prompt_client import PromptClient;print(json.dumps(PromptClient().call('memory.dual.recall',{'session':'pi:target-chat'})))",join(root,'apps/native')],{env})).stdout);assert.deepEqual(native,recall);
 const unavailable=await companionCall(target,'memory','memory.dual.search',{session:'pi:target-chat',query:'Authored cached project'});assert.equal(unavailable.unavailable,true);assert.deepEqual(await companionCall(target,'memory','memory.dual.recall',{session:'pi:target-chat'}),recall);
 assert.equal(requests.length,2);assert(requests.every(r=>r.method==='POST'&&r.path.startsWith('/v1/default/banks/')&&r.path.endsWith('/memories/recall')),'Only explicit synthetic searches reach the unavailable engine; no inference/processing calls');
 await memory.stop();await assert.rejects(()=>companionCall(target,'memory','memory.dual.recall',{session:'pi:target-chat'}));memory=companion(t,target,'memory');const reopened=await memory.ready();assert.notEqual(reopened.pid,first.pid);assert.equal(reopened.person,first.person);assert.equal(reopened.processing.paused,true);assert.deepEqual(await companionCall(target,'memory','memory.dual.recall',{session:'pi:target-chat'}),recall);
 for(const table of tables)assert.deepEqual(await query(db,'SELECT * FROM '+table),saved[table],table+' retains exact source identities/cache/jobs/charges through read/outage/restart');
 assert.equal(requests.length,2);assert.equal(stateInventory(source.data).sha256,before.sha256);
});
