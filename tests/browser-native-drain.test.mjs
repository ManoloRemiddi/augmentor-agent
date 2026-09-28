// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {spawn} from 'node:child_process'
import {once} from 'node:events'
import {mkdtemp,mkdir,readFile} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {createServer} from 'node:net'
import {setTimeout as delay} from 'node:timers/promises'
import {RELEASE} from '../dist/contracts/src/release.js'

for(const mode of ['parent','parent-with-child','pi-bridge','dsh-bridge'])test(`browser EOF drains an accepted shared request: ${mode}`,{
  timeout:15000,skip:process.platform==='win32'?'Uses a Unix fixture socket; native Windows transport has separate qualification.':false,
},async t=>{
  const root=await mkdtemp(join(tmpdir(),'augmentor-native-drain-'))
  const state=join(root,'state');await mkdir(state,{mode:0o700})
  const observed=join(root,'natural-exit')
  let release,accepted
  const waiting=new Promise(resolve=>accepted=resolve), gate=new Promise(resolve=>release=resolve)
  const sockets=new Set()
  const server=createServer(socket=>{
    sockets.add(socket);socket.on('close',()=>sockets.delete(socket));socket.on('error',()=>{})
    let buffer=''
    socket.on('data',chunk=>{
      buffer+=chunk
      if(!buffer.includes('\n'))return
      const request=JSON.parse(buffer.split('\n')[0]);buffer=''
      assert.equal(request.method,'prompts.save')
      accepted()
      void gate.then(()=>socket.end(JSON.stringify({id:request.id,result:{prompts:[{name:'preserved',content:'accepted work'}]}})+'\n'))
    })
  })
  server.listen(join(state,'prompts.sock'));await once(server,'listening')
  t.after(()=>{release();for(const socket of sockets)socket.destroy();server.close()})
  const script=mode==='pi-bridge'?'pi-bridge.mjs':mode==='dsh-bridge'?'pipe.mjs':'native-host.mjs'
  const child=spawn(process.execPath,['--import',new URL('./fixtures/browser-natural-exit.mjs',import.meta.url).href,'apps/browser/'+script],{
    env:{...process.env,AUGMENTOR_SHARED_STATE:state,AUGMENTOR_SHARED_DATA:join(root,'data'),AUGMENTOR_SHARED_CONFIG:join(root,'config'),
      AUGMENTOR_BROWSER_HARNESS:'',AUGMENTOR_UNIFIED:'0',DSH_AUGMENTOR_URL:'http://127.0.0.1:1',DSH_AUGMENTOR_WS_TOKEN:'a'.repeat(32),
      AUGMENTOR_PI_STATE:join(root,'pi'),DSH_HOME:join(root,'dsh'),AUGMENTOR_TEST_EXIT_OBSERVER:observed},
    stdio:['pipe','pipe','pipe'],
  })
  const exited=once(child,'close')
  t.after(()=>{if(child.exitCode===null)child.kill()})
  let serial=0,buffer=Buffer.alloc(0),errors=''
  const pending=new Map()
  child.stderr.on('data',chunk=>errors+=chunk)
  child.stdout.on('data',chunk=>{
    buffer=Buffer.concat([buffer,chunk])
    while(buffer.length>=4&&buffer.length>=buffer.readUInt32LE(0)+4){
      const length=buffer.readUInt32LE(0),frame=JSON.parse(buffer.subarray(4,length+4));buffer=buffer.subarray(length+4)
      pending.get(frame.id)?.(frame);pending.delete(frame.id)
    }
  })
  const call=(method,params)=>new Promise(resolve=>{
    const id=String(++serial),body=Buffer.from(JSON.stringify({id,method,params})),header=Buffer.alloc(4)
    header.writeUInt32LE(body.length);pending.set(id,resolve);child.stdin.write(Buffer.concat([header,body]))
  })
  if(mode.startsWith('parent'))assert.equal((await call('augmentor/handshake',{protocol:'augmentor/1',version:RELEASE.version})).result.version,RELEASE.version)
  const saved=call('augmentor/prompts',{action:'save',name:'preserved',content:'accepted work'})
  await waiting
  if(mode==='parent-with-child')assert.equal((await call('harness.select',{harness:'pi'})).result.harness,'pi')
  child.stdin.end()
  await delay(150);assert.equal(child.exitCode,null,'EOF must not terminate an accepted request')
  release()
  assert.equal((await saved).result.library.prompts[0].content,'accepted work')
  assert.deepEqual(await exited,[0,null],errors)
  assert.equal(await readFile(observed,'utf8'),String(child.pid),'beforeExit distinguishes natural drain from process.exit(0)')
  assert.equal(buffer.length,0,'The final response is a complete native frame')
})
