// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {observeSession} from '../dist/runtime/src/observations.js';
import {ObservationStore,DEFAULT_RETENTION} from '../dist/observation/src/store.js';
function fixture(t,capture=true){
 const root=mkdtempSync(join(tmpdir(),'augmentor-stream-observer-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
 const store=new ObservationStore(root,()=>({...DEFAULT_RETENTION,capturePayloads:capture}));let listener;
 const oldProvider=async data=>{data.transformed=true;},agent={onPayload:async payload=>({...payload,seed:42}),onProviderStreamEvent:oldProvider};
 const session={agent,thinkingLevel:'off',subscribe:callback=>{listener=callback;return()=>{};}};
 const model={id:'fixture',provider:'fixture',api:'openai-completions',contextWindow:32000};
 const observer=observeSession(session,store,'fixture',()=>({selected:{provider:'fixture',model:'fixture'}}),()=>{},message=>assert.fail(message));
 const emit=(type,message={role:'assistant',content:[],stopReason:'stop'})=>listener({type,message});
 return {store,agent,model,observer,emit,oldProvider};
}
test('parsed streams compose prior hooks, retain immutable JSON and redact credential fields',async t=>{
 const f=fixture(t);await f.agent.onPayload({messages:[]},f.model);
 const data={delta:'PRIVATE_FIXTURE_TEXT',apiKey:'SYNTHETIC_SECRET'};await f.agent.onProviderStreamEvent(data,f.model);data.delta='changed afterwards';f.emit('message_end');
 const record=f.store.page('fixture').records.find(r=>r.kind==='provider/stream');
 assert.equal(record.data.coverage,'complete');assert.deepEqual(record.data.credentialRedactions,['apiKey']);
 const body=JSON.parse(f.store.payload('fixture',record.id).text);assert.equal(body.events[0].data.delta,'PRIVATE_FIXTURE_TEXT');assert.equal(body.events[0].data.transformed,true);assert(!JSON.stringify(body).includes('SYNTHETIC_SECRET'));
 f.observer.dispose();assert.equal(f.agent.onProviderStreamEvent,f.oldProvider);
});
test('parsed-stream capture reports its bound and metadata mode retains no contents',async t=>{
 const f=fixture(t);await f.agent.onPayload({},f.model);
 await f.agent.onProviderStreamEvent({text:'small'},f.model);await f.agent.onProviderStreamEvent({text:'x'.repeat(9*1024*1024)},f.model);f.emit('message_end');
 const record=f.store.page('fixture').records.find(r=>r.kind==='provider/stream');assert.equal(record.data.coverage,'partial');assert.equal(record.data.observedEvents,2);assert.equal(record.data.capturedEvents,1);assert.equal(record.data.droppedEvents,1);
 const metadata=fixture(t,false);await metadata.agent.onPayload({},metadata.model);await metadata.agent.onProviderStreamEvent({text:'PRIVATE_SENTINEL'},metadata.model);metadata.emit('message_end');
 assert(!JSON.stringify(metadata.store.page('fixture')).includes('PRIVATE_SENTINEL'));assert.equal(metadata.store.page('fixture').records.find(r=>r.kind==='provider/stream').payload.state,'disabled');
});
test('an adapter without a new request hook does not inherit the preceding request identity',async t=>{
 const f=fixture(t);await f.agent.onPayload({},f.model);f.emit('message_end');f.emit('message_start');f.emit('message_end');
 const completed=f.store.page('fixture').records.filter(r=>r.kind==='model/complete');assert(completed[0].requestId);assert.equal(completed[1].requestId,undefined);assert.equal(completed[1].data.requestCoverage,'not-observed');assert.equal(completed[1].data.durationMs,undefined);
});
