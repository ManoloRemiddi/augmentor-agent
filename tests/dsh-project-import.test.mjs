// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,stat,readdir,rm,symlink,readlink} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {importDshProject} from '../dist/runtime/src/dsh-project-import.js';
import {piTranscriptEvent} from '../dist/memory/src/pi.js';
import {DisplayHistory} from '../dist/runtime/src/display-history.js';
import {toolOwnership} from '../apps/harness/dsh-call-identity.mjs';
import {projectChat} from '../apps/harness/chat-projection.js';
const hash=b=>createHash('sha256').update(b).digest('hex');
async function fixture(t){
 const root=await mkdtemp(join(tmpdir(),'augmentor-dsh-import-'));t.after(()=>rm(root,{recursive:true,force:true}));
 const cwd=join(root,'project');await mkdir(cwd);await writeFile(join(cwd,'original.txt'),'Original authored bytes\n');
 const event=(type,data)=>({type:'event',event:{type,data,seq:0,time:1700000000000}});
 const rows=[event('turn/start',{turn:1}),event('system/message',{message:{content:[{type:'text',text:'Historical SYSTEM MUST NOT become active.'}]}}),event('user/message',{role:'user',source:{kind:'agent-instructions'},content:[{type:'text',text:'Historical bootstrap MUST NOT become active.'}]}),event('user/message',{role:'user',source:{kind:'user'},content:[{type:'text',text:'Inspect the authored project.'}]}),event('assistant/message',{turn:1,step:1,message:{role:'assistant',content:[{type:'tool-call',id:'old-call',name:'read',arguments:'{"path":"original.txt"}'}]}}),event('tool/call',{turn:1,step:1,callId:'old-call',name:'read',arguments:'{"path":"original.txt"}'}),event('tool/result',{turn:1,step:1,message:{role:'tool',toolCallId:'old-call',isError:false,content:[{type:'text',text:'Original authored bytes\n'}]}}),event('assistant/message',{turn:1,step:2,message:{role:'assistant',content:[{type:'text',text:'I inspected the original; no action remains.'}]}}),event('turn/end',{turn:1,reason:{kind:'completed'}})];rows.forEach((r,i)=>r.event.seq=i);
 const value={schema:'augmentor-dsh-project-export/1',workspace:{path:cwd,title:'Authored project',sessionIds:['authored-source']},sessions:[{opening:{header:{id:'authored-source',cwd},cursor:rows.length-1,projections:{values:{title:'Authored old chat'}}},records:rows}],relatedSessions:[{authored:true}],archivedSessionIds:[],pinnedSessionIds:['authored-source']};
 const source=join(root,'export.json'),state=join(root,'state'),selection={provider:'authored-provider',model:'authored-model'};
 const save=async()=>{const b=JSON.stringify(value);await writeFile(source,b,{mode:0o600});return {sourceSha256:hash(b),selection};};
 return {root,cwd,source,state,value,save,selection};
}
test('offline import cold-opens labelled Pi context and completed GUI tools without executing originals',async t=>{
 const f=await fixture(t),options=await f.save(),sourceBefore=await readFile(f.source);const receipt=importDshProject(f.source,f.state,options);
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
 const f=await fixture(t),options=await f.save();assert.throws(()=>importDshProject(f.source,f.state,{...options,sourceSha256:'0'.repeat(64)}),/checksum changed/);assert(!existsSync(f.state));
 await mkdir(f.state);await writeFile(join(f.state,'sentinel'),'Existing work');assert.throws(()=>importDshProject(f.source,f.state,options),/new absolute path/);assert.equal(await readFile(join(f.state,'sentinel'),'utf8'),'Existing work');
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
])test('unsupported '+name+' leaves no partial destination',async t=>{const f=await fixture(t);change(f.value);const options=await f.save();assert.throws(()=>importDshProject(f.source,f.state,options),pattern);assert(!existsSync(f.state));assert(!(await readdir(f.root)).some(x=>x.startsWith('.dsh-import-')));assert.equal(await readFile(join(f.cwd,'original.txt'),'utf8'),'Original authored bytes\n');});

test('dangling destination link is preserved rather than replaced',async t=>{const f=await fixture(t),options=await f.save();await symlink(join(f.root,'missing'),f.state);assert.throws(()=>importDshProject(f.source,f.state,options),/new absolute path/);assert.equal(await readlink(f.state),join(f.root,'missing'));});
test('large old tool payloads are bounded in continuation context while exact source/display stay intact',async t=>{
 const f=await fixture(t);f.value.sessions[0].records[6].event.data.message.content[0].text='AUTHORED_HEAD '+('Retained exact source text. '.repeat(15000))+' AUTHORED_TAIL';
 const options=await f.save(),receipt=importDshProject(f.source,f.state,options),meta=JSON.parse(await readFile(join(f.state,'sessions',receipt.sessionId+'.meta.json'))),messages=SessionManager.open(meta.file).buildSessionContext().messages;
 const text=JSON.stringify(messages);assert(text.length<12000);assert(text.includes('AUTHORED_HEAD'));assert(text.includes('AUTHORED_TAIL'));assert(text.includes('excerpt cut'));assert(text.includes('Full source archive'));
 assert.equal(receipt.toolPayloadContextChars,256);assert(receipt.toolPayloadCharsNotInContext>300000);assert.equal(receipt.archivedToolProposalMessages,1);assert.deepEqual(await readFile(join(f.state,receipt.rawArchive)),await readFile(f.source));
 const display=[...new DisplayHistory(join(f.state,'sessions',receipt.sessionId+'.events.jsonl')).all()];assert.equal(display.find(e=>e.type==='tool/result').data.result.content[0].text,f.value.sessions[0].records[6].event.data.message.content[0].text);
});
