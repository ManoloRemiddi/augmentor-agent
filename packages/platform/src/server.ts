// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import net from 'node:net';
import {EventEmitter} from 'node:events';
import {Duplex} from 'node:stream';
import {spawn,type ChildProcessWithoutNullStreams} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {pythonExecutable,componentEnvironment} from './index.js';
import type {LocalConnection} from './transport.js';
const VERSION='augmentor-pipe-server/1';
const helper=fileURLToPath(new URL('../../../services/platform_adapters/pipe_server_relay.py',import.meta.url));
class RelayConnection extends Duplex implements LocalConnection {
 private timer?:ReturnType<typeof setTimeout>;private timeoutMs=0;
 constructor(readonly id:number,private owner:WindowsServer){super();}
 private touch(){if(this.timer)clearTimeout(this.timer);if(this.timeoutMs)this.timer=setTimeout(()=>this.emit('timeout'),this.timeoutMs);}
 setTimeout(ms:number,callback?:()=>void){this.timeoutMs=ms;if(callback)this.once('timeout',callback);this.touch();return this;}
 feed(bytes:Buffer){if(this.destroyed)return;this.touch();if(this.readableLength+bytes.length>4*1024*1024)this.destroy();else this.push(bytes);}
 _read(){}
 _write(bytes:Buffer,_encoding:BufferEncoding,done:(error?:Error|null)=>void){
  this.touch();try{for(let at=0;at<bytes.length;at+=65536)this.owner.send({type:'data',id:this.id,data:bytes.subarray(at,at+65536).toString('base64')},at+65536>=bytes.length?done:undefined);if(!bytes.length)done();}catch(error){done(error as Error);}
 }
 _final(done:()=>void){this.destroy();done();}
 _destroy(error:Error|null,done:(error?:Error|null)=>void){if(this.timer)clearTimeout(this.timer);try{this.owner.send({type:'close',id:this.id});}catch{}this.owner.forget(this.id);done(error);}
}
class WindowsServer extends EventEmitter {
 private child?:ChildProcessWithoutNullStreams;private sockets=new Map<number,RelayConnection>();private buffer='';private closing=false;private ready=false;
 constructor(private connected:(socket:LocalConnection)=>void){super();}
 forget(id:number){this.sockets.delete(id);}
 send(value:object,done?:(error?:Error|null)=>void){
  if(this.closing||!this.child||this.child.stdin.destroyed)throw Error('The owned private listener is closed.');
  if(this.child.stdin.writableLength>4*1024*1024)throw Error('The owned private listener output exceeded its bound.');
  this.child.stdin.write(JSON.stringify({version:VERSION,...value})+'\n',done);
 }
 listen(endpoint:string,done:()=>void){
  if(this.child||this.closing)throw Error('The private listener cannot be started twice.');
  const child=this.child=spawn(pythonExecutable(),['-I','-Xutf8','-B',helper,endpoint],{env:componentEnvironment(),windowsHide:true,stdio:'pipe'});
  const failed=()=>{if(this.closing)return;this.emit('error',new Error('The authenticated Windows listener was refused or disconnected.'));this.close();};
  child.on('error',failed);child.stdin.on('error',failed);child.stderr.on('data',()=>{});
  child.stdout.on('data',(bytes:Buffer)=>{
   if(this.closing)return;
   try{
    if(bytes.some(byte=>byte>127))throw Error('Invalid relay bytes.');this.buffer+=bytes.toString('ascii');let end:number;
    while((end=this.buffer.indexOf('\n'))>=0){
     if(end>128*1024)throw Error('Oversized relay frame.');const event=JSON.parse(this.buffer.slice(0,end));this.buffer=this.buffer.slice(end+1);
     if(!event||event.version!==VERSION)throw Error('Invalid relay version.');
     if(event.type==='ready'){if(this.ready)throw Error('Repeated relay readiness.');this.ready=true;done();continue;}
     if(!this.ready||!Number.isSafeInteger(event.id)||event.id<=0)throw Error('Invalid relay identity.');
     if(event.type==='connect'){
      if(this.sockets.has(event.id)||this.sockets.size>=32)throw Error('Invalid relay admission.');const socket=new RelayConnection(event.id,this);this.sockets.set(event.id,socket);this.connected(socket);
     }else if(event.type==='close'){this.sockets.get(event.id)?.destroy();}
     else if(event.type==='data'){
      if(typeof event.data!=='string'||event.data.length>87384)throw Error('Invalid relay data.');const data=Buffer.from(event.data,'base64');if(data.length>65536||data.toString('base64')!==event.data)throw Error('Invalid relay encoding.');this.sockets.get(event.id)?.feed(data);
     }else throw Error('Invalid relay operation.');
    }
    if(this.buffer.length>128*1024)throw Error('Oversized partial relay frame.');
   }catch{failed();}
  });
  child.once('close',()=>{if(!this.closing)failed();});
 }
 close(){
  if(this.closing)return;this.closing=true;for(const socket of this.sockets.values())socket.destroy();this.sockets.clear();
  if(this.child){const child=this.child;child.stdin.end(JSON.stringify({version:VERSION,type:'shutdown'})+'\n');const timer=setTimeout(()=>child.kill(),4000);timer.unref();child.once('close',()=>clearTimeout(timer));}
 }
}
/** Windows retains kernel peer/DACL checks; Unix retains the existing socket. */
export function localServer(connected:(socket:LocalConnection)=>void){return process.platform==='win32'?new WindowsServer(connected):net.createServer(connected);}
