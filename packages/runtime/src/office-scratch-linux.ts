// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {tmpdir} from 'node:os';
import {dirname,basename} from 'node:path';
import {fileURLToPath} from 'node:url';
import {lstat,rm} from 'node:fs/promises';
import type {OfficeScratch} from '../vendor/dsh-office/index.js';
import {OfficeToPdfError} from '../vendor/dsh-office/errors.js';

/** A separate cleanup owner is ready before the MIT provider copies bytes. */
export async function createLinuxOfficeScratch():Promise<OfficeScratch>{
  if(process.platform!=='linux')throw new OfficeToPdfError('unavailable','Native Office scratch ownership requires Linux.');
  const parent=tmpdir(),helper=fileURLToPath(new URL('./office-scratch-linux.py',import.meta.url));
  const child=spawn('/usr/bin/python3',['-I','-B',helper,String(process.pid),parent],{detached:true,env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',LC_ALL:'C.UTF-8'},stdio:['pipe','pipe','ignore']});
  const lifetime=new AbortController();let data='',directory:string|undefined,identity:{dev:bigint;ino:bigint}|undefined,disposing=false,failure:unknown,release:Promise<void>|undefined,killTimer:NodeJS.Timeout|undefined;
  let admit!:(value:unknown)=>void,reject!:(cause:unknown)=>void;
  const ready=new Promise<any>((resolve,fail)=>{admit=resolve;reject=fail;});
  const unavailable=()=>new OfficeToPdfError('unavailable','Native Office scratch owner failed.',{cause:failure});
  child.stdin.on('error',()=>{});child.stdout.setEncoding('utf8');
  const fail=(cause:unknown)=>{failure=cause;reject(unavailable());lifetime.abort(unavailable());if(child.exitCode===null&&child.signalCode===null){child.kill('SIGTERM');killTimer??=setTimeout(()=>child.kill('SIGKILL'),2000);killTimer.unref();}};
  child.on('error',fail);
  child.stdout.on('data',bytes=>{
    data+=bytes;if(Buffer.byteLength(data)>8192){fail(new Error('Oversized scratch receipt.'));return;}
    const end=data.indexOf('\n');if(end>=0){try{admit(JSON.parse(data.slice(0,end)));}catch(cause){fail(cause);}}
  });
  const closed=new Promise<number|null>(resolve=>child.once('close',code=>{if(killTimer)clearTimeout(killTimer);if(!disposing)fail(new Error('Scratch owner exited.'));reject(unavailable());resolve(code);}));
  const startup=setTimeout(()=>fail(new Error('Scratch owner readiness timed out.')),10000);startup.unref();
  try{
    const receipt=await ready;
    if(typeof receipt.directory!=='string'||dirname(receipt.directory)!==parent||!/^dsh-office-to-pdf-[a-f0-9]{24}$/.test(basename(receipt.directory))||typeof receipt.dev!=='string'||typeof receipt.ino!=='string')throw new Error('Invalid scratch receipt.');
    directory=receipt.directory;identity={dev:BigInt(receipt.dev),ino:BigInt(receipt.ino)};
    const current=await lstat(directory!,{bigint:true});
    if(!current.isDirectory()||current.dev!==identity.dev||current.ino!==identity.ino||Number(current.mode&0o777n)!==0o700||current.uid!==BigInt(process.getuid!()))throw new Error('Unconfirmed scratch identity.');
    lifetime.signal.throwIfAborted();
  }catch(cause){disposing=true;child.stdin.end();await closed;throw cause;}finally{clearTimeout(startup);}
  return {directory:directory!,signal:lifetime.signal,dispose(){return release??=(async()=>{
    disposing=true;child.stdin.end('R\n');
    if(child.exitCode===null&&child.signalCode===null){killTimer??=setTimeout(()=>child.kill('SIGKILL'),2000);killTimer.unref();}
    const code=await closed;
    // The live provider retains its exact-root fallback after guard loss.
    try{const current=await lstat(directory!,{bigint:true});if(!current.isDirectory()||current.dev!==identity!.dev||current.ino!==identity!.ino||Number(current.mode&0o777n)!==0o700||current.uid!==BigInt(process.getuid!()))throw new OfficeToPdfError('failed','Office scratch identity changed.');await rm(directory!,{recursive:true,force:true});}catch(cause){if((cause as NodeJS.ErrnoException).code!=='ENOENT')throw cause;}
    let confirmed=false;try{const lines=data.trim().split('\n');confirmed=lines.length===2&&JSON.parse(lines[1]).released===true;}catch{}
    if(code!==0||!confirmed||failure)throw unavailable();
  })();}};
}
