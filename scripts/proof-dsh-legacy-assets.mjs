// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Full source-codec -> view -> exact asset pipeline using authored data only.
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,readdir,rm,rename,lstat} from 'node:fs/promises';
import {resolve,join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {authoredLegacySource} from '../adapters/dsh-legacy-format/authored-source.mjs';
import {hash} from '../adapters/dsh-legacy-format/source.mjs';
const [sourceArg,outputArg,...extra]=process.argv.slice(2);if(!sourceArg||!outputArg||extra.length)throw Error('Usage: node scripts/proof-dsh-legacy-assets.mjs PINNED_PUBLIC_SOURCE NEW_PRIVATE_PROOF');if(process.platform!=='linux')throw Error('MX Linux proof');process.umask(0o077);
const repo=fileURLToPath(new URL('../',import.meta.url)),source=resolve(sourceArg),output=resolve(outputArg);try{await lstat(output);throw Error('Proof output exists');}catch(e){if(e.code!=='ENOENT')throw e;}
const stage=await mkdtemp(join(dirname(output),'.dsh-asset-proof-'));let checks=0;
const run=(script,args)=>spawnSync(process.execPath,[join(repo,'scripts',script),...args],{encoding:'utf8',timeout:180000,maxBuffer:1024*1024}),ok=proc=>{assert.equal(proc.status,0,proc.stderr);return JSON.parse(proc.stdout.trim().split('\n').at(-1));};
try{
 const {home,frozen,view,assets,cwd,image,file,empty,assetRows,rootId,childId,nodes}=await authoredLegacySource(stage);
 ok(run('export-dsh-legacy-view.mjs',[source,frozen,view]));const viewBefore=await readFile(join(view,'view.json'));const captured=ok(run('capture-dsh-legacy-assets.mjs',[source,view,home,assets]));assert.equal(captured.images,1);assert.equal(captured.files,2);assert.equal(captured.references,4);assert.equal(captured.assetBytes,file.length+image.length);checks++;
 const raw=await readFile(join(assets,'assets.json')),manifest=JSON.parse(raw),big=manifest.assets.find(r=>r.bytes===file.length),zero=manifest.assets.find(r=>r.bytes===0),childRefs=manifest.inventory.references.filter(r=>r.kind==='image');assert.deepEqual(big.chunks.map(r=>r.bytes),[8*1024*1024,8*1024*1024,4*1024*1024]);assert.deepEqual(zero.chunks,[]);assert(childRefs.every(r=>r.sourceId===childId));assert.equal(childRefs.length,2);checks++;
 const saved=home+'-retained';await rename(home,saved);ok(run('verify-dsh-legacy-assets.mjs',[source,view,assets]));await rename(saved,home);checks++;
 const object=join(assets,'objects',big.chunks[0].sha256),before=await readFile(object);await writeFile(object,Buffer.alloc(before.length,90));assert.notEqual(run('verify-dsh-legacy-assets.mjs',[source,view,assets]).status,0);await writeFile(object,before);checks++;
 manifest.inventory.references.find(r=>r.kind==='image').sourceId=rootId;await writeFile(join(assets,'assets.json'),JSON.stringify(manifest));assert.notEqual(run('verify-dsh-legacy-assets.mjs',[source,view,assets]).status,0);await writeFile(join(assets,'assets.json'),raw);checks++;
 await rename(assetRows[2].path,assetRows[2].path+'.saved');const missing=join(stage,'missing');assert.notEqual(run('capture-dsh-legacy-assets.mjs',[source,view,home,missing]).status,0);await assert.rejects(()=>lstat(missing),e=>e.code==='ENOENT');await rename(assetRows[2].path+'.saved',assetRows[2].path);checks++;
 assert.notEqual(run('capture-dsh-legacy-assets.mjs',[source,view,home,assets]).status,0);assert.deepEqual(await readFile(join(assets,'assets.json')),raw);const inside=join(home,'must-not-write');assert.notEqual(run('capture-dsh-legacy-assets.mjs',[source,view,home,inside]).status,0);await assert.rejects(()=>lstat(inside),e=>e.code==='ENOENT');checks++;
 assert.deepEqual(await readFile(join(view,'view.json')),viewBefore);for(const row of assetRows)assert.deepEqual(await readFile(row.path),row.raw);ok(run('verify-dsh-legacy-assets.mjs',[source,view,assets]));assert(!(await readdir(stage)).some(n=>n.startsWith('.dsh-historical-assets-')));checks++;
 const {importDshProject}=await import(new URL('../dist/runtime/src/dsh-project-import.js',import.meta.url)),target=join(stage,'must-not-import-assets');await assert.rejects(()=>importDshProject(join(assets,'assets.json'),target,{sourceSha256:hash(raw),selection:{provider:'fixture',model:'chosen'}}));await assert.rejects(()=>lstat(target),e=>e.code==='ENOENT');checks++;
 await mkdir(output,{mode:0o700});const receipt={schema:'augmentor-dsh-legacy-assets-proof/1',checks,images:1,files:2,references:4,twentyMiBFileChunkingExact:true,emptyFilePreserved:true,childOnlyOwnershipPreserved:true,verificationWithoutSourceHomePassed:true,changedAssetsAndForeignOwnershipRefused:true,missingAssetRefusesWholeCapture:true,existingOutputPreserved:true,sourceInputsUnchanged:true,currentHarnessImportCompatible:false,nativeImporterRefusesCompanion:true,nativeTargetsCreated:0,modelRequests:0,privateOwnerDataUsed:false};await writeFile(join(output,'proof.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
}finally{await rm(stage,{recursive:true,force:true});}
