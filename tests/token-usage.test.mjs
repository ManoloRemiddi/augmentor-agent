// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,rmSync,symlinkSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {zstdCompressSync} from 'node:zlib';
import {collectUsage} from '../services/usage/history.mjs';

const now=Date.parse('2026-10-02T12:00:00Z'),time=Date.parse('2026-10-01T12:00:00Z');
const usage={inputTokens:80,outputTokens:20,totalTokens:100,cacheReadTokens:30};
const event=(seq,u=usage)=>({type:'assistant/message',seq,time,data:{usage:u,message:{content:[{type:'text',text:'Synthetic fixture'}]}}});
function fixture(t){const root=mkdtempSync(join(tmpdir(),'augmentor-usage-'));t.after(()=>rmSync(root,{recursive:true,force:true}));return root;}
function file(path,value){mkdirSync(join(path,'..'),{recursive:true});writeFileSync(path,typeof value==='string'?value:JSON.stringify(value));}
function journal(home,id,rows,{seeded=false,preset='augmentor-linux-product',compressed=true}={}){
 const header={type:'session',version:3,id,isSeeded:seeded,agentPreset:preset};
 const lines=[header,...rows].map(r=>JSON.stringify(r)+'\n');
 const path=join(home,'sessions','cwd',id,'session.v3.jsonl');mkdirSync(join(path,'..'),{recursive:true});
 writeFileSync(compressed?path+'.zstd':path,compressed?Buffer.concat(lines.map(l=>zstdCompressSync(Buffer.from(l)))):lines.join(''));
 return path;
}
test('DSH counts reported totals/cache once across concatenated frames and seeded forks; other roles excluded',t=>{
 const root=fixture(t);const plain=journal(root,'original',[event(1)]);file(plain,'{"broken":true}\n');
 journal(root,'branch',[event(1),{type:'session/end-seed',seq:2},event(3,{inputTokens:40,outputTokens:10,totalTokens:50})],{seeded:true});
 journal(root,'foreign',[event(1)],{preset:'ptc'});
 const v=collectUsage({dshHome:root,now});assert.equal(v.total,150);assert.equal(v.records,2);assert.equal(v.days[0].cached,30);assert.deepEqual(v.sources,['DSH']);assert.equal(v.incomplete,0);
});
test('missing/invalid usage is unavailable; dated scope excludes old/future records',t=>{
 const root=fixture(t);journal(root,'original',[event(1),event(2),event(3,{inputTokens:80,outputTokens:20,totalTokens:-1}),{...event(4),time:Date.parse('2024-10-01')},{...event(5),time:Date.parse('2027-10-01')}]);
 const v=collectUsage({dshHome:root,now});assert.equal(v.total,200);assert.equal(v.records,2);assert.equal(v.incomplete,1);
 // Explicit missing metadata must not be synthesized from chat text.
 journal(root,'missing',[{...event(1),data:{message:{content:[{type:'text',text:'Synthetic text'}]}}}]);
 const missing=collectUsage({dshHome:root,now});assert.equal(missing.total,200);assert.equal(missing.incomplete,2);
});
test('Pi reads only registered in-state SDK journals and deduplicates inherited entries',t=>{
 const root=fixture(t),sessions=join(root,'sessions');
 const row={type:'message',id:'reply',timestamp:'2026-10-01T12:00:00Z',message:{role:'assistant',usage:{input:80,output:20,cacheRead:30,totalTokens:130}}};
 for(const id of ['parent','branch']){const path=join(sessions,id,'native.jsonl');file(path,JSON.stringify(row)+'\n');file(join(sessions,id+'.meta.json'),{file:path});}
 const outside=join(root,'outside.jsonl');file(outside,JSON.stringify(row)+'\n');file(join(sessions,'foreign.meta.json'),{file:outside});
 mkdirSync(join(sessions,'linked'),{recursive:true});symlinkSync(outside,join(sessions,'linked','native.jsonl'));file(join(sessions,'linked.meta.json'),{file:join(sessions,'linked','native.jsonl')});
 const v=collectUsage({piState:root,now});assert.equal(v.total,130);assert.equal(v.records,1);assert.equal(v.days[0].cached,30);assert.equal(v.incomplete,2);
});
test('Codex cumulative notifications count increments once, including inherited native rollouts',t=>{
 const root=fixture(t);const row=(total,delta,when)=>({timestamp:when,type:'event_msg',payload:{type:'token_count',info:{total_token_usage:{total_tokens:total,input_tokens:total-20,output_tokens:20},last_token_usage:{total_tokens:delta,input_tokens:delta-10,output_tokens:10,cached_input_tokens:5}}}});
 const a=row(100,100,'2026-10-01T12:00:00Z'),b=row(150,50,'2026-10-01T13:00:00Z');
 for(const id of ['parent','branch']){file(join(root,'sessions',id+'.json'),{id,status:'ready'});file(join(root,'threads',id,'runtime','sessions','2026','rollout.jsonl'),[a,b,b,...(id==='branch'?[row(200,50,'2026-10-01T14:00:00Z')]:[])].map(r=>JSON.stringify(r)+'\n').join(''));}
 const v=collectUsage({codexState:root,now});assert.equal(v.total,200);assert.equal(v.records,3);assert.equal(v.incomplete,0);assert.deepEqual(v.sources,['Codex']);
});
test('torn native final writes preserve committed usage; scan budgets report partial coverage',t=>{
 const root=fixture(t);journal(root,'plain',[event(1)],{compressed:false});
 const path=join(root,'sessions','cwd','plain','session.v3.jsonl');file(path,[{type:'session',version:3,id:'plain',isSeeded:false,agentPreset:'augmentor-browser-product'},event(1)].map(r=>JSON.stringify(r)+'\n').join('')+'{"unfinished":');
 const v=collectUsage({dshHome:root,now});assert.equal(v.total,100);assert.equal(v.incomplete,1);
 const limited=collectUsage({dshHome:root,now,milliseconds:-1});assert.equal(limited.total,0);assert.equal(limited.incomplete,1);
});
test('empty state returns an empty recorded calendar without fabricated counts',()=>{
 const v=collectUsage({now});assert.equal(v.total,0);assert.deepEqual(v.days,[]);assert.equal(v.records,0);assert.equal(v.incomplete,0);
});

test('unsafe accumulated counts are excluded atomically rather than corrupting a calendar day',t=>{
 const root=fixture(t);journal(root,'large',[event(1,{inputTokens:1,outputTokens:1,totalTokens:Number.MAX_SAFE_INTEGER}),event(2)]);
 const v=collectUsage({dshHome:root,now});assert.equal(v.total,Number.MAX_SAFE_INTEGER);assert.equal(v.days[0].input,1);assert.equal(v.days[0].output,1);assert.equal(v.records,1);assert.equal(v.incomplete,1);
});
