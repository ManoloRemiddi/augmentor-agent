// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independent scripted transport peer. No private companion, recognizer or audio assets.
import {createServer} from 'node:http';
import {randomBytes,randomUUID} from 'node:crypto';
import {WebSocketServer,WebSocket} from 'ws';
export function dictationPeer(options={}){
  const token=randomBytes(32).toString('hex'),tickets=new Map(),bridges=new Map(),connections=[],requests=[];
  let port;
  const send=(peer,value)=>{if(peer.socket.readyState===WebSocket.OPEN)peer.socket.send(JSON.stringify(value));};
  const finish=async peer=>{await options.finalGate?.();send(peer,options.empty?{type:'empty-transcript'}:{type:'transcript',requestId:peer.requestId,text:options.text??'A synthetic editable draft.'});};
  const server=createServer(async(req,res)=>{
    const reply=(status,value)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(value));};
    if(req.url==='/health'){reply(200,{protocol:'resonant-voice/1',capabilities:{scopedHarnessBridge:1,scopedHarnesses:['pi'],...(options.legacy?{}:{dictation:1})}});return;}
    if(req.headers['x-resonant-token']!==token){reply(403,{});return;}
    let body;try{let raw='';for await(const chunk of req)raw+=chunk;body=JSON.parse(raw);}catch{reply(400,{});return;}
    requests.push({path:req.url,body});
    if(req.url==='/internal/dictation/catalog'){await options.catalogGate?.();reply(200,{protocol:'resonant-voice/1',recognition:{available:options.available!==false},language:'en',device:'cpu',maxUtteranceSeconds:600});return;}
    if(req.url==='/internal/ticket'){
      if(body.purpose!=='dictation'||body.harness!=='pi'){reply(400,{});return;}
      await options.ticketGate?.();const ticket=randomBytes(32).toString('hex'),bridgeId=randomBytes(32).toString('hex'),bridge={...body,bridgeId};tickets.set(ticket,bridge);bridges.set(bridgeId,bridge);
      reply(200,{protocol:'resonant-voice/1',sessionId:body.sessionId,ticket,bridgeId,bridgeLeaseMs:8000,url:'ws://127.0.0.1:'+port+'/voice'});return;
    }
    const bridge=bridges.get(body.bridgeId);
    if(req.url!=='/internal/event'||!bridge||body.sessionId!==bridge.sessionId){reply(403,{});return;}
    if(body.type==='disconnect'){bridge.peer?.socket.close();bridges.delete(body.bridgeId);reply(200,{ok:true,active:false});return;}
    reply(200,{ok:true,active:!!bridge.peer,pending:!bridge.peer});
  });
  const sockets=new WebSocketServer({server,path:'/voice',maxPayload:65536});
  sockets.on('connection',socket=>{
    let peer;socket.on('error',()=>{});
    socket.on('message',async(data,binary)=>{
      if(binary){if(!peer)return;peer.chunks++;peer.bytes+=data.length;await options.ackGate?.(peer);send(peer,{type:'audio-accepted',requestId:peer.requestId,bytes:options.badAck?peer.bytes+2:peer.bytes});if(peer.bytes===19200000)await finish(peer);return;}
      const event=JSON.parse(data);
      if(!peer){const bridge=tickets.get(event.ticket);if(!bridge){socket.close();return;}tickets.delete(event.ticket);peer={socket,bridge,bytes:0,chunks:0};bridge.peer=peer;connections.push(peer);await options.readyGate?.();send(peer,{type:'ready',protocol:'resonant-voice/1',mode:'dictation',inputAcknowledgements:true,maxUtteranceSeconds:600,input:{sampleRate:16000,channels:1,format:'s16le'}});return;}
      if(event.type==='begin'){peer.requestId=randomUUID();send(peer,{type:'listening',requestId:peer.requestId});}
      else if(event.type==='end'){peer.ends=(peer.ends??0)+1;await finish(peer);}
    });
  });
  return {server,connections,requests,bridges,options,get connection(){return {base:'http://127.0.0.1:'+port,token};},async listen(){await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));port=server.address().port;},async close(){for(const client of sockets.clients)client.terminate();await new Promise(resolve=>sockets.close(resolve));server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}};
}
export function syntheticWave(pcmBytes=3200){
  const bytes=Buffer.alloc(44+pcmBytes);bytes.write('RIFF');bytes.writeUInt32LE(bytes.length-8,4);bytes.write('WAVEfmt ',8);bytes.writeUInt32LE(16,16);bytes.writeUInt16LE(1,20);bytes.writeUInt16LE(1,22);bytes.writeUInt32LE(16000,24);bytes.writeUInt32LE(32000,28);bytes.writeUInt16LE(2,32);bytes.writeUInt16LE(16,34);bytes.write('data',36);bytes.writeUInt32LE(pcmBytes,40);return bytes;
}
