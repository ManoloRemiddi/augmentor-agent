// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {createServer} from 'node:http'
import {WebSocketServer} from 'ws'
import {createRemoteAdapter} from '../apps/browser/shared/dsh-remote.mjs'

test('slash commands use DSH once; text and paths use model prompts',async t=>{
  const calls=[],sockets=[]
  let outcome={commandId:'c',result:{kind:'success',text:'No goal set.'}},fail=false
  const server=createServer(),wss=new WebSocketServer({server})
  wss.on('connection',socket=>{
    sockets.push(socket)
    socket.on('message',()=>socket.send(JSON.stringify({type:'item',value:{type:'snapshot',cursor:0,records:[],header:{id:'s'}}})))
  })
  await new Promise(r=>server.listen(0,'127.0.0.1',r))
  const adapter=createRemoteAdapter(`http://127.0.0.1:${server.address().port}`,{
    websocketHeaders:async()=>({}),fetch:async(route,options)=>{
      const body=JSON.parse(options.body);calls.push(body)
      if(fail)throw new Error('connection lost')
      return Response.json({type:'server-response',rpcId:body.rpcId,result:{ok:true,value:body.method==='commands/execute'?outcome:{accepted:true}}})
    }
  },()=>{})
  t.after(()=>{adapter.close();for(const s of sockets)s.terminate();wss.close();server.close()})
  const send=text=>adapter.call('session.prompt',{sessionId:'s',content:[{type:'text',text}]})
  assert.deepEqual(await send('/goal'),{accepted:true,command:outcome})
  assert.deepEqual(calls.at(-1).payload.args,{agentId:'s',line:'/goal',submittedAttachments:[]})
  for(const text of ['Summarise news','/home/example/file.txt']){
    assert.deepEqual(await send(text),{accepted:true});assert.equal(calls.at(-1).method,'session/prompt')
  }
  for(const value of [null,{result:{kind:'error',text:'No active goal'}}]){
    outcome=value;const before=calls.length
    await assert.rejects(send('/goal pause'));assert.equal(calls.length,before+1);assert.equal(calls.at(-1).method,'commands/execute')
  }
  fail=true;const before=calls.length
  await assert.rejects(send('/goal clear'),/connection lost/);assert.equal(calls.length,before+1)
})
