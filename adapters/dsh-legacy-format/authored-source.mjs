// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Authored v0 source family for actual pinned codec/asset/native operator proofs.
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';import {join} from 'node:path';
import {spawnSync} from 'node:child_process';import sharp from 'sharp';
import {hash} from './source.mjs';
export async function authoredLegacySource(stage){
 const home=join(stage,'dsh'),frozen=join(stage,'frozen'),view=join(stage,'view'),assets=join(stage,'assets'),cwd=join(stage,'project');await mkdir(home);await mkdir(cwd);await mkdir(frozen);await mkdir(join(frozen,'objects'));
 const image=await sharp({create:{width:3,height:2,channels:3,background:'#315add'}}).png().toBuffer(),file=Buffer.alloc(20*1024*1024,87),empty=Buffer.alloc(0);
 const assetRows=[{kind:'file',raw:file},{kind:'file',raw:empty},{kind:'image',raw:image}];
 for(const row of assetRows){row.id='sha256:'+hash(row.raw);const folder=join(home,'attachments','v1',row.kind==='file'?'file-objects':'objects',row.id.slice(7,9));await mkdir(folder,{recursive:true});row.path=join(folder,row.id.slice(7));await writeFile(row.path,row.raw);}
 const part=(row,name)=>({type:row.kind,attachment:{attachmentId:row.id,bytes:row.raw.length,name,...(row.kind==='image'?{mediaType:'image/png',width:3,height:2}:{})}}),rootId='authored-asset-root',childId='authored-asset-child';
 const header=(id,parent)=>({type:'session',version:0,id,createdAt:1700000000000,delegationDepth:parent?1:0,cwd,...(parent?{parentSession:parent,origin:'subagent'}:{})});
 const log=(id,parent,content)=>{const rows=[header(id,parent)],add=(type,data)=>rows.push({type,seq:rows.length-1,time:1700000000000+rows.length,data,...(type==='user/message'?{surfaceOp:'append'}:{})});if(parent)add('subagent/descriptor',{version:2,mode:'one-shot',provider:'authored',label:'Asset child'});add('session/end-seed',{});add('turn/start',{turn:1});add('step/start',{turn:1,step:1});add('user/message',{source:{kind:'user'},content:[{type:'text',text:'Authored stored asset history'},...content]});add('step/end',{turn:1,step:1});add('turn/end',{turn:1,reason:{kind:'completed'}});return rows;};
 const logs=[log(rootId,null,[part(assetRows[0],'complete.bin'),part(assetRows[1],'empty.txt')]),log(childId,rootId,[part(assetRows[2],'child-only.png'),part(assetRows[2],'child-only.png')])],nodes=[];
 for(const rows of logs){const bytes=Buffer.from(rows.map(r=>JSON.stringify(r)).join('\n')+'\n'),compressed=spawnSync('zstd',['-q','-c'],{input:bytes});assert.equal(compressed.status,0);const sha=hash(compressed.stdout);await writeFile(join(frozen,'objects',sha),compressed.stdout);nodes.push({header:rows[0],version:0,relation:rows[0].id===rootId?'root':'subagent',headerSha256:hash(Buffer.from(JSON.stringify(rows[0])+'\n')),sourceSha256:sha,compressedBytes:compressed.stdout.length,chunks:[{sha256:sha,bytes:compressed.stdout.length}]});}
 const snapshot={schema:'augmentor-dsh-source-family/1',workspace:{path:cwd,title:'Authored assets',sessionIds:[rootId]},roots:[rootId],organization:{archivedSessionIds:[],pinnedSessionIds:[]},nodes,sourceWitness:{membershipStable:true,headerIndexSha256:'a'.repeat(64),headerCount:2},attachmentsCaptured:false};await writeFile(join(frozen,'family.json'),JSON.stringify(snapshot));
 return {home,frozen,view,assets,cwd,image,file,empty,assetRows,rootId,childId,nodes};
}
