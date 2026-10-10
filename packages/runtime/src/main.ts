// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import net from 'node:net';
import {chmodSync,existsSync,lstatSync,unlinkSync} from 'node:fs';
import {join} from 'node:path';
import {Host} from './host.js';
import {HarnessServer} from './harness-server.js';
import {atomicJson,readJson,paths} from './storage.js';
import {MAX_FRAME,PROTOCOL,request,type Data} from '../../protocol/src/index.js';
process.umask(0o077);
const clients=new Map<net.Socket,string|null>();
const write=(socket:net.Socket,value:unknown)=>{if(socket.destroyed)return;const raw=JSON.stringify(value)+'\n';if(Buffer.byteLength(raw)>MAX_FRAME||socket.writableLength>4*MAX_FRAME){socket.destroy();return;}socket.write(raw);};
let harness:HarnessServer|undefined;
let openingHarness:Promise<{url:string;origin:string}>|undefined;
let host:Host;
let closing=false;
let readyOwner:()=>void,failedOwner:(error:unknown)=>void;
const initialised=new Promise<void>((resolve,reject)=>{readyOwner=resolve;failedOwner=reject;});
void initialised.catch(()=>{});
const connected=(sid:string)=>[...clients.values()].includes(sid)||harness?.connected(sid)===true;
async function openHarness(){
  if(openingHarness)return openingHarness;
  openingHarness=(async()=>{
    const server=new HarnessServer(host);
    try{
      const link=await server.start(Number(process.env.AUGMENTOR_HARNESS_PORT??0));
      harness=server;atomicJson(join(host.dirs.state,'harness.json'),{...link,pid:process.pid});
      return link;
    }catch(error){await server.close();openingHarness=undefined;throw error;}
  })();
  return openingHarness;
}
const path=paths().socket;
if(existsSync(path)){
  if(!lstatSync(path).isSocket()||lstatSync(path).uid!==process.getuid?.())throw new Error('Runtime socket path is not an owned socket');
  const live=await new Promise<boolean>((resolve,reject)=>{const probe=net.createConnection(path);probe.on('connect',()=>{probe.destroy();resolve(true);});probe.on('error',(error:NodeJS.ErrnoException)=>{if(error.code==='ECONNREFUSED'||error.code==='ENOENT')resolve(false);else reject(error);});});
  if(live){console.error('Augmentor Pi runtime is already running');process.exit(0);}unlinkSync(path);
}
const server=net.createServer(socket=>{
  clients.set(socket,null);let buffer=Buffer.alloc(0);let ready=false;
  socket.on('error',()=>{});
  socket.on('close',()=>{if(host)host.browser.detach(socket);const sid=clients.get(socket);clients.delete(socket);if(host&&sid&&!connected(sid))host.interactions.cancel(sid);});
  socket.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);if(buffer.length>MAX_FRAME){socket.destroy();return;}let newline:number;
    while((newline=buffer.indexOf(10))>=0){const line=buffer.subarray(0,newline).toString('utf8');buffer=buffer.subarray(newline+1);void (async()=>{
      let id:string|undefined;
      try{const req:unknown=JSON.parse(line);request(req);id=req.id;const p=req.params??{};
        await initialised;
        if(req.method==='host.hello'){if(p.protocol!==PROTOCOL)throw new Error('Incompatible Augmentor protocol');ready=true;write(socket,{id,result:{protocol:PROTOCOL}});return;}
        if(!ready)throw new Error('A protocol handshake is required');
        if(closing)throw new Error('Runtime is closing for maintenance.');
        if(req.method==='events.subscribe'){if(p.sessionId!==null&&p.sessionId!==undefined)host.getMeta(p.sessionId);clients.set(socket,p.sessionId??null);write(socket,{id,result:{subscribed:true}});if(p.sessionId)for(const frame of host.interactions.frames(p.sessionId))write(socket,{event:frame});return;}
        if(req.method==='browser.attach'){if(host.getMeta(p.sessionId).surface!=='browser')throw new Error('Browser tools require a browser session');host.browser.attach(p.sessionId,socket,frame=>write(socket,{event:{method:'browser/execute',payload:frame}}));write(socket,{id,result:{attached:true}});return;}
        if(req.method==='browser.respond'){host.browser.respond(socket,p.rpcId,p.result,p.error);write(socket,{id,result:{accepted:true}});return;}
        if(req.method==='host.shutdown'){await host.dispatch('host.prepareShutdown',{},req.id);write(socket,{id,result:{accepted:true}});void shutdown();return;}
        if(req.method==='harness.open'){if(p.sessionId!==undefined)host.getMeta(p.sessionId);const link=await openHarness();write(socket,{id,result:{...link,url:link.url+(p.sessionId?'&session='+encodeURIComponent(p.sessionId):'')}});return;}
        const result=await host.dispatch(req.method,p,req.id);write(socket,{id,result});
      }catch(error){write(socket,{id,error:{message:error instanceof Error?error.message:String(error)}});}
    })();}
  });
});
await new Promise<void>((resolve,reject)=>{server.once('error',reject);server.listen(path,()=>{chmodSync(path,0o600);resolve();});});
// Bind the owned socket before opening session journals. Concurrent fresh
// launches therefore cannot both recover/prune the same profile.
try{
  host=new Host((sid,frame)=>{harness?.publish(sid,frame);for(const [socket,session] of clients)if(session===sid)write(socket,{event:frame});},connected);
  await host.init();readyOwner!();
}catch(error){failedOwner!(error);for(const socket of clients.keys())socket.destroy();server.close();if(existsSync(path))unlinkSync(path);throw error;}
if(process.env.AUGMENTOR_HARNESS==='1')await openHarness();
console.log(JSON.stringify({ready:true,socket:path,protocol:PROTOCOL}));
async function shutdown(){if(closing)return;closing=true;server.close();await harness?.close();await host.close();for(const client of clients.keys())client.destroy();if(existsSync(path))unlinkSync(path);const descriptor=join(host.dirs.state,'harness.json');if(readJson<Data>(descriptor,{}).pid===process.pid)unlinkSync(descriptor);}
process.on('SIGTERM',()=>void shutdown());process.on('SIGINT',()=>void shutdown());
