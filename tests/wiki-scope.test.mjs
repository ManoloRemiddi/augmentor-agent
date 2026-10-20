import {realpathSync as wikiRealpathSync} from 'node:fs';
// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,chmod,symlink,link,rm,readdir} from 'node:fs/promises';
import {join} from 'node:path';import {tmpdir} from 'node:os';
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {withWikiFs,readFile as guardedRead,writeFile as guardedWrite} from '../dist/runtime/src/wiki-fs.js';
import {WikiBinding,wikiConfig} from '../dist/runtime/src/wiki.js';
async function fixture(t){const base=await mkdtemp(join(wikiRealpathSync(tmpdir()),'augmentor-wiki-scope-'));t.after(()=>rm(base,{recursive:true,force:true}));const root=join(base,'vault'),outside=join(base,'outside');await mkdir(root);await mkdir(outside);await writeFile(join(outside,'secret.md'),'AUTHORED OUTSIDE BYTES');return {base,root,outside};}
test('Wiki IO cannot follow linked parents/leaves, shared hardlinks or outside roots and read scope cannot write',{skip:!['linux','darwin'].includes(process.platform)},async t=>{
 const {root,outside}=await fixture(t);await symlink(outside,join(root,'wiki'));await symlink(join(outside,'secret.md'),join(root,'leaf.md'));await link(join(outside,'secret.md'),join(root,'hard.md'));
 for(const path of [join(root,'wiki/secret.md'),join(root,'leaf.md'),join(root,'hard.md'),join(outside,'secret.md')])await assert.rejects(withWikiFs(root,false,undefined,()=>guardedRead(path,'utf8')));
 await assert.rejects(withWikiFs(root,false,undefined,()=>guardedWrite(join(root,'new.md'),'not admitted')),/cannot change/);assert.equal(await readFile(join(outside,'secret.md'),'utf8'),'AUTHORED OUTSIDE BYTES');assert.deepEqual((await readdir(root)).sort(),['hard.md','leaf.md','wiki']);
});
test('archive collisions preserve both originals; the uncertainty receipt survives a fresh binding and blocks another mutation',{skip:!['linux','darwin'].includes(process.platform)},async t=>{
 const {base,root}=await fixture(t);await mkdir(join(root,'.raw'));await mkdir(join(root,'.archive'));await writeFile(join(root,'.raw/source.txt'),'NEW AUTHORED SOURCE');await writeFile(join(root,'.archive/source.txt'),'OLDER AUTHORED ARCHIVE');
 const config={enabled:true,vaultPath:root,maxQueryResults:10,typeFolders:{}},state=join(base,'state');const manager=SessionManager.inMemory(root);
 const tools=new Map(),binding=new WikiBinding(config,state);binding.factory({on:()=>{},registerTool:tool=>tools.set(tool.name,tool)});
 const ctx={sessionManager:manager};const assistant=(id,name,args)=>manager.appendMessage({role:'assistant',content:[{type:'toolCall',id,name,arguments:args}],api:'openai-completions',provider:'fixture',model:'fixture',usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}},stopReason:'toolUse',timestamp:Date.now()});
 const args={source_path:'.raw/source.txt'},archiveEntry=assistant('archive-one','wiki_archive',args);const result=await tools.get('wiki_archive').execute('archive-one',args,undefined,undefined,ctx);assert.equal(result.isError,true);assert.equal(result.details.outcome,'unknown');assert.match(result.content[0].text,/different bytes/);
 assert.equal(await readFile(join(root,'.raw/source.txt'),'utf8'),'NEW AUTHORED SOURCE');assert.equal(await readFile(join(root,'.archive/source.txt'),'utf8'),'OLDER AUTHORED ARCHIVE');
 const fresh=new Map();new WikiBinding(config,state).factory({on:()=>{},registerTool:tool=>fresh.set(tool.name,tool)});const input={type:'concept',title:'Not Replayed',content:'MUST NOT WRITE'};assistant('write-next','wiki_write',input);const blocked=await fresh.get('wiki_write').execute('write-next',input,undefined,undefined,ctx);assert.equal(blocked.isError,true);assert.match(blocked.content[0].text,/uncertain/);assert.equal((await readdir(root)).includes('wiki'),false);
 const view=binding.receipts.describe(),row=view.rows.find(r=>r.state==='unknown'),path=join(binding.receipts.root,row.key+'.json'),original=await readFile(path);binding.receipts.review({key:row.key,sha256:row.sha256,expectedRevision:view.revision,acknowledgeUnknownOutcome:true,reviewId:crypto.randomUUID()});manager.branch(archiveEntry);
 const replay=await fresh.get('wiki_archive').execute('archive-one',args,undefined,undefined,ctx);assert.equal(replay.isError,true);assert.match(replay.content[0].text,/not replayed/);assert.deepEqual(await readFile(path),original);assert.equal(await readFile(join(root,'.raw/source.txt'),'utf8'),'NEW AUTHORED SOURCE');assert.equal(await readFile(join(root,'.archive/source.txt'),'utf8'),'OLDER AUTHORED ARCHIVE');
});
test('explicit private Wiki configuration preserves unsafe originals and never infers a vault',{skip:!['linux','darwin'].includes(process.platform)},async t=>{
 const {base,root,outside}=await fixture(t);const cfg=join(base,'config');await mkdir(cfg);assert.equal(wikiConfig(cfg),undefined);
 const p=join(cfg,'wiki.json'),content=JSON.stringify({schema:'augmentor-wiki/1',enabled:true,vaultPath:root});await writeFile(p,content,{mode:0o644});await chmod(p,0o644);assert.throws(()=>wikiConfig(cfg),/unsafe/);assert.equal(await readFile(p,'utf8'),content);await rm(p);await symlink(join(outside,'secret.md'),p);assert.throws(()=>wikiConfig(cfg),/unsafe/);await rm(p);await writeFile(p,content,{mode:0o600});assert.equal(wikiConfig(cfg).vaultPath,root);
});

test('a completed native Wiki action cannot replay with altered arguments but a new native entry may reuse the SDK call ID',{skip:!['linux','darwin'].includes(process.platform)},async t=>{
 const {base,root}=await fixture(t),config={enabled:true,vaultPath:root,maxQueryResults:10,typeFolders:{}},state=join(base,'state'),manager=SessionManager.inMemory(root),tools=new Map();new WikiBinding(config,state).factory({on:()=>{},registerTool:tool=>tools.set(tool.name,tool)});
 const id='same-sdk-id',args={mode:'generic',purpose:'AUTHORED FIRST PURPOSE'},ctx={sessionManager:manager};
 const append=input=>manager.appendMessage({role:'assistant',content:[{type:'toolCall',id,name:'wiki_scaffold',arguments:input}],api:'openai-completions',provider:'fixture',model:'fixture',usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}},stopReason:'toolUse',timestamp:Date.now()});
 append(args);const first=await tools.get('wiki_scaffold').execute(id,args,undefined,undefined,ctx);assert.equal(first.isError,undefined);
 const path=join(root,'wiki/overview.md'),before=await readFile(path);const changed={...args,purpose:'MUST NOT REPLAY THIS NATIVE CALL'};const replay=await tools.get('wiki_scaffold').execute(id,changed,undefined,undefined,ctx);assert.equal(replay.isError,true);assert.match(replay.content[0].text,/not replayed/);assert.deepEqual(await readFile(path),before);
 append(changed);const fresh=await tools.get('wiki_scaffold').execute(id,changed,undefined,undefined,ctx);assert.equal(fresh.isError,undefined);assert(fresh.details.value.skipped.length>0,'a distinct native call retains the supplier scaffold idempotence');assert.deepEqual(await readFile(path),before);
});
