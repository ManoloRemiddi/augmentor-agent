// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {richRuntimeFixture} from './fixtures/dsh-rich-runtime.mjs';import {authoredSurfaceDshProject,authoredFramedSurfaceDshProject} from './fixtures/dsh-surface-project.mjs';
test('public framed source checkpoints reach the actual Pi provider as historical context and survive cold reads without replay',{timeout:45000},async t=>{
 const f=await richRuntimeFixture(t,{vision:false,projectFactory:authoredFramedSurfaceDshProject}),sessionIds=(await f.call('session.list')).items.map(s=>s.sessionId).sort();assert.equal(f.requests.length,0);await f.prompt(f.sid,{kind:'read'});assert.equal(f.requests.length,2);
 const messages=JSON.stringify(f.requests[0].messages);assert(messages.includes('FINAL-SOURCE-CHECKPOINT'));assert(messages.includes('<compacted-summary>'));assert(messages.includes('</compacted-summary>'));assert(!messages.includes('SUPERSEDED-FIRST-CHECKPOINT'));assert(!messages.includes('SUPERSEDED-SECOND-QUESTION'));assert(!messages.includes('image_url'));
 const native=await f.native(f.sid);await f.stop();await f.start();const history=await f.call('session.history',{sessionId:f.sid});assert(JSON.stringify(history).includes('SUPERSEDED-SECOND-QUESTION'));assert.equal(f.requests.length,2);assert.deepEqual((await f.native(f.sid)).bytes,native.bytes);assert.equal(await readFile(f.source,'utf8'),f.raw);assert.deepEqual((await f.call('session.list')).items.map(s=>s.sessionId).sort(),sessionIds);
});
test('real Pi continuation uses final source replacements and never revives shadowed images or old tool work',{timeout:45000},async t=>{
 const f=await richRuntimeFixture(t,{vision:false,projectFactory:authoredSurfaceDshProject});assert.equal(f.requests.length,0);assert.equal((await f.call('memory.status')).events,0);await f.call('events.subscribe',{sessionId:f.sid});
 await f.prompt(f.sid,{kind:'read'});assert.equal(f.requests.length,2);const request=JSON.stringify(f.requests[0].messages);
 assert(request.includes('FINAL-SOURCE-CHECKPOINT'));assert(request.includes('CURRENT-SOURCE-QUESTION'));assert(request.includes('CURRENT-SOURCE-ANSWER'));for(const old of ['SUPERSEDED','NATIVE-HISTORY-ALPHA','PRUNED-HISTORICAL','image_url'])assert(!request.includes(old),'shadowed '+old+' remains outside active context');
 assert.deepEqual(f.frames.filter(x=>x.method==='session/event'&&x.payload.event.type==='tool/call').map(x=>x.payload.event.data.name),['plan_read']);
 const native=await f.native(f.sid);await f.stop();await f.start();const history=await f.call('session.history',{sessionId:f.sid});assert(JSON.stringify(history).includes('SUPERSEDED-SECOND-QUESTION'),'original display history is still inspectable');assert.equal(f.requests.length,2);assert.deepEqual((await f.native(f.sid)).bytes,native.bytes);
 await f.prompt(f.sid,{kind:'read'});assert.equal(f.requests.length,4);assert(!JSON.stringify(f.requests[2].messages).includes('SUPERSEDED'));assert.equal(await readFile(f.source,'utf8'),f.raw);
 const link=await f.link(),url=new URL(link.url),headers={Authorization:'Bearer '+new URLSearchParams(url.hash.slice(1)).get('token')};
 const image=url.origin+'/api/attachments/image?'+new URLSearchParams({sessionId:f.sid,ref:JSON.stringify(f.attachment)});assert.deepEqual(Buffer.from(await (await fetch(image,{headers})).arrayBuffer()),f.bytes,'shadowing context does not delete the original gallery image');
});
test('plain source message replacement sends only the edited human text at its original context position',{timeout:30000},async t=>{
 const {authoredDshProject}=await import('./fixtures/dsh-project.mjs');
 const projectFactory=async cwd=>{const value=authoredDshProject(cwd),s=value.sessions[0],rows=s.records;for(const {event:e} of rows)if(['user/message','assistant/message','tool/result'].includes(e.type))e.surfaceOp='append';s.opening.header.version=4;
 const seq=rows.length;rows.push({type:'event',event:{seq,time:1700000001000,type:'user/message',data:{role:'user',source:{kind:'user'},content:[{type:'text',text:'EDITED-ONLY-SOURCE-QUESTION'}]},surfaceOp:{op:'replace',startSeq:1,endSeq:1},sourceEventSeqs:[1]}});s.opening.cursor=seq;return {value};};
 const f=await richRuntimeFixture(t,{vision:false,projectFactory});assert.equal(f.requests.length,0);await f.prompt(f.sid,{kind:'read'});assert.equal(f.requests.length,2);
 const messages=f.requests[0].messages,text=JSON.stringify(messages);assert(text.includes('EDITED-ONLY-SOURCE-QUESTION'));assert(!text.includes('NATIVE-HISTORY-ALPHA explicit project question.'),'the overwritten original human message must not remain in provider input');
 const index=messages.findIndex(m=>JSON.stringify(m.content).includes('EDITED-ONLY-SOURCE-QUESTION')),answer=messages.findIndex(m=>JSON.stringify(m.content).includes('NATIVE-HISTORY-ALPHA completed historical answer.'));assert(index>=0&&answer>index,'replacement occupies its source surface position');
});
