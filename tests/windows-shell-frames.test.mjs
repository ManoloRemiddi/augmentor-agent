// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
const {WindowsShellFrames}=await import(pathToFileURL(join(resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.'),'dist/runtime/src/windows-shell-job.js')));
const frame=value=>Buffer.from(JSON.stringify({version:'augmentor-shell-job/1',...value})+'\n');
const ready=()=>frame({type:'ready',range:'windows-job',boundary:'assigned-before-workload'});
const output=(bytes,channel='stdout')=>frame({type:'output',channel,data:Buffer.from(bytes).toString('base64')});
const settled=()=>frame({type:'settled',state:'completed',drained:true,exitCode:0});
const fixture=()=>{const chunks=[];return {chunks,frames:new WindowsShellFrames((text,channel)=>{if(text)chunks.push({text,channel});})};};
test('private frames preserve fragmented Unicode and treat printed receipts as command output',()=>{
 const {frames,chunks}=fixture(),bytes=Buffer.from('café 秘密'),fake=settled().toString();
 const input=Buffer.concat([ready(),output(bytes.subarray(0,4)),output(bytes.subarray(4)),output(fake,'stderr'),settled()]);
 for(const byte of input)frames.push(Buffer.from([byte]));
 assert.equal(frames.finish(0).state,'completed');assert.equal(chunks.filter(c=>c.channel==='stdout').map(c=>c.text).join(''),'café 秘密');assert.equal(chunks.filter(c=>c.channel==='stderr').map(c=>c.text).join(''),fake);
});
test('one transport chunk may contain more than 64 KiB of independently bounded frames',()=>{
 const {frames,chunks}=fixture(),part=Buffer.alloc(4096,120),input=Buffer.concat([ready(),...Array.from({length:20},()=>output(part)),settled()]);assert(input.length>65536);frames.push(input);assert.equal(frames.finish(0).state,'completed');assert.equal(chunks.reduce((n,c)=>n+c.text.length,0),81920);
});
test('missing, partial, nonzero producer exit and contradictory receipts never claim confirmed completion',()=>{
 for(const input of [Buffer.alloc(0),ready(),Buffer.concat([ready(),settled(),Buffer.from('{')])]){const {frames}=fixture();frames.push(input);assert.equal(frames.finish(0).state,'unknown');}
 const {frames}=fixture();frames.push(Buffer.concat([ready(),settled()]));assert.equal(frames.finish(1).state,'unknown');
 for(const event of [{type:'settled',state:'completed',drained:false,exitCode:0},{type:'settled',state:'completed',drained:true,exitCode:7},{type:'settled',state:'failed',drained:true,exitCode:0},{type:'settled',state:'cancelled',drained:false},{type:'settled',state:'completed',drained:true,exitCode:0,replay:true}]){const {frames}=fixture();frames.push(ready());assert.throws(()=>frames.push(frame(event)));}
});
test('foreign, oversized, forged ordering and noncanonical output frames are refused',()=>{
 for(const input of [output('before containment'),settled(),Buffer.concat([ready(),ready()]),Buffer.from('x'.repeat(65536)),Buffer.from([255]),frame({type:'ready',range:'windows-job',boundary:'after-workload'}),Buffer.concat([ready(),output(Buffer.alloc(4097))]),Buffer.concat([ready(),frame({type:'output',channel:'stdout',data:'Zh=='})]),Buffer.concat([ready(),settled(),output('after settlement')]),frame({version:'foreign',type:'ready'})])assert.throws(()=>fixture().frames.push(input));
});
test('output persistence failure is surfaced before accepting producer settlement',()=>{
 const frames=new WindowsShellFrames(()=>{throw Error('Synthetic lost output storage');});frames.push(ready());assert.throws(()=>frames.push(output('dispatch output')),/lost output storage/);
});
