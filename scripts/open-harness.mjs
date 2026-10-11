// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Open an inspection client of the already running Pi owner. Never start inference.
import net from 'node:net';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {randomUUID} from 'node:crypto';
import {paths} from '../dist/runtime/src/storage.js';
import {MAX_FRAME,PROTOCOL,identifier} from '../dist/protocol/src/index.js';
const args=process.argv.slice(2),print=args.includes('--print-url'),index=args.indexOf('--session');
const sessionId=index>=0?identifier(args[index+1]):undefined;
const expected=new Set(['--print-url','--session',...(sessionId?[sessionId]:[])]);
if(args.some(arg=>!expected.has(arg)))throw Error('Use --session ID and/or --print-url');
const socket=net.createConnection(paths().socket);socket.setEncoding('utf8');
socket.setTimeout(10000,()=>socket.destroy(Error('Pi owner did not respond. Open the tested runtime profile first.')));
const pending=new Map();let buffer='';
socket.on('error',error=>{for(const item of pending.values())item.reject(error);pending.clear();});
socket.on('close',()=>{for(const item of pending.values())item.reject(Error('Pi owner disconnected'));pending.clear();});
socket.on('data',data=>{
 buffer+=data;if(Buffer.byteLength(buffer)>MAX_FRAME){socket.destroy(Error('Local response exceeds its limit'));return;}
 let boundary;
 while((boundary=buffer.indexOf('\n'))>=0){const raw=buffer.slice(0,boundary);buffer=buffer.slice(boundary+1);try{const frame=JSON.parse(raw),item=pending.get(frame.id);if(item){pending.delete(frame.id);frame.error?item.reject(Error(frame.error.message)):item.resolve(frame.result);}}catch(error){socket.destroy(error);return;}}
});
const rpc=(method,params)=>new Promise((resolve,reject)=>{const id=randomUUID();pending.set(id,{resolve,reject});socket.write(JSON.stringify({id,method,params})+'\n');});
try{
 await once(socket,'connect');await rpc('host.hello',{protocol:PROTOCOL});
 const link=await rpc('harness.open',sessionId?{sessionId}:{}),url=new URL(link.url);
 if(url.protocol!=='http:'||url.hostname!=='127.0.0.1'||!url.hash.startsWith('#token='))throw Error('Pi owner returned an invalid local link');
 if(print)console.log(link.url);
 else{
  const executable=process.platform==='darwin'?'open':process.platform==='win32'?'rundll32':'xdg-open';
  const commandArgs=process.platform==='win32'?['url.dll,FileProtocolHandler',link.url]:[link.url];
  const browser=spawn(executable,commandArgs,{stdio:'ignore'});const [code]=await once(browser,'exit');
  if(code!==0)throw Error('The default browser could not open Harness. Use --print-url for its private link.');
 }
}catch(error){console.error('Augmentor Harness: '+error.message);process.exitCode=1;}
finally{socket.destroy();}
