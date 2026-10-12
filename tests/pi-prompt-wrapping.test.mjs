// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';import {join} from 'node:path';
import {piPromptWrapping} from '../dist/runtime/src/prompt-wrapping.js';
import {planFixture,until} from './fixtures/plans.mjs';

async function preferences(f,field,value){const row=(await f.call('settings.describe',{ns:'dsh-context'})).namespaces[0];return f.call('settings.mutate',{ns:'dsh-context',expectedRevision:row.revision,ops:[{op:'set',path:[field],value}]});}
const system=body=>body.messages.filter(row=>row.role==='system'||row.role==='developer').map(row=>typeof row.content==='string'?row.content:row.content.map(part=>part.text??'').join('')).join('\n\n');
const payload=async(f,sid,row)=>{let offset=0,text='';while(true){const page=await f.call('observation.payload',{sessionId:sid,eventId:row.id,offset,limit:65536,sha256:row.payload.sha256});assert(page.available);text+=page.text;if(!page.hasMore)return JSON.parse(text);assert(page.nextOffset>offset);offset=page.nextOffset;}};
async function evidence(f,sid){const rows=(await f.call('observation.list',{sessionId:sid,limit:500})).records;return Promise.all(rows.filter(row=>row.kind==='context/provenance').map(row=>payload(f,sid,row)));}

test('verbatim supplier section registration preserves literal text, structured system state, tool declarations and native input copies',()=>{
 let hook,revision=3,value={promptPrefix:'  PREFIX {{literal}}\r\n🙂  ',promptSuffix:' SUFFIX {{literal}} '};const observed=[];
 piPromptWrapping(()=>({revision,value}),row=>observed.push(row))({on:(name,handler)=>{assert.equal(name,'context_with_system');hook=handler;}});
 const messages=[{role:'system',timestamp:1,content:[{type:'text',text:'BASE'}],sections:{one:'FIRST','dsh-context:prompt-suffix':'APPROVED_OTHER_OWNER'},toolsAdded:[{name:'exact',description:'preserved',parameters:{type:'object'}}]},{role:'user',timestamp:2,content:'USER'},{role:'system',timestamp:3,content:'LATER',sections:{one:'REPLACED',two:'LAST_SECTION'},toolsRemoved:[{name:'retired'}]}],original=structuredClone(messages);
 const result=hook({messages});assert.deepEqual(messages,original);assert.equal(result.messages[0].content[0].text,value.promptPrefix+'\n\n');assert.deepEqual(result.messages[0].toolsAdded,original[0].toolsAdded);assert.deepEqual(result.messages[0].sections,original[0].sections);assert.deepEqual(result.messages[2].toolsRemoved,original[2].toolsRemoved);assert.equal(result.messages[2].sections['dsh-context:prompt-suffix:1'],value.promptSuffix);assert.equal(observed[0].revision,3);assert.equal(observed[0].sections[0].interpolate,false);assert.deepEqual(hook({messages}),result,'request copies cannot accumulate wrapping in native history');
 revision=4;value={promptPrefix:' \n ',promptSuffix:'\t'};assert.equal(hook({messages}),undefined);assert.equal(observed.at(-1).state,'disabled');assert.deepEqual(messages,original);
 value={promptPrefix:'ACTIVE'};assert.equal(hook({messages:[messages[1]]}),undefined);assert.equal(observed.at(-1).state,'unavailable-no-leading-system-message');
 piPromptWrapping(()=>({revision,value}),()=>{throw Error('inspection unavailable');})({on:(_name,handler)=>hook=handler});assert(hook({messages}).messages[0].content[0].text.startsWith('ACTIVE'));
});

test('one real Host owner applies an edit from the next model step, retains earlier exact requests and survives cold inspection without replay',{timeout:60000},async t=>{
 const f=await planFixture(t),sid='wrapping-parent',marker=join(f.workspace,'tool-waiting'),release=join(f.workspace,'tool-release'),extension=join(f.workspace,'gate.mjs');
 await writeFile(extension,"import {writeFileSync,existsSync} from 'node:fs';export default pi=>pi.on('tool_call',async event=>{if(event.toolName==='plan_read'){writeFileSync("+JSON.stringify(marker)+",'waiting');while(!existsSync("+JSON.stringify(release)+"))await new Promise(resolve=>setTimeout(resolve,20));}});");
 await writeFile(join(f.config,'resources.json'),JSON.stringify({sources:[extension],skills:[]}));
 await preferences(f,'promptPrefix','PREFIX_A {{literal}}');await preferences(f,'promptSuffix','SUFFIX_A');
 await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});await f.prompt(sid,{kind:'read'},{wait:false});await until(async()=>readFile(marker,'utf8').then(text=>text==='waiting').catch(()=>false),'actual tool held');assert.equal(f.requests.length,1);
 await preferences(f,'promptPrefix','PREFIX_B');await preferences(f,'promptSuffix','SUFFIX_B');assert.equal(f.requests.length,1,'saving text starts no provider call');await writeFile(release,'release');await f.settled(sid);assert.equal(f.requests.length,2,f.errors());
 assert(system(f.requests[0]).startsWith('PREFIX_A {{literal}}\n\n'));assert(system(f.requests[0]).endsWith('SUFFIX_A'));assert(system(f.requests[1]).startsWith('PREFIX_B\n\n'));assert(system(f.requests[1]).endsWith('SUFFIX_B'));assert(!system(f.requests[1]).includes('PREFIX_A'));assert.deepEqual(f.requests[1].tools,f.requests[0].tools);
 const snapshots=await evidence(f,sid);assert.deepEqual(snapshots.map(row=>row.snapshots.promptWrapping.revision),[2,4]);assert.equal(snapshots[0].snapshots.promptWrapping.sections[0].text,'PREFIX_A {{literal}}');assert.equal(snapshots[1].snapshots.promptWrapping.sections[0].text,'PREFIX_B');
 const native=await f.native(sid);assert(!native.bytes.includes('PREFIX_A'));assert(!native.bytes.includes('PREFIX_B'));const count=f.requests.length,history=await f.call('session.history',{sessionId:sid});
 await f.stop();await f.start();assert.equal((await f.call('settings.describe',{ns:'dsh-context'})).namespaces[0].value.promptPrefix,'PREFIX_B');assert.deepEqual(await evidence(f,sid),snapshots);assert.deepEqual((await f.native(sid)).bytes,native.bytes);assert.deepEqual(await f.call('session.history',{sessionId:sid}),history);assert.equal(f.requests.length,count);
 await preferences(f,'promptPrefix','');await preferences(f,'promptSuffix','');await f.prompt(sid,{kind:'read'});assert(!system(f.requests.at(-1)).includes('PREFIX_'));assert(!system(f.requests.at(-1)).includes('SUFFIX_'));assert(!JSON.stringify(f.requests.at(-1).messages.filter(row=>row.role==='user')).includes('PREFIX_'),'submitted user text stays distinct from system sections');assert.equal(f.errors(),'');
});

test('literal sections reach both managed Browser conversations and distinct bounded agent workers without expanding their grants',{timeout:60000},async t=>{
 const f=await planFixture(t,{jobMode:{}});await preferences(f,'promptPrefix','SCOPE_PREFIX');await preferences(f,'promptSuffix','SCOPE_SUFFIX');
 for(const [sid,surface] of [['scope-root','linux'],['scope-browser','browser']]){await f.call('session.create',{sessionId:sid,surface,selection:f.selection,cwd:f.workspace});await f.prompt(sid,{kind:'worker-reply'});}
 const started=await f.call('session.startJob',{sessionId:'scope-root',spec:{requestId:crypto.randomUUID(),kind:'delegate',task:JSON.stringify({kind:'worker-reply'}),allowedTools:[]}});let job;await until(async()=>{job=(await f.call('session.job',{sessionId:'scope-root',jobId:started.job.id})).job;return job.state==='completed';},'worker settled');
 assert.equal(f.requests.length,3,f.errors());for(const body of f.requests){assert(system(body).startsWith('SCOPE_PREFIX\n\n'));assert(system(body).endsWith('SCOPE_SUFFIX'));}assert(!f.requests[2].tools?.length,'wrapping cannot add a callable tool to the worker');
 for(const sid of ['scope-root','scope-browser',job.childId]){assert(!(await f.native(sid)).bytes.includes('SCOPE_PREFIX'));assert.equal((await evidence(f,sid))[0].snapshots.promptWrapping.revision,2);}
});

test('the real bounded desktop specialist keeps its tool/evidence ownership while recording literal prompt sections in its own request scope',{timeout:60000},async t=>{
 const f=await planFixture(t,{desktopMode:{}}),sid='desktop-wrapping-parent';await preferences(f,'promptPrefix','DESKTOP_PREFIX');await preferences(f,'promptSuffix','DESKTOP_SUFFIX');await f.call('session.create',{sessionId:sid,selection:f.selection,cwd:f.workspace});
 await f.prompt(sid,{kind:'desktop-parent',brief:{task:'Synthetic click',successCriteria:'Synthetic post-action observation',constraints:'Authored private peer only.'}});const jobs=(await f.call('session.jobs',{sessionId:sid})).items;const job=jobs.find(row=>row.kind==='desktop');assert(job?.childId,f.errors());assert.equal(job.state,'completed');
 assert(f.requests.some(body=>body.tools?.some(tool=>tool.function.name==='desktop_finish')));for(const body of f.requests){assert(system(body).startsWith('DESKTOP_PREFIX\n\n'));assert(system(body).endsWith('DESKTOP_SUFFIX'));}
 const records=await evidence(f,job.childId);assert(records.length>=4);for(const row of records)assert.equal(row.snapshots.promptWrapping.revision,2);assert(!(await f.native(job.childId)).bytes.includes('DESKTOP_PREFIX'));assert.equal(f.desktop.calls.filter(row=>row.method==='action').length,1);
});
