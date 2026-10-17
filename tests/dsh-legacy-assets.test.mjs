// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Data reader units; actual codec/recomputation admission is covered by the
// separate authored public-source pipeline, not these deliberately small views.
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,rm,symlink} from 'node:fs/promises';
import {join} from 'node:path';import {tmpdir} from 'node:os';import {spawnSync} from 'node:child_process';
import {assetInventory,verifyAssets} from '../adapters/dsh-legacy-format/assets.mjs';
import {hash} from '../adapters/dsh-legacy-format/source.mjs';
async function fixture(t){
 const base=await mkdtemp(join(tmpdir(),'augmentor-historical-assets-'));t.after(()=>rm(base,{recursive:true,force:true}));const view=join(base,'view'),assets=join(base,'assets');for(const dir of [view,assets]){await mkdir(dir);await mkdir(join(dir,'objects'));}
 const put=async(root,raw)=>{const ref={sha256:hash(raw),bytes:raw.length};await writeFile(join(root,'objects',ref.sha256),raw);return ref;};
 const file=Buffer.from('Authored binary\0\xff'),image=Buffer.from('Authored image bytes'),empty=Buffer.alloc(0),part=(type,raw)=>({type,attachment:{attachmentId:'sha256:'+hash(raw),bytes:raw.length,name:'Authored'}}),filePart=part('file',file),imagePart=part('image',image),emptyPart=part('file',empty),events=[{type:'user/message',seq:0,data:{content:[filePart,emptyPart]}},{type:'user/message',seq:0,data:{content:[imagePart,imagePart]}}];
 const nodes=[];for(const [i,id] of ['root','child'].entries())nodes.push({sourceId:id,eventCount:1,header:await put(view,Buffer.from(JSON.stringify({id}))),segments:[{...await put(view,Buffer.from(JSON.stringify([events[i]]))),firstSeq:0,count:1}]});
 const original=await put(view,Buffer.from('Authored retained source chunk')),source=Buffer.from(JSON.stringify({nodes:[{chunks:[original]}]}));await writeFile(join(view,'source-family.json'),source);for(const name of ['FORMAT-LICENSE','SCHEMA-REFERENCE-LICENSE','SOURCES.json'])await writeFile(join(view,name),'Authored notice');const manifest={schema:'augmentor-dsh-offline-project-view/1',historicalOnly:true,sourceFamilySha256:hash(source),nodes};await writeFile(join(view,'view.json'),JSON.stringify(manifest));
 const {inventory}=await assetInventory(view),rows=[];for(const row of inventory.requests){const raw=row.kind==='image'?image:row.bytes?file:empty;rows.push({...row,chunks:raw.length?[await put(assets,raw)]:[]});}
 const companion={schema:'augmentor-dsh-historical-assets/1',inventory,assets:rows,currentHarnessImportCompatible:false,workingFilesCaptured:false};await writeFile(join(assets,'assets.json'),JSON.stringify(companion));return {base,view,assets,manifest,companion,file,image,events,put};
}
test('asset inventory keeps exact child-only occurrences, deduplicated objects and empty files',async t=>{const f=await fixture(t),checked=await verifyAssets(f.view,f.assets);assert.equal(checked.objects.size,2);assert.equal(checked.manifest.assets.length,3);const references=checked.manifest.inventory.references;assert.equal(references.length,4);assert(references.filter(r=>r.kind==='image').every(r=>r.sourceId==='child'));assert.deepEqual(checked.manifest.assets.find(r=>r.bytes===0).chunks,[]);});
for(const [name,alter] of [
 ['foreign source ownership',f=>{f.companion.inventory.references[2].sourceId='root';}],
 ['wrong source cut',f=>{f.companion.inventory.references[0].seq=1;}],
 ['wrong content index',f=>{f.companion.inventory.references[0].partIndex=2;}],
 ['different view fingerprint',f=>{f.companion.inventory.viewSha256='a'.repeat(64);}],
 ['different original-family fingerprint',f=>{f.companion.inventory.sourceFamilySha256='a'.repeat(64);}],
 ['inferred native compatibility',f=>{f.companion.currentHarnessImportCompatible=true;}],
 ['claimed working folder capture',f=>{f.companion.workingFilesCaptured=true;}],
 ['missing asset metadata',f=>{f.companion.assets.pop();}],
 ['foreign asset identity',f=>{f.companion.assets[0].attachmentId='sha256:'+'f'.repeat(64);}],
 ['mismatched asset size',f=>{f.companion.assets[0].bytes++;}],
 ['zero-length object',f=>{f.companion.assets[0].chunks[0].bytes=0;}],
 ['path traversal object',f=>{f.companion.assets[0].chunks[0].sha256='../foreign';}],
 ['extra asset key',f=>{f.companion.assets[0].execute=true;}],
])test('asset verifier refuses '+name,async t=>{const f=await fixture(t);alter(f);await writeFile(join(f.assets,'assets.json'),JSON.stringify(f.companion));await assert.rejects(()=>verifyAssets(f.view,f.assets));});
test('a matching chunk checksum cannot replace the complete referenced asset digest',async t=>{const f=await fixture(t),row=f.companion.assets[0],forged=Buffer.alloc(row.bytes,90),ref=await f.put(f.assets,forged);row.chunks=[ref];await writeFile(join(f.assets,'assets.json'),JSON.stringify(f.companion));await assert.rejects(()=>verifyAssets(f.view,f.assets),/complete asset checksum/);});
test('unreferenced asset bytes refuse',async t=>{const f=await fixture(t);await f.put(f.assets,Buffer.from('unrelated private bytes'));await assert.rejects(()=>verifyAssets(f.view,f.assets),/unreferenced/);});
for(const kind of ['missing','changed','symlink','FIFO'])test('asset '+kind+' refuses without changing source view', {skip:process.platform!=='linux'},async t=>{const f=await fixture(t),before=await readFile(join(f.view,'view.json')),path=join(f.assets,'objects',f.companion.assets[0].chunks[0].sha256);await rm(path);if(kind==='changed')await writeFile(path,Buffer.from('changed'));if(kind==='symlink')await symlink(join(f.view,'view.json'),path);if(kind==='FIFO')assert.equal(spawnSync('mkfifo',[path]).status,0);await assert.rejects(()=>verifyAssets(f.view,f.assets));assert.deepEqual(await readFile(join(f.view,'view.json')),before);});
for(const [name,change] of [
 ['malformed identity',p=>{p.attachment.attachmentId='../foreign';}],
 ['boolean size',p=>{p.attachment.bytes=true;}],
 ['oversized file',p=>{p.attachment.bytes=20*1024*1024+1;}],
 ['negative size',p=>{p.attachment.bytes=-1;}],
])test('inventory refuses '+name,async t=>{const f=await fixture(t);change(f.events[0].data.content[0]);const ref=await f.put(f.view,Buffer.from(JSON.stringify([f.events[0]])));f.manifest.nodes[0].segments=[{...ref,firstSeq:0,count:1}];await writeFile(join(f.view,'view.json'),JSON.stringify(f.manifest));await assert.rejects(()=>assetInventory(f.view));});
test('segment coordinate gaps are refused',async t=>{const f=await fixture(t);f.manifest.nodes[0].segments[0].firstSeq=1;await writeFile(join(f.view,'view.json'),JSON.stringify(f.manifest));await assert.rejects(()=>assetInventory(f.view),/coverage/);});
