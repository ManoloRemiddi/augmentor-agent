// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';import {spawn} from 'node:child_process';import {once} from 'node:events';import {readFileSync,writeFileSync,existsSync} from 'node:fs';import {join} from 'node:path';import {fileURLToPath} from 'node:url';
import {PiConnection} from '../dist/client/src/socket.js';import {localConnect} from '../dist/platform/src/transport.js';
const source=fileURLToPath(new URL('../',import.meta.url));
async function until(fn){const end=Date.now()+15000;while(Date.now()<end){if(await fn())return;await new Promise(r=>setTimeout(r,25));}throw Error('Authored runtime condition timed out');}
test('actual SDK keeps Ungrouped histories, drafts, work files and provider context separate',{timeout:60000},async t=>{
 let output='',errors='',link,owner;
 const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(k)));for(const k of ['AUGMENTOR_PI_TEST_ROOT','AUGMENTOR_PYTHON'])if(process.env[k])env[k]=process.env[k];
 const child=spawn(process.execPath,[join(source,'scripts/harness-ui-proof.mjs')],{cwd:source,env:{...env,AUGMENTOR_HARNESS_PROOF_RECORD_REQUESTS:'1'},stdio:['ignore','pipe','pipe']});child.stdout.on('data',b=>output+=b);child.stderr.on('data',b=>errors+=b);
 t.after(async()=>{owner?.close();if(child.exitCode===null){const end=once(child,'exit');child.kill();await end;}});
 await until(()=>{assert.equal(child.exitCode,null,errors);try{link=JSON.parse(output.split('\n').find(x=>x.startsWith('{"fixture"')));return !!link;}catch{return false;}});
 const socket=localConnect(join(link.state,'runtime.sock'));await once(socket,'connect');owner=new PiConnection(socket);await owner.call('host.hello',{protocol:'augmentor-pi/1'});
 const selection=(await owner.call('models.list')).default;
 for(const sessionId of ['quick-a','quick-b'])await owner.call('session.create',{sessionId,selection,ungrouped:true});
 const rows=(await owner.call('session.list')).items,a=rows.find(x=>x.sessionId==='quick-a'),b=rows.find(x=>x.sessionId==='quick-b');assert.notEqual(a.cwd,b.cwd);assert(a.ungrouped&&b.ungrouped);
 writeFileSync(join(a.cwd,'a-private.txt'),'ALPHA_FILE_ONLY');assert(!existsSync(join(b.cwd,'a-private.txt')));
 const before=(await owner.call('workspace.list')).items;assert(!before.some(x=>x.cwd===a.cwd||x.cwd===b.cwd));
 await owner.call('draft.text',{sessionId:a.sessionId,expectedTextRevision:0,text:'ALPHA_DRAFT_ONLY'});assert.equal((await owner.call('draft.describe',{sessionId:b.sessionId})).text,'');
 for(const [row,prompt] of [[a,'ALPHA_HISTORY_ONLY'],[b,'BETA_FRESH_CHAT']]){
  await owner.call('session.prompt',{sessionId:row.sessionId,requestId:'request-'+row.sessionId,mode:'queue',resumeQueue:true,content:[{type:'text',text:prompt}]});await until(async()=>{const h=await owner.call('session.history',{sessionId:row.sessionId});return h.events.some(x=>x.event.type==='turn/end');});
 }
 const hb=await owner.call('session.history',{sessionId:b.sessionId});assert(!JSON.stringify(hb).includes('ALPHA_HISTORY_ONLY'));assert.equal(hb.events.filter(x=>x.event.type==='user/message').length,1);
 const requests=readFileSync(link.requestLog,'utf8').trim().split('\n').map(JSON.parse),beta=requests.filter(x=>JSON.stringify(x.messages).includes('BETA_FRESH_CHAT'));assert(beta.length>0);for(const wire of beta){assert(!JSON.stringify(wire).includes('ALPHA_HISTORY_ONLY'));assert(!JSON.stringify(wire).includes('ALPHA_DRAFT_ONLY'));}
 await owner.call('draft.text',{sessionId:a.sessionId,expectedTextRevision:1,text:''});
 // Explicit project creation remains a project; no old workspace is removed.
 await owner.call('session.create',{sessionId:'project-explicit',selection,cwd:link.workspace});assert((await owner.call('workspace.list')).items.some(x=>x.cwd===link.workspace));
 assert.equal((await owner.call('session.list')).items.find(x=>x.sessionId===a.sessionId).cwd,a.cwd);
});
