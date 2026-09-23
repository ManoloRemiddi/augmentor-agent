// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import net from 'node:net';
import {chmodSync,existsSync,lstatSync,unlinkSync} from 'node:fs';
import {Host} from './host.js';
import {MAX_FRAME,PROTOCOL,request,type Data} from '../../protocol/src/index.js';
process.umask(0o077);
const clients=new Map<net.Socket,string|null>();
const write=(socket:net.Socket,value:unknown)=>{if(socket.destroyed)return;const raw=JSON.stringify(value)+'\n';if(Buffer.byteLength(raw)>MAX_FRAME||socket.writableLength>4*MAX_FRAME){socket.destroy();return;}socket.write(raw);};
const host=new Host((sid,frame)=>{for(const [socket,session] of clients)if(session===sid)write(socket,{event:frame});},sid=>[...clients.values()].includes(sid));
const path=host.dirs.socket;
if(existsSync(path)){
  if(!lstatSync(path).isSocket()||lstatSync(path).uid!==process.getuid?.())throw new Error('Runtime socket path is not an owned socket');
  const live=await new Promise<boolean>((resolve,reject)=>{const probe=net.createConnection(path);probe.on('connect',()=>{probe.destroy();resolve(true);});probe.on('error',(error:NodeJS.ErrnoException)=>{if(error.code==='ECONNREFUSED'||error.code==='ENOENT')resolve(false);else reject(error);});});
  if(live){console.error('Augmentor Pi runtime is already running');process.exit(0);}unlinkSync(path);
}
await host.init();
const server=net.createServer(socket=>{
  clients.set(socket,null);let buffer=Buffer.alloc(0);let ready=false;
  socket.on('error',()=>{});
  socket.on('close',()=>{host.browser.detach(socket);const sid=clients.get(socket);clients.delete(socket);if(sid&&![...clients.values()].includes(sid))host.interactions.cancel(sid);});
  socket.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);if(buffer.length>MAX_FRAME){socket.destroy();return;}let newline:number;
    while((newline=buffer.indexOf(10))>=0){const line=buffer.subarray(0,newline).toString('utf8');buffer=buffer.subarray(newline+1);void (async()=>{
      let id:string|undefined;
      try{const req:unknown=JSON.parse(line);request(req);id=req.id;const p=req.params??{};
        if(req.method==='host.hello'){if(p.protocol!==PROTOCOL)throw new Error('Incompatible Augmentor protocol');ready=true;write(socket,{id,result:{protocol:PROTOCOL}});return;}
        if(!ready)throw new Error('A protocol handshake is required');
        if(closing)throw new Error('Runtime is closing for maintenance.');
        if(req.method==='events.subscribe'){if(p.sessionId!==null&&p.sessionId!==undefined)host.getMeta(p.sessionId);clients.set(socket,p.sessionId??null);write(socket,{id,result:{subscribed:true}});if(p.sessionId)for(const frame of host.interactions.frames(p.sessionId))write(socket,{event:frame});return;}
        if(req.method==='browser.attach'){if(host.getMeta(p.sessionId).surface!=='browser')throw new Error('Browser tools require a browser session');host.browser.attach(p.sessionId,socket,frame=>write(socket,{event:{method:'browser/execute',payload:frame}}));write(socket,{id,result:{attached:true}});return;}
        if(req.method==='browser.respond'){host.browser.respond(socket,p.rpcId,p.result,p.error);write(socket,{id,result:{accepted:true}});return;}
        if(req.method==='host.shutdown'){await host.dispatch('host.prepareShutdown',{},req.id);write(socket,{id,result:{accepted:true}});void shutdown();return;}
        const result=await host.dispatch(req.method,p,req.id);write(socket,{id,result});
      }catch(error){write(socket,{id,error:{message:error instanceof Error?error.message:String(error)}});}
    })();}
  });
});
await new Promise<void>((resolve,reject)=>{server.once('error',reject);server.listen(path,()=>{chmodSync(path,0o600);resolve();});});
console.log(JSON.stringify({ready:true,socket:path,protocol:PROTOCOL}));
let closing=false;
async function shutdown(){if(closing)return;closing=true;server.close();await host.close();for(const client of clients.keys())client.destroy();if(existsSync(path))unlinkSync(path);}
process.on('SIGTERM',()=>void shutdown());process.on('SIGINT',()=>void shutdown());
