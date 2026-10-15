// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {homedir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {readFile,lstat,rm,mkdtemp} from 'node:fs/promises';
import type {ConverterOptions} from '@deepseek-ai/libreoffice-kit';
import type {OfficeConverter} from '../vendor/dsh-office/index.js';
import {OfficeToPdfError} from '../vendor/dsh-office/errors.js';
import {createLinuxOfficeScratch} from './office-scratch-linux.js';

const helper=fileURLToPath(new URL('./office-native-linux.py',import.meta.url));
const defaults=fileURLToPath(new URL('../vendor/office-font-fallbacks/groups.json',import.meta.url));
const limits={timeoutMs:60_000,maxInputBytes:20*1024*1024,maxOutputBytes:20*1024*1024,maxImageResolution:192,maxArchiveEntries:10_000,maxUncompressedBytes:250*1024*1024,maxFontFiles:20_000,maxFontFileBytes:256*1024*1024,maxLoadedFontBytes:512*1024*1024};
const codes=new Set(['input-too-large','output-too-large','invalid-document','unsupported-format','invalid-output','timeout','unavailable','failed']);

/** Opt-in Linux adapter. Each operation owns a helper/process group and private
 * sandbox; disposal/cancellation waits for actual exit before slot reuse. */
export async function createLinuxNativeOfficeConverter(options:ConverterOptions={}):Promise<OfficeConverter>{
  if(process.platform!=='linux'||process.arch!=='x64')throw new OfficeToPdfError('unavailable','Native Office sandbox is not qualified for this OS/architecture.');
  for(const name of Object.keys(options))if(!(name in limits)&&!['fontDirectories','fontFallbacks','fontMetadataCacheDirectory'].includes(name))throw new TypeError('Unknown native Office option: '+name);
  if(options.fontMetadataCacheDirectory!==undefined&&options.fontMetadataCacheDirectory!==false)throw new TypeError('Native Office previews require transient font metadata.');
  for(const [name,defaultValue] of Object.entries(limits)){
    const value=options[name as keyof typeof limits]??defaultValue;
    if(!Number.isSafeInteger(value)||value<1||value>0x7fffffff)throw new RangeError('Invalid native Office limit: '+name);
  }
  const fontDirectories=options.fontDirectories??[...new Set([...(process.env.XDG_DATA_DIRS??'/usr/local/share:/usr/share').split(':').filter(Boolean).map(root=>join(root,'fonts')),join(homedir(),'.fonts'),join(process.env.XDG_DATA_HOME??join(homedir(),'.local/share'),'fonts')])];
  const fontFallbacks=options.fontFallbacks??JSON.parse(await readFile(defaults,'utf8'));
  if(!Array.isArray(fontDirectories)||fontDirectories.some(root=>typeof root!=='string'||!root.startsWith('/')||root.includes('\0')))throw new TypeError('Native Office font roots must be absolute.');
  if(!Array.isArray(fontFallbacks)||fontFallbacks.some(group=>!Array.isArray(group)||group.length<2||group.some(name=>typeof name!=='string'||!name.trim()||name.includes('\0'))))throw new TypeError('Native Office font fallback groups are invalid.');
  const resolved={...limits,...Object.fromEntries(Object.keys(limits).map(name=>[name,options[name as keyof typeof limits]??limits[name as keyof typeof limits]])),fontDirectories:[...fontDirectories],fontFallbacks:fontFallbacks.map(group=>[...group])};
  const lifetime=new AbortController();let tail:Promise<unknown>=Promise.resolve();
  const perform=async(request:{inputPath:string;outputPath:string},signal?:AbortSignal)=>{
    const deadline=AbortSignal.timeout(resolved.timeoutMs),upstream=AbortSignal.any([lifetime.signal,deadline,...(signal?[signal]:[])]);upstream.throwIfAborted();
    if(typeof request.outputPath!=='string'||!request.outputPath.startsWith('/')||request.outputPath.includes('\0'))throw new OfficeToPdfError('invalid-output','Invalid native Office output.');
    try{await lstat(request.outputPath);throw new OfficeToPdfError('invalid-output','Native Office output already exists.');}catch(cause){if((cause as NodeJS.ErrnoException).code!=='ENOENT')throw cause;}
    let succeeded=false;
    const scratch=await mkdtemp(join(dirname(request.outputPath),'augmentor-native-office-'));
    const identity=await lstat(scratch,{bigint:true});
    try{upstream.throwIfAborted();const result=await new Promise<{missingFonts:string[]}>((resolve,reject)=>{
      // Node owns the cleanup helper directly. Its separate-session broker has
      // a kernel death kill; namespace monitors own the native descendants.
      const child=spawn('/usr/bin/python3',['-I','-B',helper,String(process.pid),scratch,String(identity.dev),String(identity.ino)],{detached:true,env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',LC_ALL:'C.UTF-8',TZ:'UTC'},stdio:['pipe','pipe','ignore']});
      let data='',overflow=false,error:unknown,killTimer:NodeJS.Timeout|undefined;
      const kill=(kind:NodeJS.Signals)=>{if(child.pid&&child.exitCode===null){try{process.kill(-child.pid,kind);}catch(cause){if((cause as NodeJS.ErrnoException).code!=='ESRCH')error=cause;}}};
      const abort=()=>{kill('SIGTERM');killTimer=setTimeout(()=>kill('SIGKILL'),2000);killTimer.unref();};
      upstream.addEventListener('abort',abort,{once:true});if(upstream.aborted)abort();
      child.on('error',cause=>{error=cause;});child.stdin.on('error',()=>{});child.stdout.setEncoding('utf8');
      child.stdout.on('data',bytes=>{if(overflow)return;data+=bytes.toString('utf8');if(Buffer.byteLength(data)>256*1024){overflow=true;kill('SIGTERM');}});
      child.once('close',code=>{
        upstream.removeEventListener('abort',abort);if(killTimer)clearTimeout(killTimer);
        if(upstream.aborted){reject(deadline.aborted&&!signal?.aborted&&!lifetime.signal.aborted?new OfficeToPdfError('timeout','Native Office conversion timed out.'):upstream.reason);return;}
        if(error||overflow){reject(new OfficeToPdfError('unavailable','Native Office helper failed.',{cause:error}));return;}
        try{
          const result=JSON.parse(data);if(result.error){const kind=codes.has(result.error.code)?result.error.code:'failed';throw new OfficeToPdfError(kind,'Native Office conversion failed.');}
          if(code!==0||!Array.isArray(result.missingFonts)||result.missingFonts.some((family:unknown)=>typeof family!=='string')||result.backend!=='linux-native')throw new Error('Invalid native Office reply.');
          resolve({missingFonts:result.missingFonts});
        }catch(cause){reject(cause instanceof OfficeToPdfError?cause:new OfficeToPdfError('failed','Native Office conversion failed.',{cause}));}
      });
      child.stdin.end(JSON.stringify({request,options:resolved}));
    });
    upstream.throwIfAborted();succeeded=true;return result;
    }finally{
      try{const current=await lstat(scratch,{bigint:true});if(current.dev!==identity.dev||current.ino!==identity.ino||!current.isDirectory())throw new OfficeToPdfError('failed','Native Office scratch identity changed.');
        await new Promise<void>((resolve,reject)=>{
          const cleanup=spawn('/usr/bin/python3',['-I','-B',helper,'--cleanup',String(process.pid),scratch,String(identity.dev),String(identity.ino)],{detached:true,env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',LC_ALL:'C.UTF-8'},stdio:['ignore','pipe','ignore']});let result='',error:unknown,overflow=false;
          cleanup.on('error',cause=>error=cause);cleanup.stdout.setEncoding('utf8');cleanup.stdout.on('data',bytes=>{if(overflow)return;result+=bytes;if(Buffer.byteLength(result)>8192){overflow=true;cleanup.kill('SIGKILL');}});
          cleanup.once('close',code=>{try{if(code!==0||error||overflow||JSON.parse(result).cleaned!==true)throw new Error('Native actor completion was not confirmed.');resolve();}catch(cause){const failure=new OfficeToPdfError('unavailable','Native Office cleanup remains unconfirmed.',{cause});lifetime.abort(failure);reject(failure);}});
        });
      }catch(cause){if((cause as NodeJS.ErrnoException).code!=='ENOENT')throw cause;}
      if(!succeeded)await rm(request.outputPath,{force:true});
    }
  };
  return {
    createScratch:createLinuxOfficeScratch,
    render(request,signal){const task=tail.then(()=>{lifetime.signal.throwIfAborted();signal?.throwIfAborted();return perform(request,signal);});tail=task.catch(()=>{});return task;},
    async dispose(){lifetime.abort(new Error('Native Office converter closed.'));await tail;},
  };
}
