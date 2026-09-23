// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {connect,Socket} from 'node:net';
import {randomUUID} from 'node:crypto';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {pythonExecutable,componentEnvironment} from '../../platform/src/index.js';
export class PiConnection {
  pending=new Map<string,{resolve:(value:any)=>void;reject:(error:Error)=>void;timer:NodeJS.Timeout}>();
  buffer=Buffer.alloc(0);closed=false;
  constructor(readonly socket:Socket,readonly event:(frame:any)=>void=()=>{},readonly disconnected:(error:Error)=>void=()=>{}){
    socket.on('error',error=>this.fail(error));socket.on('close',()=>this.fail(new Error('Harness disconnected; the previous action was not replayed.')));
    socket.on('data',data=>{this.buffer=Buffer.concat([this.buffer,data]);if(this.buffer.length>1024*1024){socket.destroy();return;}let end;
      while((end=this.buffer.indexOf(10))>=0){let frame:any;try{frame=JSON.parse(this.buffer.subarray(0,end).toString());}catch{socket.destroy();return;}this.buffer=this.buffer.subarray(end+1);
        if(frame.event)this.event(frame.event);else{const row=this.pending.get(frame.id);if(row){this.pending.delete(frame.id);clearTimeout(row.timer);frame.error?row.reject(new Error(frame.error.message)):row.resolve(frame.result);}}
      }});
  }
  fail(error:Error){if(this.closed)return;this.closed=true;this.socket.destroy();for(const row of this.pending.values()){clearTimeout(row.timer);row.reject(error);}this.pending.clear();this.disconnected(error);}
  call(method:string,params:Record<string,unknown>={},id:string=randomUUID()):Promise<any>{
    if(this.closed)return Promise.reject(new Error('Harness connection is closed'));
    return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(new Error('Request timed out; verify the outcome before retrying.'));},method==='tools.execute'?130000:30000);this.pending.set(id,{resolve,reject,timer});this.socket.write(JSON.stringify({id,method,params})+'\n');});
  }
  close(){this.socket.destroy();}
  static async open(event?:(frame:any)=>void,disconnected?:(error:Error)=>void,harness:'pi'='pi'){
    if(harness!=='pi')throw new Error('Only Pi uses this runtime connection.');
    const prefix='AUGMENTOR_PI';
    const env=componentEnvironment();
    const state=env[prefix+'_STATE']??join(env.XDG_STATE_HOME??join(homedir(),'.local/state'),'augmentor-'+harness);const path=env[prefix+'_SOCKET']??join(state,'runtime.sock');
    const dial=()=>new Promise<Socket>((resolve,reject)=>{const s=connect(path);s.once('connect',()=>resolve(s));s.once('error',reject);});
    let socket:Socket;
    try{socket=await dial();}catch(error:any){
      if(!['ENOENT','ECONNREFUSED'].includes(error.code))throw error;
      // Both surfaces share the same startup lock and cold-start allowance.
      // This helper performs health checks only; it never replays an action.
      await new Promise<void>((resolve,reject)=>{
        const child=spawn(pythonExecutable(),[fileURLToPath(new URL('../../../scripts/ensure-runtime.py',import.meta.url)),'--harness',harness],{stdio:'ignore',env:{...env,AUGMENTOR_PI_NODE:env.AUGMENTOR_PI_NODE??process.execPath}});
        child.once('error',reject);child.once('close',code=>code===0?resolve():reject(new Error(harness+' could not finish starting. Reconnect to check its status.')));
      });
      socket=await dial();
    }
    const client=new PiConnection(socket,event,disconnected);await client.call('host.hello',{protocol:'augmentor-'+harness+'/1'});return client;
  }
}
