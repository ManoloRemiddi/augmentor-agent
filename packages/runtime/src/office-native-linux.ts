// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process';
import {homedir} from 'node:os';
import {join,dirname,basename} from 'node:path';
import {constants} from 'node:fs';
import type {BigIntStats} from 'node:fs';
import type {FileHandle} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {readFile,lstat,open,unlink,mkdtemp} from 'node:fs/promises';
import type {ConverterOptions} from '../vendor/office-entry/index.js';
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
    let succeeded=false,scratch:string|undefined,identity:BigIntStats|undefined;
    let parent:FileHandle|undefined,output:FileHandle|undefined,outputIdentity:BigIntStats|undefined;
    const outputName=basename(request.outputPath);
    const ownedOutput=async(missingOk=false)=>{
      let current:BigIntStats;
      try{current=await lstat('/proc/self/fd/'+parent!.fd+'/'+outputName,{bigint:true});}
      catch(cause){if((cause as NodeJS.ErrnoException).code!=='ENOENT')throw cause;if(missingOk)return false;const failure=new OfficeToPdfError('invalid-output','Native Office output is no longer linked.');lifetime.abort(failure);throw failure;}
      if(!current.isFile()||current.dev!==outputIdentity!.dev||current.ino!==outputIdentity!.ino||current.uid!==BigInt(process.getuid!())||Number(current.mode&0o777n)!==0o600){
        const failure=new OfficeToPdfError('invalid-output','Native Office output identity changed.');lifetime.abort(failure);throw failure;
      }
      return true;
    };
    try{
      parent=await open(dirname(request.outputPath),constants.O_RDONLY|constants.O_DIRECTORY|constants.O_NOFOLLOW);
      try{output=await open('/proc/self/fd/'+parent.fd+'/'+outputName,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);}
      catch(cause){if((cause as NodeJS.ErrnoException).code==='EEXIST')throw new OfficeToPdfError('invalid-output','Native Office output already exists.');throw cause;}
      outputIdentity=await output.stat({bigint:true});
      scratch=await mkdtemp(join(dirname(request.outputPath),'augmentor-native-office-'));
      identity=await lstat(scratch,{bigint:true});
      upstream.throwIfAborted();const result=await new Promise<{missingFonts:string[]}>((resolve,reject)=>{
      // Node owns the cleanup helper directly. Its separate-session broker has
      // a kernel death kill; namespace monitors own the native descendants.
      const child=spawn('/usr/bin/python3',['-I','-B',helper,String(process.pid),scratch!,String(identity!.dev),String(identity!.ino),outputName],{detached:true,env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',LC_ALL:'C.UTF-8',TZ:'UTC'},stdio:['pipe','pipe','ignore',output!.fd,parent!.fd]});
      let data='',overflow=false,error:unknown,killTimer:NodeJS.Timeout|undefined;
      const kill=(kind:NodeJS.Signals)=>{if(child.pid&&child.exitCode===null){try{process.kill(-child.pid,kind);}catch(cause){if((cause as NodeJS.ErrnoException).code!=='ESRCH')error=cause;}}};
      const abort=()=>{kill('SIGTERM');killTimer=setTimeout(()=>kill('SIGKILL'),2000);killTimer.unref();};
      upstream.addEventListener('abort',abort,{once:true});if(upstream.aborted)abort();
      child.on('error',cause=>{error=cause;});child.stdin!.on('error',()=>{});child.stdout!.setEncoding('utf8');
      child.stdout!.on('data',bytes=>{if(overflow)return;data+=bytes.toString('utf8');if(Buffer.byteLength(data)>256*1024){overflow=true;kill('SIGTERM');}});
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
      child.stdin!.end(JSON.stringify({request,options:resolved}));
    });
    upstream.throwIfAborted();succeeded=true;return result;
    }finally{
      let cleaned=false;
      try{
        if(scratch&&identity){
          try{const current=await lstat(scratch,{bigint:true});if(current.dev!==identity.dev||current.ino!==identity.ino||!current.isDirectory())throw new OfficeToPdfError('failed','Native Office scratch identity changed.');
            await new Promise<void>((resolve,reject)=>{
              const cleanup=spawn('/usr/bin/python3',['-I','-B',helper,'--cleanup',String(process.pid),scratch!,String(identity!.dev),String(identity!.ino)],{detached:true,env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',LC_ALL:'C.UTF-8'},stdio:['ignore','pipe','ignore']});let result='',error:unknown,overflow=false;
              cleanup.on('error',cause=>error=cause);cleanup.stdout.setEncoding('utf8');cleanup.stdout.on('data',bytes=>{if(overflow)return;result+=bytes;if(Buffer.byteLength(result)>8192){overflow=true;cleanup.kill('SIGKILL');}});
              cleanup.once('close',code=>{try{if(code!==0||error||overflow||JSON.parse(result).cleaned!==true)throw new Error('Native actor completion was not confirmed.');resolve();}catch(cause){const failure=new OfficeToPdfError('unavailable','Native Office cleanup remains unconfirmed.',{cause});lifetime.abort(failure);reject(failure);}});
            });
          }catch(cause){if((cause as NodeJS.ErrnoException).code!=='ENOENT'){lifetime.abort(cause);throw cause;}}
        }
        cleaned=true;
        if(succeeded){try{upstream.throwIfAborted();const currentParent=await lstat(dirname(request.outputPath),{bigint:true}),originalParent=await parent!.stat({bigint:true});if(!currentParent.isDirectory()||currentParent.dev!==originalParent.dev||currentParent.ino!==originalParent.ino)throw new OfficeToPdfError('invalid-output','Native Office output parent changed.');await ownedOutput();upstream.throwIfAborted();}catch(cause){succeeded=false;lifetime.abort(cause);throw cause;}}
      }finally{
        try{
          if(output&&outputIdentity&&(!succeeded||!cleaned)){
            try{if(await ownedOutput(true))await unlink('/proc/self/fd/'+parent!.fd+'/'+outputName);}
            catch(cause){if((cause as NodeJS.ErrnoException).code!=='ENOENT')throw cause;}
          }
        }finally{try{await output?.close();}finally{await parent?.close();}}
      }
    }
  };
  return {
    createScratch:createLinuxOfficeScratch,
    render(request,signal){const task=tail.then(()=>{lifetime.signal.throwIfAborted();signal?.throwIfAborted();return perform(request,signal);});tail=task.catch(()=>{});return task;},
    async dispose(){lifetime.abort(new Error('Native Office converter closed.'));await tail;},
  };
}
