// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,readFile,writeFile,rm,readdir,symlink} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';import {promisify} from 'node:util';
import {authoredDshProject} from './fixtures/dsh-project.mjs';
const root=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
const {importDshProjects}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-project-batch.js')));
const {importDshProject}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-project-import.js')));
const {stateInventory}=await import(pathToFileURL(join(root,'dist/runtime/src/profile-transaction.js')));
const sdk=JSON.parse(await readFile(join(root,'node_modules/@earendil-works/pi-coding-agent/package.json')));
const {SessionManager}=await import(pathToFileURL(join(root,'node_modules/@earendil-works/pi-coding-agent',sdk.exports['.'].import)));
const sha=b=>createHash('sha256').update(b).digest('hex');
async function fixture(t){const base=await mkdtemp(join(tmpdir(),'augmentor-project-batch-'));t.after(()=>rm(base,{recursive:true,force:true}));const state=join(base,'state'),selection={provider:'fixture',model:'fixture'};
 const inputs=[],values=[];
 for(const tag of ['A','B']){const cwd=join(base,tag);await mkdir(cwd);const value=authoredDshProject(cwd),ids=new Map(value.workspace.sessionIds.map(id=>[id,tag+'-'+id]));value.workspace.title='Authored '+tag;value.workspace.sessionIds=value.workspace.sessionIds.map(id=>ids.get(id));value.pinnedSessionIds=value.pinnedSessionIds.map(id=>ids.get(id));value.archivedSessionIds=value.archivedSessionIds.map(id=>ids.get(id));for(const s of value.sessions)s.opening.header.id=ids.get(s.opening.header.id);values.push(value);const sourceFile=join(base,tag+'.json'),raw=JSON.stringify(value);await writeFile(sourceFile,raw,{mode:0o600});inputs.push({sourceFile,options:{sourceSha256:sha(raw),selection}});}
 return {base,state,selection,inputs,values};}
async function save(f,index){const raw=JSON.stringify(f.values[index]);await writeFile(f.inputs[index].sourceFile,raw,{mode:0o600});f.inputs[index].options.sourceSha256=sha(raw);}
test('one transaction publishes multiple projects with independent native paths, pins and archives',{skip:process.platform!=='linux'},async t=>{
 const f=await fixture(t),result=await importDshProjects(f.inputs,f.state);assert.equal(result.result.createdSessions.length,6);assert.equal(result.result.existingConversationsPreserved,0);assert.equal(result.transaction.backup,null);
 const workspace=JSON.parse(await readFile(join(f.state,'workspaces.json')));assert.deepEqual(workspace.items.map(x=>x.title),['Authored A','Authored B']);const organization=JSON.parse(await readFile(join(f.state,'session-organization.json')));assert.equal(organization.pinnedSessionIds.length,4);assert.equal(organization.archivedSessionIds.length,2);
 for(const row of result.result.createdSessions){const meta=JSON.parse(await readFile(join(f.state,'sessions',row.sessionId+'.meta.json')));assert(meta.file.startsWith(join(f.state,'sessions')+'/'));assert(!meta.file.includes('.stage'));assert((await readFile(meta.file,'utf8')).includes(f.state));}
 assert.equal(stateInventory(f.state).sha256,result.after.sha256);assert.equal(result.transaction.status,'completed');
});
test('an existing imported chat and its new Harness continuation remain byte exact on repeated source import',{skip:process.platform!=='linux'},async t=>{
 const f=await fixture(t),a=await importDshProject(f.inputs[0].sourceFile,f.state,f.inputs[0].options),row=a.sessions[0],path=join(f.state,'sessions',row.sessionId+'.meta.json'),meta=JSON.parse(await readFile(path));
 const manager=SessionManager.open(meta.file);manager.appendMessage({role:'user',content:'NEW-HARNESS-WORK-PRESERVE',timestamp:1700000001000});manager.appendMessage({role:'assistant',content:[{type:'text',text:'New native answer.'}],api:'openai-completions',provider:'fixture',model:'fixture',usage:{input:1,output:1,cacheRead:0,cacheWrite:0,totalTokens:2,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}},stopReason:'stop',timestamp:1700000001001});
 const before=stateInventory(f.state),native=await readFile(meta.file),result=await importDshProjects(f.inputs,f.state);
 assert.equal(result.result.retainedSessions.length,3);assert.equal(result.result.createdSessions.length,3);assert.equal(result.result.existingConversationsPreserved,3);assert.deepEqual(await readFile(meta.file),native);assert.deepEqual(await readFile(path),Buffer.from(JSON.stringify(meta,null,2)+'\n'));
 assert.equal(stateInventory(result.transaction.backup).sha256,before.sha256,'the exact complete original state is retained as the backup');
 const replay=await importDshProjects(f.inputs,f.state);assert.equal(replay.result.createdSessions.length,0);assert.equal(replay.result.retainedSessions.length,6);assert.deepEqual(await readFile(meta.file),native);
});
for(const [name,mutate,pattern] of [
 ['invalid second history',f=>{f.values[1].sessions[0].records[3].event.data.callId='foreign';},/ambiguous/],
 ['duplicate workspace',f=>{f.values[1]=structuredClone(f.values[0]);},/same workspace/],
 ['cross-project source ID',f=>{const id=f.values[0].workspace.sessionIds[0],s=f.values[1],old=s.workspace.sessionIds[0];s.workspace.sessionIds[0]=id;s.sessions[0].opening.header.id=id;s.pinnedSessionIds=s.pinnedSessionIds.map(x=>x===old?id:x);},/more than one chosen project/],
])test('batch '+name+' publishes no destination or partial project',{skip:process.platform!=='linux'},async t=>{
 const f=await fixture(t);mutate(f);await save(f,1);await assert.rejects(()=>importDshProjects(f.inputs,f.state),pattern);assert(!(await readdir(f.base)).includes('state'));assert(!(await readdir(f.base)).some(x=>x.endsWith('.stage')));
});
test('diverging DSH cuts cannot overwrite new Harness work, and linked source state remains untouched',{skip:process.platform!=='linux'},async t=>{
 const f=await fixture(t);await importDshProject(f.inputs[0].sourceFile,f.state,f.inputs[0].options);const before=stateInventory(f.state);f.values[0].sessions[0].records[1].event.data.content[0].text='Changed in DSH';await save(f,0);
 await assert.rejects(()=>importDshProjects(f.inputs,f.state),/diverged/);assert.equal(stateInventory(f.state).sha256,before.sha256);assert(!(await readdir(f.base)).some(x=>x.endsWith('.stage')));
 await symlink(f.state,join(f.base,'linked'));await assert.rejects(()=>importDshProjects(f.inputs,join(f.base,'linked')),/real directory/);assert.equal(stateInventory(f.state).sha256,before.sha256);
});

test('the offline batch CLI accepts explicit project checksums and writes one recoverable state',{skip:process.platform!=='linux'},async t=>{
 const f=await fixture(t),manifest=join(f.base,'manifest.json');await writeFile(manifest,JSON.stringify({schema:'augmentor-dsh-project-batch-input/1',projects:f.inputs}),{mode:0o600});
 const {stdout}=await promisify(execFile)(process.execPath,[join(root,'scripts/import-dsh-projects.mjs'),'import',manifest,f.state],{maxBuffer:4*1024*1024});const result=JSON.parse(stdout);assert.equal(result.result.createdSessions.length,6);assert.equal(result.transaction.status,'completed');assert.equal(stateInventory(f.state).sha256,result.after.sha256);
});

test('a copied profile with native paths into another owner is refused without changing either profile',{skip:process.platform!=='linux'},async t=>{
 const f=await fixture(t),a=await importDshProject(f.inputs[0].sourceFile,f.state,f.inputs[0].options),sid=a.sessions[0].sessionId,path=join(f.state,'sessions',sid+'.meta.json'),meta=JSON.parse(await readFile(path));meta.file=join(f.base,'another-owner','sessions',sid,'native.jsonl');await writeFile(path,JSON.stringify(meta),{mode:0o600});const before=stateInventory(f.state);
 await assert.rejects(()=>importDshProjects(f.inputs,f.state),/outside this profile/);assert.equal(stateInventory(f.state).sha256,before.sha256);
});
