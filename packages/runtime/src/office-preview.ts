// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {OfficeToPdf,type Config,type OfficeConverterFactory} from '../vendor/dsh-office/index.js';
import {PreviewReadError} from './file-preview.js';

export interface WorkspaceFileScope {sessionId:string;workspaceRoot:string;}
export interface WorkspaceFileStat {absolutePath:string;version:string;bytes:number;}
export interface WorkspaceFileBytes extends WorkspaceFileStat {offset:number;eof:boolean;data:Uint8Array;}
export interface OfficePreviewSeat {
  effect(setup:()=>()=>Promise<void>):void;
  get(name:'workspaceFiles'):{
    readBytes(scope:WorkspaceFileScope,path:string,params:any,signal:AbortSignal):Promise<WorkspaceFileBytes>;
    stat(scope:WorkspaceFileScope,path:string,signal:AbortSignal):Promise<WorkspaceFileStat>;
  };
}
/** The same complete-byte ceiling as file previews; CPU conversion admission is
 * independent of chat/model settings and keeps the original supplier queue. */
export const OFFICE_PREVIEW_LIMITS:Readonly<Config>={
  maxConcurrentConversions:1,maxQueuedJobs:4,maxReaders:16,
  maxSourceBytes:20*1024*1024,maxBackgroundConversions:0,
  maxCachedEntries:8,maxCachedBytes:64*1024*1024,maxSourceEntries:64,
  timeoutMs:60_000,maxInputBytes:20*1024*1024,maxOutputBytes:20*1024*1024,
  maxImageResolution:192,maxArchiveEntries:10_000,maxUncompressedBytes:250*1024*1024,
  maxFontFiles:20_000,maxFontFileBytes:256*1024*1024,maxLoadedFontBytes:512*1024*1024,
};
type AuthorizedRead=(scope:WorkspaceFileScope,kind:'stat'|'bytes',params:any,signal:AbortSignal)=>Promise<any>;

/** Adapter seat for the original MIT provider; construction starts no engine,
 * Session, tool, model request or permanent document storage. */
export class PiOfficePreview {
  private readonly provider:OfficeToPdf;
  private readonly disposers:Array<()=>Promise<void>>=[];
  private closing?:Promise<void>;
  constructor(read:AuthorizedRead,converterFactory?:OfficeConverterFactory){
    const files={readBytes:(scope:WorkspaceFileScope,path:string,params:any,signal:AbortSignal)=>read(scope,'bytes',{path,...params},signal),
      stat:(scope:WorkspaceFileScope,path:string,signal:AbortSignal)=>read(scope,'stat',{path},signal)};
    this.provider=new OfficeToPdf({get:()=>files,effect:setup=>{this.disposers.push(setup());}}, {...OFFICE_PREVIEW_LIMITS,...(converterFactory?{converterFactory}:{})});
  }
  get busy(){return this.provider.busy;}
  generation(signal:AbortSignal){if(this.closing)throw new PreviewReadError('gateway/service-unavailable','Office previews are unavailable.');return this.provider.getGeneration(signal);}
  render(scope:WorkspaceFileScope,params:any,signal:AbortSignal){
    if(this.closing)throw new PreviewReadError('gateway/service-unavailable','Office previews are unavailable.');
    if(typeof params.path!=='string'||!params.path||params.path.length>4096||params.path.includes('\0')||params.priority!==undefined&&params.priority!=='foreground'&&params.priority!=='background')throw new PreviewReadError('gateway/bad-request','Invalid Office preview request.');
    return this.provider.render(scope,params.path,params.priority??'foreground',signal);
  }
  close(){return this.closing??=Promise.all(this.disposers.map(dispose=>dispose())).then(()=>{});}
}
