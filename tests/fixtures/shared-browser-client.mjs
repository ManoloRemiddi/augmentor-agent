// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real native messaging pipe + isolated DSH fixture. No browser UI or live model.
import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import assert from 'node:assert/strict'
import {setTimeout as delay} from 'node:timers/promises'
const child=spawn(process.execPath,[fileURLToPath(new URL('../../apps/browser/pipe.mjs',import.meta.url))],{stdio:['pipe','pipe','inherit'],env:{...process.env,AUGMENTOR_UNIFIED:'1'}})
let serial=0,buffer=Buffer.alloc(0);const pending=new Map(),events=[]
const send=(method,params={})=>new Promise((resolve,reject)=>{
 const id=++serial,data=Buffer.from(JSON.stringify({id,method,params})),prefix=Buffer.alloc(4);prefix.writeUInt32LE(data.length)
 const timer=setTimeout(()=>{pending.delete(id);reject(Error('Fixture request timed out: '+method))},15000)
 pending.set(id,{resolve,reject,timer});child.stdin.write(Buffer.concat([prefix,data]))
})
child.stdout.on('data',data=>{
 buffer=Buffer.concat([buffer,data]);while(buffer.length>=4){const n=buffer.readUInt32LE();if(buffer.length<n+4)break
  const frame=JSON.parse(buffer.subarray(4,4+n));buffer=buffer.subarray(4+n)
  if(!frame.method&&pending.has(frame.id)){const p=pending.get(frame.id);pending.delete(frame.id);clearTimeout(p.timer);frame.error?p.reject(Error(frame.error.message)):p.resolve(frame.result)}else events.push(frame)
 }
})
async function until(fn){for(let i=0;i<150;i++){const value=fn();if(value)return value;await delay(100)}throw Error('Fixture notification timed out')}
try{
 const rows=(await send('session.list')).items
 assert(rows.some(row=>row.sessionId==='setup-linux'));assert(rows.some(row=>row.sessionId==='setup-browser'))
 for(const [sessionId,outcome] of [['setup-browser','rejected'],['setup-linux','allowed-once']]){
  const before=events.length
  await send('session.prompt',{sessionId,mode:'queue',content:[{type:'text',text:'native approval fixture via shared browser bridge'}]})
  const request=await until(()=>events.slice(before).find(e=>e.method==='approval.requested'&&e.params.sessionId===sessionId))
  await send('augmentor/interaction',{sessionId,id:request.id,value:{outcome}})
  await until(()=>events.slice(before).find(e=>e.method==='session.event'&&e.params.sessionId===sessionId&&e.params.event.type==='turn/end'))
  await assert.rejects(send('augmentor/interaction',{sessionId,id:request.id,value:{outcome}}))
 }
 console.log('Native browser pipe shares both personal conversations and handles explicit approval/rejection without replay.')
}finally{
 for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Fixture closing'))}pending.clear()
 child.stdin.end();const timer=setTimeout(()=>child.kill(),2000);timer.unref();child.once('exit',()=>clearTimeout(timer))
}
