// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Windows uses the same kernel-authenticated pipe adapter as Python services.
 * An inherited stdio relay avoids undocumented Node handle access and adds no
 * unauthenticated localhost port. The wire contract stays byte-for-byte intact.
 */
import {connect as unixConnect} from 'node:net';
import {Duplex} from 'node:stream';
import {spawn, type ChildProcessWithoutNullStreams} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {pythonExecutable,componentEnvironment} from './index.js';

export interface LocalConnection extends Duplex {setTimeout(ms:number,callback?:()=>void):this}

class WindowsConnection extends Duplex implements LocalConnection {
  child:ChildProcessWithoutNullStreams;
  private timeoutMs=0;
  private timer?:NodeJS.Timeout;
  private connected=false;
  private control='';
  constructor(endpoint:string){
    super();
    this.child=spawn(pythonExecutable(),['-Xutf8','-B',fileURLToPath(new URL('../../../services/platform_adapters/pipe_relay.py',import.meta.url)),endpoint],
      {stdio:'pipe',windowsHide:true,env:componentEnvironment()});
    this.child.once('error',error=>this.destroy(error));
    this.child.stdin.on('error',error=>this.destroy(error));
    this.child.stdout.on('data',(chunk:Buffer)=>{this.touch();if(!this.push(chunk))this.child.stdout.pause();});
    this.child.stdout.on('end',()=>this.push(null));
    this.child.stderr.on('data',(chunk:Buffer)=>{
      if(this.connected)return;
      this.control+=chunk.toString('utf8');
      if(this.control.length>8192){this.destroy(new Error('Invalid private transport handshake'));return;}
      const newline=this.control.indexOf('\n');if(newline<0)return;
      try{
        const value=JSON.parse(this.control.slice(0,newline));
        if(value.connected===true){this.connected=true;this.touch();this.emit('connect');}
        else {const error=new Error('The private companion could not be connected.') as NodeJS.ErrnoException;
          error.code=['ENOENT','EACCES','EIO'].includes(value.code)?value.code:'EIO';this.destroy(error);}
      }catch{this.destroy(new Error('Invalid private transport handshake'));}
    });
    this.child.once('close',code=>{
      if(!this.destroyed)this.destroy(code===0&&this.connected?undefined:new Error('The private companion disconnected; the request was not replayed.'));
    });
  }
  private touch(){if(this.timer)clearTimeout(this.timer);if(this.timeoutMs)this.timer=setTimeout(()=>this.emit('timeout'),this.timeoutMs);}
  setTimeout(ms:number,callback?:()=>void){this.timeoutMs=ms;if(callback)this.once('timeout',callback);this.touch();return this;}
  _read(){this.child.stdout.resume();}
  _write(chunk:Buffer,encoding:BufferEncoding,callback:(error?:Error|null)=>void){this.touch();this.child.stdin.write(chunk,encoding,callback);}
  _final(callback:(error?:Error|null)=>void){this.child.stdin.end(callback);}
  _destroy(error:Error|null,callback:(error?:Error|null)=>void){
    if(this.timer)clearTimeout(this.timer);
    this.child.stdin.destroy();this.child.stdout.destroy();this.child.stderr.destroy();
    if(this.child.exitCode===null)this.child.kill();
    callback(error);
  }
}

export function localConnect(endpoint:string):LocalConnection {
  return process.platform==='win32'?new WindowsConnection(endpoint):unixConnect(endpoint);
}
