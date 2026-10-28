// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {sessionFamily} from '../dist/runtime/src/session-family.js';

test('family identities require both saved authorities and preserve unknown outcomes without borrowing forks, shells, task bodies or usage',{timeout:1000},()=>{
 const root={id:'parent',title:'Authored parent',cwd:'/authored',running:false,updatedAt:1};
 const meta=new Map([
  ['good',{id:'good',title:'Authored worker',cwd:'/authored',running:true,updatedAt:2,delegation:{parentId:'parent',jobId:'owned'}}],
  ['wrong',{id:'wrong',title:'Foreign worker secret',cwd:'/foreign',running:false,updatedAt:2,delegation:{parentId:'foreign',jobId:'wrong'}}],
  ['branch',{id:'branch',title:'Ordinary branch',cwd:'/authored',running:false,updatedAt:2,fork:{sessionId:'parent'}}],
 ]);
 const job=(id,childId,patch={})=>({id,owner:'parent',kind:'delegate',childId,state:'unknown',createdAt:1,updatedAt:3,requests:2,tools:1,outputTokens:8,...patch});
 const rows=[job('owned','good',{task:'Hidden task body',output:'Hidden result',usage:{private:'Hidden usage'},usageRecorded:true,usageAccounted:true}),job('wrong','wrong'),job('branch','branch'),job('shell',undefined,{kind:'shell'}),job('pending',undefined,{state:'starting'}),job('missing','missing'),job('duplicate','good')];
 const before=structuredClone({root,rows,meta:[...meta]});const value=sessionFamily(root,rows,id=>meta.get(id));
 assert.equal(value.available,true);assert.deepEqual(value.items.map(row=>row.sessionId),['parent','good']);assert.equal(value.items[1].reportedState,'unknown');assert.equal(value.items[1].running,false,'the durable recovered job overrides stale metadata running');assert.equal(value.items[1].usageAccounted,true);assert.equal(value.items[1].usageRecorded,true);
 assert.deepEqual(value.coverage,{retainedJobs:7,agentJobs:6,verifiedChildren:1,pendingChildren:1,unavailableChildren:4,historicalCompleteness:'not-established; removed receipts are not rediscovered',completion:'reported producer disposition; task success is not established'});
 assert(!/Hidden|Foreign worker secret|Ordinary branch|\/foreign/.test(JSON.stringify(value)));assert.deepEqual({root,rows,meta:[...meta]},before,'reading neither mutates nor accounts work');
 const unavailable=sessionFamily(root,rows,id=>meta.get(id),'Authored unavailable catalogue');assert.equal(unavailable.available,false);assert.equal(unavailable.coverage,null);assert.deepEqual(unavailable.items,[]);
 assert.throws(()=>sessionFamily(root,[job('foreign','good',{owner:'foreign'})],id=>meta.get(id)),/another conversation/);
 assert.throws(()=>sessionFamily({...root,delegation:{parentId:'outer',jobId:'outer-job'}},[],()=>undefined),/parent job/);
 const invalid=sessionFamily(root,[job('owned','good',{requests:NaN,tools:-1,outputTokens:'unreported'})],id=>meta.get(id));for(const key of ['reportedRequests','reportedTools','reportedOutputTokens'])assert.equal(invalid.items[1][key],null,'invalid counters must not become observed zero');
});
