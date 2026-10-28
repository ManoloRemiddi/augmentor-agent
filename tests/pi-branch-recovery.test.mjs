// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,readFile,writeFile,chmod,stat,rm,symlink,link,unlink} from 'node:fs/promises';
import {existsSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const runtimeRoot=process.env.AUGMENTOR_PI_TEST_ROOT??fileURLToPath(new URL('..',import.meta.url));
const {BranchIntents}=await import(pathToFileURL(join(runtimeRoot,'dist/runtime/src/branch-intents.js')));
const {inspectBranchContext}=await import(pathToFileURL(join(runtimeRoot,'dist/runtime/src/branches.js')));
const {privateDir}=await import(pathToFileURL(join(runtimeRoot,'dist/runtime/src/storage.js')));
import {CURRENT_SESSION_VERSION} from '@earendil-works/pi-coding-agent';
async function fixture(t){const root=await mkdtemp(join(tmpdir(),'augmentor-branch-recovery-'));t.after(async()=>{await chmod(join(root,'state'),0o700).catch(()=>{});await rm(root,{recursive:true,force:true});});const state=join(root,'state');privateDir(state);const file=join(state,'branch-intents.json');return {root,state,file,store:new BranchIntents(file)};}
const boundary={sessionId:'parent',messageSeq:8,mode:'reply'};
test('branch identities survive a fresh reader and creating phase, while reads create no record or conversation',async t=>{
 const {state,file,store}=await fixture(t);assert.deepEqual(store.list(),[]);assert.equal(existsSync(file),false);
 const first=store.reserve(boundary,'child-one');assert.deepEqual(first,{...boundary,newSessionId:'child-one'});assert.deepEqual(new BranchIntents(file).reserve(boundary,'must-not-replace'),first);
 store.begin(first);const cold=new BranchIntents(file);assert.equal(cold.list()[0].phase,'creating');assert.deepEqual(cold.reserve(boundary,'must-not-replace'),first);assert.equal(existsSync(join(state,'sessions')),false);
 if(process.platform!=='win32')assert.equal((await stat(file)).mode&0o777,0o600);
});
test('exact-boundary settlement never clears a newer intent or another session/sequence/mode',async t=>{
 const {file,store}=await fixture(t),a=store.reserve(boundary,'child-a'),other={...boundary,messageSeq:9};store.reserve(other,'child-other');store.begin(a);assert.equal(new BranchIntents(file).settle(a),true);
 const newer=store.reserve(boundary,'child-new');assert.equal(store.settle(a),false);assert.equal(store.settle({...newer,mode:'edit'}),false);assert.equal(store.settle({...newer,sessionId:'foreign'}),false);assert.equal(store.settle({...newer,messageSeq:99}),false);
 assert.deepEqual(store.list().map(x=>x.newSessionId),['child-other','child-new']);assert.deepEqual(store.reserve(boundary,'not-used'),newer);assert.throws(()=>store.begin(a),/no longer current/);
});
test('separate journal readers retain peer operations and do not restore discarded snapshots',async t=>{
 const {file,store}=await fixture(t),peer=new BranchIntents(file),a=store.reserve(boundary,'child-a'),b=peer.reserve({...boundary,sessionId:'peer'},'child-b');store.begin(a);peer.begin(b);store.settle(a);
 assert.deepEqual(peer.list(),[{...b,phase:'creating'}]);assert.deepEqual(new BranchIntents(file).list(),peer.list());
});
test('pending bounds refuse new boundaries without eviction and still reconcile a retained identity',async t=>{
 const {file,store}=await fixture(t);for(let n=1;n<=64;n++)store.reserve({...boundary,messageSeq:n},'child-'+n);const original=await readFile(file,'utf8');
 assert.throws(()=>store.reserve({...boundary,messageSeq:65},'overflow'),/none were discarded/);assert.equal(await readFile(file,'utf8'),original);assert.equal(store.reserve({...boundary,messageSeq:8},'replacement').newSessionId,'child-8');
 assert.throws(()=>store.reserve({...boundary,messageSeq:0},'invalid'),/Invalid branch/);assert.throws(()=>store.reserve({...boundary,mode:'foreign'},'invalid'),/Invalid branch/);assert.throws(()=>store.begin({...boundary,newSessionId:'parent'}),/own conversation/);assert.equal(await readFile(file,'utf8'),original);
});
test('a failed durable write preserves the committed reservation and never claims a new identity',{skip:process.platform==='win32'||process.getuid?.()===0},async t=>{
 const {file,state,store}=await fixture(t);store.reserve(boundary,'child-a');const original=await readFile(file,'utf8');await chmod(state,0o500);t.after(()=>chmod(state,0o700).catch(()=>{}));
 assert.throws(()=>store.reserve({...boundary,messageSeq:9},'child-b'),/EACCES|permission/i);assert.equal(await readFile(file,'utf8'),original);await chmod(state,0o700);assert.deepEqual(new BranchIntents(file).list().map(x=>x.newSessionId),['child-a']);
});
test('corrupt, duplicate, oversized and foreign-schema records fail closed without leaking their body or replacing originals',async t=>{
 const {file,store}=await fixture(t),row={...boundary,newSessionId:'child-a',phase:'prepared'};
 for(const text of ['SECRET_PRIVATE_BODY not JSON',JSON.stringify({schema:'foreign',pending:[]}),JSON.stringify({schema:'augmentor-branch-intents/1',pending:[row,row]}),JSON.stringify({schema:'augmentor-branch-intents/1',pending:[{...row,content:'PRIVATE_PROMPT'}]}),' '.repeat(65537)]){
  await writeFile(file,text,{mode:0o600});assert.throws(()=>store.reserve(boundary,'new-child'),error=>{assert(!error.message.includes('SECRET_PRIVATE_BODY'));assert(!error.message.includes('PRIVATE_PROMPT'));return true;});assert.equal(await readFile(file,'utf8'),text);
 }
});
test('links, hardlinks and public records cannot redirect branch recovery',{skip:process.platform==='win32'},async t=>{
 const {root,file,store}=await fixture(t),outside=join(root,'outside.json');await writeFile(outside,'Private external original.',{mode:0o600});await symlink(outside,file);assert.throws(()=>store.list(),/private bounded/);assert.equal(await readFile(outside,'utf8'),'Private external original.');await unlink(file);
 await symlink(join(root,'missing'),file);assert.throws(()=>store.reserve(boundary,'child-a'),/private bounded/);assert.equal(existsSync(join(root,'missing')),false);await unlink(file);
 store.reserve(boundary,'child-a');const original=await readFile(file,'utf8');await link(file,join(root,'second-link'));assert.throws(()=>store.begin({...boundary,newSessionId:'child-a'}),/private bounded/);assert.equal(await readFile(file,'utf8'),original);await unlink(join(root,'second-link'));await chmod(file,0o644);assert.throws(()=>store.list(),/private bounded/);assert.equal(await readFile(file,'utf8'),original);
});
test('a linked profile directory remains untouched by record preparation',{skip:process.platform==='win32'},async t=>{
 const {root,state}=await fixture(t),outside=join(root,'outside');await mkdir(outside,{mode:0o755});const alias=join(root,'alias');await symlink(outside,alias);const store=new BranchIntents(join(alias,'branch-intents.json')),before=(await stat(outside)).mode;
 assert.throws(()=>store.reserve(boundary,'child-a'),/private profile directory/);assert.equal((await stat(outside)).mode,before);assert.equal(existsSync(join(outside,'branch-intents.json')),false);assert.notEqual(state,outside);
});

test('branch preparation refuses SDK header migration before opening a source and preserves its exact bytes',async t=>{
 const {root}=await fixture(t),file=join(root,'older-native.jsonl'),original=JSON.stringify({type:'session',version:CURRENT_SESSION_VERSION-1,id:'authored-source',cwd:root})+'\n';await writeFile(file,original,{mode:0o600});
 const events=[{seq:8,type:'assistant/message',data:{message:{content:[{type:'text',text:'Authored reply.'}]}}}];assert.throws(()=>inspectBranchContext(file,root,events,8,'reply'),/reviewed migration/);assert.equal(await readFile(file,'utf8'),original);
});
