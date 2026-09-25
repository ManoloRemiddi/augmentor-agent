// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {createServer} from 'node:http'
import {WebSocketServer} from 'ws'
import {createRemoteAdapter} from '../apps/browser/shared/dsh-remote.mjs'

test('Browser history and Stop use live idle status even without turn/end',async t=>{
 const server=createServer(),wss=new WebSocketServer({server}),sockets=[],calls=[],notifications=[]
 wss.on('connection',socket=>{sockets.push(socket);socket.on('message',()=>socket.send(JSON.stringify({type:'item',value:{type:'snapshot',cursor:2,records:[],header:{id:'s'}}})))})
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve))
 const adapter=createRemoteAdapter(`http://127.0.0.1:${server.address().port}`,{
  websocketHeaders:async()=>({}),fetch:async(_url,options)=>{
   const body=JSON.parse(options.body);calls.push(body.method)
   const value=body.method==='session/list'?{items:[{sessionId:'s',running:false}]}:body.method==='session/page'?{records:[{event:{seq:1,type:'turn/start'}},{event:{seq:2,type:'step/end'}}],hasMore:false}:{accepted:true}
   return Response.json({type:'server-response',rpcId:body.rpcId,result:{ok:true,value}})
  }
 },frame=>notifications.push(frame))
 t.after(()=>{adapter.close();for(const s of sockets)s.terminate();wss.close();server.close()})
 const history=await adapter.call('session.history',{sessionId:'s'})
 assert.equal(history.running,false);assert.equal(history.events.at(-1).event.type,'step/end')
 assert.equal(notifications.at(-1).params.status,'idle')
 const result=await adapter.call('session.cancel',{sessionId:'s'})
 assert.equal(result.accepted,true);assert.equal(notifications.at(-1).params.status,'idle')
 assert.equal(calls.filter(x=>x==='session/cancel').length,1)
 assert(!calls.includes('session/prompt'))
})
