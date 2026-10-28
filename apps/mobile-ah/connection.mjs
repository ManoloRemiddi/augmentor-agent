// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import net from 'node:net';
import {randomUUID} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
/** Resolve and attest the installed AH. No new Host, model or profile is started. */
export async function installedConnection(){
 const script=fileURLToPath(new URL('../../scripts/ah-connection.py',import.meta.url));
 const selected=JSON.parse(execFileSync('python3',['-B',script],{encoding:'utf8',timeout:15000}));
 const socket=net.createConnection(selected.profile.socket);socket.setEncoding('utf8');
 let buffer='';const pending=new Map();
 const fail=()=>{for(const p of pending.values())p.reject(Error('AH disconnected. Reconnect explicitly; no action was repeated.'));pending.clear();};
 socket.on('error',fail);socket.on('close',fail);socket.setTimeout(10000,()=>socket.destroy());
 socket.on('data',chunk=>{buffer+=chunk;if(Buffer.byteLength(buffer)>1048576){socket.destroy();return;}let end;while((end=buffer.indexOf('\n'))>=0){const raw=buffer.slice(0,end);buffer=buffer.slice(end+1);try{const f=JSON.parse(raw),p=pending.get(f.id);if(p){pending.delete(f.id);f.error?p.reject(Error('AH refused connection.')):p.resolve(f.result);}}catch{socket.destroy();}}});
 const rpc=(method,params={})=>new Promise((resolve,reject)=>{const id=randomUUID();pending.set(id,{resolve,reject});socket.write(JSON.stringify({id,method,params})+'\n');});
 try{
  await new Promise((resolve,reject)=>{socket.once('connect',resolve);socket.once('error',reject);});
  await rpc('host.hello',{protocol:'augmentor-pi/1'});const host=await rpc('host.describe');
  if(host.protocol!=='augmentor-pi/1'||host.version!==selected.version||host.stateDir!==selected.profile.state||host.configDir!==selected.profile.config)throw Error('AH profile identity changed.');
  const link=await rpc('harness.open'),url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
  if(url.protocol!=='http:'||url.hostname!=='127.0.0.1'||url.username||url.password||url.pathname!=='/'||url.search||!/^\d+$/.test(url.port)||!/^[a-f0-9]{64}$/.test(token??''))throw Error('AH returned an invalid connection.');
  return {origin:url.origin,token,binding:selected.binding};
 }finally{socket.destroy();}
}
