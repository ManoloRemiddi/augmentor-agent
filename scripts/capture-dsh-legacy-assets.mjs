// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {resolve,join,dirname,basename,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {realpath,lstat,mkdtemp,open,rm} from 'node:fs/promises';
import {constants} from 'node:fs';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {assetInventory,verifyAssets} from '../adapters/dsh-legacy-format/assets.mjs';
const repo=fileURLToPath(new URL('../',import.meta.url));
const [sourceArg,viewArg,homeArg,outputArg,...extra]=process.argv.slice(2);
if(!sourceArg||!viewArg||!homeArg||!outputArg||extra.length)throw Error('Usage: node scripts/capture-dsh-legacy-assets.mjs PINNED_PUBLIC_SOURCE VERIFIED_PRIVATE_VIEW EXPLICIT_DSH_HOME NEW_PRIVATE_ASSETS');
if(process.platform!=='linux')throw Error('Historical asset capture currently requires Linux');process.umask(0o077);
const source=await realpath(resolve(sourceArg)),view=await realpath(resolve(viewArg)),home=await realpath(resolve(homeArg)),output=resolve(outputArg),canonical=join(await realpath(dirname(output)),basename(output));
if([source,view,home].some(root=>canonical===root||canonical.startsWith(root+sep)))throw Error('Asset output must stay outside input directories');
try{await lstat(output);throw Error('Asset output exists; never overwrite it');}catch(e){if(e.code!=='ENOENT')throw e;}
const check=()=>{const run=spawnSync(process.execPath,[join(repo,'scripts/verify-dsh-legacy-view.mjs'),source,view],{encoding:'utf8',timeout:180000,maxBuffer:1024*1024});if(run.status!==0)throw Error('Retained-source verification refused the historical view');};
check();const {inventory}=await assetInventory(view),stage=await mkdtemp(join(dirname(output),'.dsh-historical-assets-'));
try{
 const run=spawnSync(process.env.AUGMENTOR_PYTHON??'python3',['-B',join(repo,'scripts/capture-dsh-legacy-assets.py'),home,stage],{input:JSON.stringify(inventory.requests),encoding:'utf8',timeout:180000,maxBuffer:32*1024*1024});if(run.status!==0)throw Error('Source asset capture refused; no companion published');
 const captured=JSON.parse(run.stdout),manifest={schema:'augmentor-dsh-historical-assets/1',inventory,assets:captured.assets,currentHarnessImportCompatible:false,workingFilesCaptured:false,scope:'Exact stored assets referenced by the bound historical view; no source edits, native import or model work'},raw=Buffer.from(JSON.stringify(manifest)+'\n');
 if(raw.length>32*1024*1024||raw.length+inventory.viewExpandedBytes+captured.expandedBytes>256*1024*1024)throw Error('Combined view/asset byte bound exceeded');
 const file=await open(join(stage,'assets.json'),'wx',0o600);try{await file.writeFile(raw);await file.sync();}finally{await file.close();}
 await verifyAssets(view,stage);check();assert.deepEqual((await assetInventory(view)).inventory,inventory,'Source view changed during capture');
 for(const path of [join(stage,'objects'),stage]){const fd=await open(path,constants.O_RDONLY|constants.O_DIRECTORY|constants.O_NOFOLLOW);try{await fd.sync();}finally{await fd.close();}}
 const published=spawnSync(process.env.AUGMENTOR_PYTHON??'python3',['-B','-c','import sys;sys.path.insert(0,sys.argv[1]);from dsh_project_bundle import publish;publish(sys.argv[2],sys.argv[3])',join(repo,'scripts'),stage,output],{encoding:'utf8',timeout:10000});if(published.status!==0)throw Error('Atomic no-replace asset publication refused');
 console.log(JSON.stringify({images:inventory.requests.filter(r=>r.kind==='image').length,files:inventory.requests.filter(r=>r.kind==='file').length,references:inventory.references.length,assetBytes:captured.expandedBytes,originalViewUnchanged:true,currentHarnessImportCompatible:false,nativeTargetsCreated:0,modelRequests:0}));
}finally{await rm(stage,{recursive:true,force:true});}
