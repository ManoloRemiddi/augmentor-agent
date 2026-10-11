// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Diagnostic real-kernel I/O calibration, not a representative performance claim.
import assert from 'node:assert/strict';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {rm} from 'node:fs/promises';
import {performance} from 'node:perf_hooks';
import {privateDir,atomicJson,readJson} from '../../dist/runtime/src/storage.js';
if(process.platform!=='win32')throw Error('Actual Windows record calibration required.');
const root=privateDir(join(tmpdir(),'augmentor-record-calibration-'+crypto.randomUUID())),file=join(root,'record.json');
try{
 const start=performance.now();let heartbeat;
 const yielded=new Promise(resolve=>setImmediate(()=>{heartbeat=performance.now()-start;resolve();}));
 const writes=[],reads=[];
 for(let index=0;index<20;index++){
  const value={version:1,index,text:'Independent synthetic record café'};
  let at=performance.now();atomicJson(file,value);writes.push(performance.now()-at);
  at=performance.now();assert.deepEqual(readJson(file,null),value);reads.push(performance.now()-at);
 }
 await yielded;
 const stats=values=>({calls:values.length,totalMs:values.reduce((sum,value)=>sum+value,0),minMs:Math.min(...values),maxMs:Math.max(...values)});
 console.log(JSON.stringify({kind:'windows-private-record-calibration',writes:stats(writes),reads:stats(reads),eventLoopYieldMs:heartbeat}));
}finally{await rm(root,{recursive:true,force:true,maxRetries:5,retryDelay:100});}
