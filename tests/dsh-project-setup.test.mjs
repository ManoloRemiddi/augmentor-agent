// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,mkdir,readFile,writeFile,readdir,rm} from 'node:fs/promises';import {existsSync} from 'node:fs';import {tmpdir} from 'node:os';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
import {authoredSetupDshProject} from './fixtures/dsh-setup-project.mjs';
const root=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.'),{importDshProject}=await import(pathToFileURL(join(root,'dist/runtime/src/dsh-project-import.js'))),{SessionManager}=await import('@earendil-works/pi-coding-agent');
async function fixture(t,options={}){const base=await mkdtemp(join(tmpdir(),'augmentor-dsh-setup-'));t.after(()=>rm(base,{recursive:true,force:true}));const cwd=join(base,'project');await mkdir(cwd);return {...await authoredSetupDshProject(cwd,options),base,source:join(base,'source.json'),state:join(base,'state')};}
async function save(f){const bytes=JSON.stringify(f.value);await writeFile(f.source,bytes,{mode:0o600});return {sourceSha256:createHash('sha256').update(bytes).digest('hex'),selection:{provider:'fixture',model:'chosen-model'}};}
for(const minimal of [false,true])test('v4 setup-only conversation preserves its source without creating historical chat or carrying old grants '+(minimal?'minimal':'full'),async t=>{
 const f=await fixture(t,{only:true,minimal}),options=await save(f),before=await readFile(f.source),receipt=await importDshProject(f.source,f.state,options);
 assert.equal(receipt.sourceHistoryKind,'setup-only');assert.equal(receipt.contextEntries,0);assert.deepEqual(receipt.effectiveSourceSeqs,[]);assert.equal(receipt.sourceEvents,f.session.records.length);assert.equal(receipt.historicalToolCallsExecutable,false);
 const meta=JSON.parse(await readFile(join(f.state,'sessions',receipt.sessionId+'.meta.json')));assert.equal(meta.policy,'read-only');assert.equal(meta.running,false);assert.deepEqual(meta.requests,[]);assert.equal(meta.title,'Authored setup-only chat');assert.deepEqual(meta.selection,options.selection);
 const context=SessionManager.open(meta.file).buildSessionContext().messages;assert.equal(context.length,1);assert(context.every(m=>m.role==='custom'));assert(!JSON.stringify(context).includes('historical-preset-must-not-be-active'));assert(!JSON.stringify(context).includes('historical-provider'));
 const display=(await readFile(join(f.state,'sessions',receipt.sessionId+'.events.jsonl'),'utf8')).trim().split('\n').map(JSON.parse);assert(!display.some(e=>['user/message','assistant/message','tool/call','tool/result'].includes(e.type)));assert(display.at(-1).data.message.includes('Send your first message'));
 assert.deepEqual(await readFile(f.source),before);assert.deepEqual(await readFile(join(f.state,receipt.rawArchive)),before);
});
test('setup-only and completed source conversations retain their identities and organization in one atomic project',async t=>{
 const f=await fixture(t),receipt=await importDshProject(f.source,f.state,await save(f));assert.equal(receipt.sessions.length,3);assert.equal(receipt.sessions.filter(s=>s.sourceHistoryKind==='setup-only').length,1);assert.equal(receipt.sessions.filter(s=>s.contextEntries>0).length,2);
 const organization=JSON.parse(await readFile(join(f.state,'session-organization.json')));assert.equal(organization.pinnedSessionIds.length,2);assert.equal(organization.archivedSessionIds.length,1);assert(new Set(receipt.sessions.map(s=>s.sessionId)).size===3);
});
const append=(f,type,data)=>{const rows=f.session.records;rows.push({type:'event',event:{seq:rows.length,time:1700000001000+rows.length,type,data}});f.session.opening.cursor=rows.length-1;};
for(const [name,mutate,pattern] of [
 ['unfinished turn',f=>append(f,'turn/start',{turn:1}),/unresolved|finish/],
 ['assistant work without a human input',f=>append(f,'assistant/message',{turn:1,step:1,message:{role:'assistant',content:[{type:'text',text:'Authored work must not look unused'}]}}),/unresolved/],
 ['undispatched action proposal',f=>append(f,'assistant/message',{turn:1,step:1,message:{role:'assistant',content:[{type:'tool-call',id:'pending',name:'read',arguments:'{}'}]}}),/unresolved/],
 ['pending dispatched action even with a stopped turn',f=>{append(f,'turn/start',{turn:1});append(f,'user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'Authored request'}]});append(f,'assistant/message',{turn:1,step:1,message:{role:'assistant',content:[{type:'tool-call',id:'pending',name:'read',arguments:'{}'}]}});append(f,'tool/call',{turn:1,step:1,callId:'pending',name:'read',arguments:'{}'});append(f,'turn/end',{turn:1,reason:{kind:'aborted'}});},/unresolved/],
 ['goal activity',f=>append(f,'goal/change',{active:true}),/unresolved/],
 ['tool workflow',f=>append(f,'tool-workflow/run-start',{id:'authored-workflow'}),/unresolved/],
 ['unknown event',f=>append(f,'authored/unknown',{value:true}),/unresolved|unknown/],
 ['legacy untyped setup history',f=>{delete f.session.opening.header.version;},/unresolved/],
 ['header-only incomplete initialization',f=>{f.session.records=[];f.session.opening.cursor=-1;},/bounded complete/],
 ['changed source cut',f=>{f.session.opening.cursor++;},/incomplete/],
 ['missing inherited boundary',f=>{f.session.opening.header.isSeeded=true;},/inherited boundary/],
])test('setup exception does not admit '+name,async t=>{
 const f=await fixture(t,{only:true});mutate(f);const options=await save(f),before=await readFile(f.source);await assert.rejects(()=>importDshProject(f.source,f.state,options),pattern);assert(!existsSync(f.state));assert(!(await readdir(f.base)).some(n=>n.startsWith('.dsh-import-')));assert.deepEqual(await readFile(f.source),before);
});
