// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {diagnosticFrame} from '../apps/browser/extension/diagnostics.mjs';
import {log,state} from '../apps/browser/extension/state.mjs';
test('wire diagnostics omit arbitrary personal data in requests, results, ids and errors',()=>{
 const secret='a private sentence without any credential pattern';
 for(const frame of [{id:secret,method:'augmentor/memory',params:{apiKey:secret,content:secret}},{id:'x',result:{text:secret}},{error:{message:secret}},{method:secret}]){
  assert(!JSON.stringify(diagnosticFrame(frame)).includes(secret));
  log('wire',{dir:'ext->bridge',msg:frame,note:secret});
  assert(!JSON.stringify(state.wirelog).includes(secret));
 }
 assert.equal(diagnosticFrame({id:'x',method:'setup.test',params:{apiKey:secret}}).method,'setup.test');
});

test('diagnostic files are opt-in, private, bounded, and exclude arbitrary strings',async()=>{
 const {MetadataLog}=await import('../apps/browser/shared/diagnostics.mjs');
 const {mkdtempSync,readdirSync,readFileSync,statSync,existsSync,rmSync}=await import('node:fs');
 const {tmpdir}=await import('node:os');const {join}=await import('node:path');
 const root=mkdtempSync(join(tmpdir(),'augmentor-diagnostics-')),directory=join(root,'trace');
 try{
  new MetadataLog(directory,false).write({kind:'log',category:'secret'});assert(!existsSync(directory));
  for(let i=0;i<7;i++){
   const log=new MetadataLog(directory,true);
   for(let n=0;n<12000;n++)log.write({kind:'log',category:'DSH app ready: private-user-home',msg:{id:'secret',method:'aPrivateTokenWithoutSpaces',params:{content:'private sentence'}}});
   log.close();
  }
  const files=readdirSync(directory);assert.equal(files.length,5);
  for(const file of files){const path=join(directory,file);assert(statSync(path).size<=1024*1024);assert.equal(statSync(path).mode&0o777,0o600);const data=readFileSync(path,'utf8');for(const secret of ['private-user-home','aPrivateTokenWithoutSpaces','private sentence'])assert(!data.includes(secret))}
 }finally{rmSync(root,{recursive:true,force:true})}
});
