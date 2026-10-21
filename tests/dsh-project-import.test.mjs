// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,stat,readdir,rm,symlink,readlink,realpath} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
const applicationRoot=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.');
const sdkRoot=resolve(applicationRoot,'node_modules/@earendil-works/pi-coding-agent'),sdkPackage=JSON.parse(await readFile(join(sdkRoot,'package.json'),'utf8'));
const {SessionManager}=await import(pathToFileURL(resolve(sdkRoot,sdkPackage.exports['.'].import)));
const {importDshProject}=await import(pathToFileURL(resolve(applicationRoot,'dist/runtime/src/dsh-project-import.js')));
import {piTranscriptEvent} from '../dist/memory/src/pi.js';
import {DisplayHistory} from '../dist/runtime/src/display-history.js';
import {toolOwnership} from '../apps/harness/dsh-call-identity.mjs';
import {projectChat} from '../apps/harness/chat-projection.js';
const hash=b=>createHash('sha256').update(b).digest('hex');
async function fixture(t){
 const root=await realpath(await mkdtemp(join(tmpdir(),'augmentor-dsh-import-')));t.after(()=>rm(root,{recursive:true,force:true}));
 const cwd=join(root,'project');await mkdir(cwd);await writeFile(join(cwd,'original.txt'),'Original authored bytes\n');
 const event=(type,data)=>({type:'event',event:{type,data,seq:0,time:1700000000000}});
 const rows=[event('turn/start',{turn:1}),event('system/message',{message:{content:[{type:'text',text:'Historical SYSTEM MUST NOT become active.'}]}}),event('user/message',{role:'user',source:{kind:'agent-instructions'},content:[{type:'text',text:'Historical bootstrap MUST NOT become active.'}]}),event('user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'Inspect the authored project.'}]}),event('assistant/message',{turn:1,step:1,message:{role:'assistant',content:[{type:'tool-call',id:'old-call',name:'read',arguments:'{"path":"original.txt"}'}]}}),event('tool/call',{turn:1,step:1,callId:'old-call',name:'read',arguments:'{"path":"original.txt"}'}),event('tool/result',{turn:1,step:1,message:{role:'tool',toolCallId:'old-call',isError:false,content:[{type:'text',text:'Original authored bytes\n'}]}}),event('assistant/message',{turn:1,step:2,message:{role:'assistant',content:[{type:'text',text:'I inspected the original; no action remains.'}]}}),event('turn/end',{turn:1,reason:{kind:'completed'}})];rows.forEach((r,i)=>r.event.seq=i);
 const value={schema:'augmentor-dsh-project-export/1',workspace:{path:cwd,title:'Authored project',sessionIds:['authored-source']},sessions:[{opening:{header:{id:'authored-source',cwd},cursor:rows.length-1,projections:{values:{title:'Authored old chat'}}},records:rows}],relatedSessions:[{authored:true}],archivedSessionIds:[],pinnedSessionIds:['authored-source']};
 const source=join(root,'export.json'),state=join(root,'state'),selection={provider:'authored-provider',model:'authored-model'};
 const save=async()=>{const b=JSON.stringify(value);await writeFile(source,b,{mode:0o600});return {sourceSha256:hash(b),selection};};
 return {root,cwd,source,state,value,save,selection};
}
test('offline import cold-opens labelled Pi context and completed GUI tools without executing originals',async t=>{
 const f=await fixture(t),options=await f.save(),sourceBefore=await readFile(f.source);const receipt=await importDshProject(f.source,f.state,options);
 const meta=JSON.parse(await readFile(join(f.state,'sessions',receipt.sessionId+'.meta.json'))),manager=SessionManager.open(meta.file),context=manager.buildSessionContext();
 assert.equal(meta.policy,'read-only');assert.equal(meta.running,false);assert.deepEqual(meta.requests,[]);assert.deepEqual(meta.selection,f.selection);assert.equal(meta.memoryStartSeq,undefined);
 assert.equal(context.messages.filter(m=>m.role==='user').length,1);assert(!context.messages.some(m=>m.role==='assistant'||m.role==='toolResult'),'old calls are labelled data, never native executable proposals');
 const text=JSON.stringify(context.messages);assert(text.includes('Original authored bytes'));assert(text.includes('old-call'));assert(!text.includes('Historical SYSTEM MUST'));assert(!text.includes('Historical bootstrap MUST'));assert(text.includes('Wait for a new human request'));
 const display=[...new DisplayHistory(join(f.state,'sessions',receipt.sessionId+'.events.jsonl')).all()],bindings=toolOwnership(display),chat=projectChat(display,{toolBindings:bindings});
 assert.equal(chat.filter(x=>x.kind==='user').length,1);assert.equal(chat.find(x=>x.kind==='tool').status,'finished');assert.equal(bindings.get(6).id,bindings.get(7).id);assert.equal(display[0].data.importedFrom.sourceSeq,0);assert.equal(display[0].seq,1);assert.deepEqual(display.flatMap(e=>piTranscriptEvent(e)),[],'historical records are not recaptured into automatic memory');
 assert.equal(await readFile(join(f.cwd,'original.txt'),'utf8'),'Original authored bytes\n');assert.deepEqual(await readFile(f.source),sourceBefore);assert.deepEqual(await readFile(join(f.state,receipt.rawArchive)),sourceBefore);
 assert.equal(receipt.relatedSessionsArchived,1);assert.deepEqual(JSON.parse(await readFile(join(f.state,'session-organization.json'))).pinnedSessionIds,[receipt.sessionId]);assert.equal((await stat(meta.file)).mode&0o077,0);
 manager.appendMessage({role:'user',content:'New explicit human follow-up',timestamp:1700000001000});assert.equal(SessionManager.open(meta.file).buildSessionContext().messages.at(-1).content,'New explicit human follow-up');
});
test('changed source and an occupied target fail without overwriting either side',async t=>{
 const f=await fixture(t),options=await f.save();await assert.rejects(()=>importDshProject(f.source,f.state,{...options,sourceSha256:'0'.repeat(64)}),/checksum changed/);assert(!existsSync(f.state));
 await mkdir(f.state);await writeFile(join(f.state,'sentinel'),'Existing work');await assert.rejects(()=>importDshProject(f.source,f.state,options),/new absolute path/);assert.equal(await readFile(join(f.state,'sentinel'),'utf8'),'Existing work');
});
for(const [name,change,pattern] of [
 ['gap',v=>{v.sessions[0].records[3].event.seq=99;},/gap/],
 ['undispatched proposal',v=>{v.sessions[0].records[5].event.type='historical-other';v.sessions[0].records[6].event.type='historical-other';},/unresolved/],
 ['pending call',v=>{v.sessions[0].records[6].event.type='historical-other';},/unresolved/],
 ['missing proposal',v=>{v.sessions[0].records[4].event.data.message.content=[];},/ambiguous/],
 ['compaction',v=>{v.sessions[0].records[1].event.type='context/compaction';},/compacted/],
 ['image attachment',v=>{v.sessions[0].records[3].event.data.content.push({type:'image',attachment:{}});},/attachment/],
 ['unfinished turn',v=>{v.sessions[0].records.pop();v.sessions[0].opening.cursor--;},/finish/],
 ['membership',v=>{v.workspace.sessionIds=['other'];},/membership/]
])test('unsupported '+name+' leaves no partial destination',async t=>{const f=await fixture(t);change(f.value);const options=await f.save();await assert.rejects(()=>importDshProject(f.source,f.state,options),pattern);assert(!existsSync(f.state));assert(!(await readdir(f.root)).some(x=>x.startsWith('.dsh-import-')));assert.equal(await readFile(join(f.cwd,'original.txt'),'utf8'),'Original authored bytes\n');});

test('dangling destination link is preserved rather than replaced',async t=>{const f=await fixture(t),options=await f.save();await symlink(join(f.root,'missing'),f.state);await assert.rejects(()=>importDshProject(f.source,f.state,options),/new absolute path/);assert.equal(await readlink(f.state),join(f.root,'missing'));});
test('large old tool payloads are bounded in continuation context while exact source/display stay intact',async t=>{
 const f=await fixture(t);f.value.sessions[0].records[6].event.data.message.content[0].text='AUTHORED_HEAD '+('Retained exact source text. '.repeat(15000))+' AUTHORED_TAIL';
 const options=await f.save(),receipt=await importDshProject(f.source,f.state,options),meta=JSON.parse(await readFile(join(f.state,'sessions',receipt.sessionId+'.meta.json'))),messages=SessionManager.open(meta.file).buildSessionContext().messages;
 const text=JSON.stringify(messages);assert(text.length<12000);assert(text.includes('AUTHORED_HEAD'));assert(text.includes('AUTHORED_TAIL'));assert(text.includes('excerpt cut'));assert(text.includes('Full source archive'));
 assert.equal(receipt.toolPayloadContextChars,256);assert(receipt.toolPayloadCharsNotInContext>300000);assert.equal(receipt.archivedToolProposalMessages,1);assert.deepEqual(await readFile(join(f.state,receipt.rawArchive)),await readFile(f.source));
 const display=[...new DisplayHistory(join(f.state,'sessions',receipt.sessionId+'.events.jsonl')).all()];assert.equal(display.find(e=>e.type==='tool/result').data.result.content[0].text,f.value.sessions[0].records[6].event.data.message.content[0].text);
});

async function multiFixture(t){
 const f=await fixture(t),first=f.value.sessions[0];
 f.value.workspace.sessionIds=['authored-source','authored-beta','authored-gamma'];
 f.value.sessions=f.value.workspace.sessionIds.map((id,index)=>{const s=structuredClone(first);s.opening.header.id=id;s.opening.projections.values.title='Authored chat '+index;
  s.records[3].event.data.content[0].text='Authored isolated question '+index;
  s.records[6].event.data.message.content[0].text='Authored isolated result '+index;
  s.records[7].event.data.message.content[0].text='Authored isolated answer '+index;return s;});
 f.value.archivedSessionIds=['authored-gamma'];f.value.pinnedSessionIds=['authored-beta','authored-gamma','authored-source'];
 return f;
}
test('a whole project cold-opens separate native conversations with exact pin order, archive membership and one raw archive',async t=>{
 const f=await multiFixture(t);f.value.sessions.reverse();const options=await f.save();options.sessionSelections={'authored-beta':{provider:'explicit-beta-provider',model:'explicit-beta-model'}};const sourceBefore=await readFile(f.source),receipt=await importDshProject(f.source,f.state,options);
 assert.equal(receipt.schema,'augmentor-dsh-project-import/2');assert.equal(receipt.sessionId,undefined);assert.equal(receipt.sessions.length,3);
 assert.deepEqual(receipt.sessions.map(r=>r.sourceSessionId),f.value.workspace.sessionIds);assert.equal(receipt.sourceEvents,27);assert.equal(receipt.displayEvents,30);
 assert.equal(receipt.relatedSessionsArchived,1);assert.equal((await readdir(join(f.state,'dsh-imports'))).length,2,'one shared original plus one project receipt');
 const native=[];
 for(const [index,row] of receipt.sessions.entries()){
  const meta=JSON.parse(await readFile(join(f.state,'sessions',row.sessionId+'.meta.json'))),manager=SessionManager.open(meta.file),text=JSON.stringify(manager.buildSessionContext().messages);
  assert.equal(meta.title,'Authored chat '+index);assert.equal(manager.getSessionName(),'Authored chat '+index);assert.equal(meta.policy,'read-only');assert.equal(meta.running,false);assert.deepEqual(meta.requests,[]);assert.deepEqual(meta.selection,index===1?options.sessionSelections['authored-beta']:f.selection);assert.deepEqual(row.selection,meta.selection);
  assert(text.includes('Authored isolated question '+index));assert(text.includes('Authored isolated result '+index));assert(text.includes('Authored isolated answer '+index));
  for(const other of [0,1,2].filter(n=>n!==index))assert(!text.includes('Authored isolated question '+other),'no cross-conversation context');
  assert(!manager.buildSessionContext().messages.some(m=>m.role==='assistant'||m.role==='toolResult'));
  const display=[...new DisplayHistory(join(f.state,'sessions',row.sessionId+'.events.jsonl')).all()];
  assert(display.slice(0,-1).every(e=>e.data.importedFrom.sourceSessionId===row.sourceSessionId));assert.deepEqual(display.flatMap(piTranscriptEvent),[]);
  assert.equal(projectChat(display,{toolBindings:toolOwnership(display)}).find(x=>x.kind==='tool').status,'finished','reused old-call identities remain local to each conversation');
  native.push({manager,file:meta.file,bytes:await readFile(meta.file)});
 }
 const organization=JSON.parse(await readFile(join(f.state,'session-organization.json')));assert.deepEqual(organization.pinnedSessionIds,[receipt.sessions[1].sessionId,receipt.sessions[0].sessionId]);assert.deepEqual(organization.archivedSessionIds,[receipt.sessions[2].sessionId]);
 assert.equal(JSON.parse(await readFile(join(f.state,'workspaces.json'))).items.length,1);assert.deepEqual(await readFile(join(f.state,receipt.rawArchive)),sourceBefore);assert.deepEqual(await readFile(f.source),sourceBefore);
 native[1].manager.appendMessage({role:'user',content:'New explicit Beta continuation',timestamp:1700000001000});
 assert.equal(SessionManager.open(native[1].file).buildSessionContext().messages.at(-1).content,'New explicit Beta continuation');
 for(const index of [0,2])assert.deepEqual(await readFile(native[index].file),native[index].bytes);
 assert.equal(await readFile(join(f.cwd,'original.txt'),'utf8'),'Original authored bytes\n');
});
for(const [name,change,pattern] of [
 ['invalid second history',v=>{v.sessions[1].records[6].event.type='unresolved-original';},/unresolved/],
 ['duplicate source identity',v=>{v.sessions[1].opening.header.id=v.sessions[0].opening.header.id;},/membership/],
 ['duplicate project membership',v=>{v.workspace.sessionIds[1]=v.workspace.sessionIds[0];},/membership/],
 ['second conversation in another folder',v=>{v.sessions[1].opening.header.cwd+='/other';},/another workspace/],
 ['foreign pin',v=>{v.pinnedSessionIds.push('not-in-the-project');},/organization/],
 ['malformed organization',v=>{v.archivedSessionIds='not-an-array';},/organization/],
 ['overflow',v=>{v.sessions=Array.from({length:129},()=>v.sessions[0]);},/128/]
])test('whole-project '+name+' publishes no partial conversations',async t=>{
 const f=await multiFixture(t);change(f.value);const options=await f.save(),before=await readFile(f.source);await assert.rejects(()=>importDshProject(f.source,f.state,options),pattern);
 assert(!existsSync(f.state));assert(!(await readdir(f.root)).some(x=>x.startsWith('.dsh-import-')));assert.deepEqual(await readFile(f.source),before);
});
test('an empty source project preserves its folder registration without inventing a conversation',async t=>{
 const f=await fixture(t);f.value.sessions=[];f.value.workspace.sessionIds=[];f.value.relatedSessions=[];f.value.pinnedSessionIds=[];
 const receipt=await importDshProject(f.source,f.state,await f.save());assert.equal(receipt.schema,'augmentor-dsh-project-import/2');assert.deepEqual(receipt.sessions,[]);assert.equal(receipt.sourceEvents,0);assert.equal(receipt.contextEntries,0);
 assert.deepEqual(await readdir(join(f.state,'sessions')),[]);assert.equal(JSON.parse(await readFile(join(f.state,'workspaces.json'))).items[0].cwd,f.cwd);
});

for(const [name,sessionSelections] of [
 ['foreign source',{'not-a-source':{provider:'explicit',model:'choice'}}],
 ['blank model',{'authored-beta':{provider:'explicit',model:'  '}}],
 ['extra credential fields',{'authored-beta':{provider:'explicit',model:'choice',apiKey:'authored-not-a-real-key'}}],
 ['array mapping',[]]
])test('invalid per-conversation model '+name+' leaves the whole destination absent',async t=>{
 const f=await multiFixture(t),options=await f.save();await assert.rejects(()=>importDshProject(f.source,f.state,{...options,sessionSelections}),/model|project/);assert(!existsSync(f.state));
});

test('offline CLI accepts an explicit bounded session-model map and reports all source mappings',async t=>{
 const f=await multiFixture(t),options=await f.save(),mapFile=join(f.root,'authored-model-map.json');
 const chosen={provider:'explicit-beta-provider',model:'explicit-beta-model'};await writeFile(mapFile,JSON.stringify({'authored-beta':chosen}),{mode:0o600});
 const script=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.','scripts/import-dsh-project.mjs');
 const {stdout}=await promisify(execFile)(process.execPath,[script,f.source,f.state,options.sourceSha256,f.selection.provider,f.selection.model,'--session-selections',mapFile]);
 const receipt=JSON.parse(stdout);assert.equal(receipt.sessions.length,3);assert.deepEqual(receipt.sessions[1].selection,chosen);assert.deepEqual(receipt.sessions[0].selection,f.selection);
 const meta=JSON.parse(await readFile(join(f.state,'sessions',receipt.sessions[1].sessionId+'.meta.json')));assert.deepEqual(meta.selection,chosen);
});

test('a second native writer failure removes the entire staged project and preserves its source',async t=>{
 const f=await multiFixture(t),options=await f.save(),before=await readFile(f.source),create=SessionManager.create;let written=0;
 t.mock.method(SessionManager,'create',(...args)=>{if(++written===2)throw Error('Authored second native writer failure');return create(...args);});
 await assert.rejects(()=>importDshProject(f.source,f.state,options),/Authored second native writer failure/);assert.equal(written,2);
 assert(!existsSync(f.state));assert(!(await readdir(f.root)).some(x=>x.startsWith('.dsh-import-')));assert.deepEqual(await readFile(f.source),before);assert.equal(await readFile(join(f.cwd,'original.txt'),'utf8'),'Original authored bytes\n');
});
