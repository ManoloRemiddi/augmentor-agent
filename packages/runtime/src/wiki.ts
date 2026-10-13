// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash,randomUUID} from 'node:crypto';
import {existsSync,lstatSync,readFileSync,realpathSync,mkdirSync,readdirSync,openSync,writeFileSync,fsyncSync,closeSync,renameSync,unlinkSync,constants} from 'node:fs';
import {dirname,isAbsolute,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {Type} from 'typebox';
import type {ExtensionAPI,ExtensionContext,ToolDefinition} from '@earendil-works/pi-coding-agent';
import type {ExecutionContract} from './execution.js';
import {withWikiFs} from './wiki-fs.js';
import {createTools,type OriginalWikiTool} from '../vendor/dsh-plugin-wiki-tools/index.js';
import {Vault} from '../vendor/dsh-plugin-wiki-tools/lib/vault.js';

export interface WikiConfig {enabled:true;vaultPath:string;maxQueryResults:number;typeFolders:Record<string,string>}
export interface WikiProfile {enabled:boolean;vaultPath:string;maxQueryResults:number;typeFolders:Record<string,string>}
export function checkedWikiProfile(value:any):WikiProfile {
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>!['enabled','vaultPath','maxQueryResults','typeFolders'].includes(k))||typeof value.enabled!=='boolean')throw Error('Invalid Wiki configuration; its original is preserved.');
 const vaultPath=value.vaultPath??'',maxQueryResults=value.maxQueryResults??10,typeFolders=value.typeFolders??{};
 if(typeof vaultPath!=='string'||vaultPath.length>4096||vaultPath.includes('\0')||vaultPath&&(vaultPath==='/'||!isAbsolute(vaultPath)||resolve(vaultPath)!==vaultPath)||value.enabled&&!vaultPath)throw Error('Wiki vaultPath must be an explicit absolute normalized directory.');
 if(!Number.isSafeInteger(maxQueryResults)||maxQueryResults<1||maxQueryResults>100||!typeFolders||typeof typeFolders!=='object'||Array.isArray(typeFolders)||Object.values(typeFolders).some(v=>typeof v!=='string'))throw Error('Invalid Wiki query/routing configuration.');
 if(value.enabled&&process.platform!=='linux')throw Error('The Wiki binding currently requires Linux qualification.');
 if(vaultPath)new Vault(vaultPath,{typeFolders});
 return {enabled:value.enabled,vaultPath,maxQueryResults,typeFolders:structuredClone(typeFolders)};
}
const hash=(value:string)=>createHash('sha256').update(value).digest('hex');
function privateFile(path:string){const info=lstatSync(path);if(!info.isFile()||info.isSymbolicLink()||info.nlink!==1||info.size>16384||info.uid!==process.getuid!()||(info.mode&0o077)!==0)throw Error('Wiki private configuration/receipt is unsafe; its original is preserved.');return readFileSync(path,'utf8');}
export function wikiConfig(configDir:string):WikiConfig|undefined{
 const path=join(configDir,'wiki.json');try{lstatSync(path);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return;throw error;}
 const value=JSON.parse(privateFile(path));if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>!['schema','enabled','vaultPath','maxQueryResults','typeFolders'].includes(k))||value.schema!=='augmentor-wiki/1'||typeof value.enabled!=='boolean')throw Error('Invalid Wiki configuration; its original is preserved.');
 const {schema:_schema,...fields}=value,profile=checkedWikiProfile(fields);return profile.enabled?{...profile,enabled:true}:undefined;
}
type Receipt={schema:'augmentor-wiki-action/1';key:string;tool:string;state:'started'|'completed'|'refused'|'unknown'};
function directory(path:string){const missing:string[]=[];let existing=path;while(!existsSync(existing)){try{lstatSync(existing);throw Error('Linked Wiki receipt parent is unsafe.');}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}missing.unshift(existing);existing=dirname(existing);}if(realpathSync(existing)!==resolve(existing))throw Error('Linked Wiki receipt parent is unsafe.');for(const next of missing)mkdirSync(next,{mode:0o700});const info=lstatSync(path);if(!info.isDirectory()||info.isSymbolicLink()||info.uid!==process.getuid!()||(info.mode&0o077)!==0)throw Error('Wiki receipt directory is unsafe.');}
function save(path:string,value:Receipt,exclusive=false){const temp=exclusive?path:path+'.'+randomUUID()+'.tmp';const fd=openSync(temp,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);try{writeFileSync(fd,JSON.stringify(value)+'\n');fsyncSync(fd);}finally{closeSync(fd);}if(!exclusive)renameSync(temp,path);const parent=openSync(dirname(path),constants.O_RDONLY|constants.O_DIRECTORY|constants.O_NOFOLLOW);try{fsyncSync(parent);}finally{closeSync(parent);}}
function identity(id:string,name:string,ctx:ExtensionContext){const branch=ctx.sessionManager.getBranch();const assistant=[...branch].reverse().find(entry=>entry.type==='message'&&entry.message.role==='assistant'&&entry.message.content.some(part=>part.type==='toolCall'&&part.id===id));if(!assistant||assistant.type!=='message'||assistant.message.role!=='assistant')throw Error('Wiki mutation has no native assistant-call identity.');const matches=assistant.message.content.filter(part=>part.type==='toolCall'&&part.id===id);if(matches.length!==1||matches[0].type!=='toolCall'||matches[0].name!==name)throw Error('Wiki mutation native-call identity is ambiguous.');return hash(JSON.stringify([ctx.sessionManager.getSessionId(),assistant.id,id]));}
function schema(tool:OriginalWikiTool){const required:string[]=[],properties:Record<string,unknown>={};for(const [name,raw] of Object.entries(tool.parameters)){const {required:needed,...property}=raw;if(needed)required.push(name);properties[name]=property;}return Type.Unsafe({type:'object',properties,required,additionalProperties:false});}
const writers=new Map<string,Promise<void>>();
async function serial<T>(key:string,fn:()=>Promise<T>){const prior=writers.get(key)??Promise.resolve();let release!:()=>void;const held=new Promise<void>(r=>release=r);writers.set(key,held);await prior;try{return await fn();}finally{release();if(writers.get(key)===held)writers.delete(key);}}

export class WikiBinding {
 readonly skillPath=fileURLToPath(new URL('../vendor/dsh-plugin-wiki-skills/skills',import.meta.url));
 private definitions:OriginalWikiTool[];private receipts:string;
 constructor(readonly config:WikiConfig,stateDir:string){this.definitions=createTools(new Vault(config.vaultPath,{typeFolders:config.typeFolders}),config);this.receipts=join(stateDir,'wiki-actions',hash(config.vaultPath));}
 isRead(name:string){return name==='wiki_query';}
 private known(){directory(this.receipts);const names=readdirSync(this.receipts);if(names.length>2048||names.some(name=>!/^([a-f0-9]{64}\.json|\.operation-lock)$/.test(name)))throw Error('Wiki action receipts need operator inspection; no mutation is admitted.');return names.filter(name=>name.endsWith('.json')).map(name=>{const value=JSON.parse(privateFile(join(this.receipts,name))) as Receipt;if(value.schema!=='augmentor-wiki-action/1'||value.key+'.json'!==name||!['started','completed','refused','unknown'].includes(value.state))throw Error('Invalid Wiki action receipt; its original is preserved.');return value;});}
 factory=(pi:ExtensionAPI)=>{
  pi.on('resources_discover',()=>({skillPaths:[this.skillPath]}));
  pi.on('tool_result',(event,ctx)=>{if(this.definitions.some(tool=>tool.name===event.toolName)&&!this.isRead(event.toolName)&&(event.details as {stop?:boolean})?.stop)ctx.abort();});
  for(const original of this.definitions){const read=this.isRead(original.name);
  const definition:ToolDefinition&{augmentorExecution:ExecutionContract}={name:original.name,label:original.name,description:original.description,parameters:schema(original),annotations:{readOnlyHint:read,idempotentHint:read,openWorldHint:false},augmentorExecution:{effect:()=>read?'read':'change',outcome:(_args,result)=>({status:(result.details as {outcome?:'completed'|'unknown'|'failed-before-dispatch'})?.outcome??(read?'completed':'unknown')})},
   execute:async(id,args,signal,_update,ctx)=>{
    const input=args as Record<string,unknown>;
    const reply=(reason:string,outcome:'unknown'|'failed-before-dispatch',stop=outcome==='unknown')=>({content:[{type:'text' as const,text:reason}],details:{outcome,stop},isError:true});
    if(read){try{const value=await withWikiFs(this.config.vaultPath,false,signal,()=>original.execute(input));return {content:original.output.render(input,value),details:{outcome:'completed',value}};}catch(error){return reply((error as Error).message,'failed-before-dispatch');}}
    return serial(this.config.vaultPath,async()=>{
     let receipt:Receipt|undefined,path:string|undefined,lock:number|undefined,attempted=false;
     try{signal?.throwIfAborted();const key=identity(id,original.name,ctx),known=this.known();if(known.some(row=>row.key===key))return reply('This native Wiki action already has a receipt. Inspect its original; it is not replayed.','failed-before-dispatch');if(known.some(row=>['started','unknown'].includes(row.state)))return reply('A Wiki vault mutation is uncertain. An operator must inspect its receipt and vault before another change.','failed-before-dispatch',true);
      lock=openSync(join(this.receipts,'.operation-lock'),constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);
      receipt={schema:'augmentor-wiki-action/1',key,tool:original.name,state:'started'};path=join(this.receipts,key+'.json');save(path,receipt,true);
      const value=await withWikiFs(this.config.vaultPath,true,signal,()=>original.execute(input),()=>attempted=true,original.name==='wiki_scaffold');
      save(path,{...receipt,state:'completed'});return {content:original.output.render(input,value),details:{outcome:'completed',value}};
     }catch(error){const outcome=attempted?'unknown':'failed-before-dispatch';if(path&&receipt)try{save(path,{...receipt,state:attempted?'unknown':'refused'});}catch{/* The preserved started receipt still blocks another mutation. */}return reply((error as Error).message+(attempted?' The vault change is unconfirmed; do not replay automatically.':''),outcome);
     }finally{if(lock!==undefined){closeSync(lock);unlinkSync(join(this.receipts,'.operation-lock'));}}
    });
   }
  };pi.registerTool(definition);
 }};
}
export function configuredWiki(configDir:string,stateDir:string){const config=wikiConfig(configDir);return config?new WikiBinding(config,stateDir):undefined;}
