// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {WikiReceipts,wikiActionKey,type WikiReceipt} from './wiki-receipts.js';
import {lstatSync,readFileSync} from 'node:fs';
import {isAbsolute,join,resolve} from 'node:path';
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
function privateFile(path:string){const info=lstatSync(path);if(!info.isFile()||info.isSymbolicLink()||info.nlink!==1||info.size>16384||info.uid!==process.getuid!()||(info.mode&0o077)!==0)throw Error('Wiki private configuration/receipt is unsafe; its original is preserved.');return readFileSync(path,'utf8');}
export function wikiConfig(configDir:string):WikiConfig|undefined{
 const path=join(configDir,'wiki.json');try{lstatSync(path);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return;throw error;}
 const value=JSON.parse(privateFile(path));if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>!['schema','enabled','vaultPath','maxQueryResults','typeFolders'].includes(k))||value.schema!=='augmentor-wiki/1'||typeof value.enabled!=='boolean')throw Error('Invalid Wiki configuration; its original is preserved.');
 const {schema:_schema,...fields}=value,profile=checkedWikiProfile(fields);return profile.enabled?{...profile,enabled:true}:undefined;
}
function identity(id:string,name:string,ctx:ExtensionContext){const branch=ctx.sessionManager.getBranch();const assistant=[...branch].reverse().find(entry=>entry.type==='message'&&entry.message.role==='assistant'&&entry.message.content.some(part=>part.type==='toolCall'&&part.id===id));if(!assistant||assistant.type!=='message'||assistant.message.role!=='assistant')throw Error('Wiki mutation has no native assistant-call identity.');const matches=assistant.message.content.filter(part=>part.type==='toolCall'&&part.id===id);if(matches.length!==1||matches[0].type!=='toolCall'||matches[0].name!==name)throw Error('Wiki mutation native-call identity is ambiguous.');return wikiActionKey(ctx.sessionManager.getSessionId(),assistant.id,id);}
function schema(tool:OriginalWikiTool){const required:string[]=[],properties:Record<string,unknown>={};for(const [name,raw] of Object.entries(tool.parameters)){const {required:needed,...property}=raw;if(needed)required.push(name);properties[name]=property;}return Type.Unsafe({type:'object',properties,required,additionalProperties:false});}
const writers=new Map<string,Promise<void>>();
async function serial<T>(key:string,fn:()=>Promise<T>){const prior=writers.get(key)??Promise.resolve();let release!:()=>void;const held=new Promise<void>(r=>release=r);writers.set(key,held);await prior;try{return await fn();}finally{release();if(writers.get(key)===held)writers.delete(key);}}

export class WikiBinding {
 readonly skillPath=fileURLToPath(new URL('../vendor/dsh-plugin-wiki-skills/skills',import.meta.url));
 private definitions:OriginalWikiTool[];readonly receipts:WikiReceipts;
 constructor(readonly config:WikiConfig,stateDir:string){this.definitions=createTools(new Vault(config.vaultPath,{typeFolders:config.typeFolders}),config);this.receipts=new WikiReceipts(stateDir,config.vaultPath);}
 isRead(name:string){return name==='wiki_query';}
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
     let receipt:WikiReceipt|undefined,release:(()=>void)|undefined,attempted=false,admitted=false;
     try{signal?.throwIfAborted();const key=identity(id,original.name,ctx),known=this.receipts.describe();
      if(known.rows.some(row=>row.key===key))return reply('This native Wiki action already has a receipt. Inspect its original; it is not replayed.','failed-before-dispatch');
      if(known.blocked)return reply('A Wiki vault mutation or operation lock is uncertain. Inspect the recorded action and vault in Wiki settings before another change.','failed-before-dispatch',true);
      release=this.receipts.acquire();const confirmed=this.receipts.describe(true);
      if(confirmed.rows.some(row=>row.key===key)||confirmed.blocked)return reply('Wiki receipts changed before dispatch. Inspect their originals; nothing was replayed.','failed-before-dispatch',true);
      receipt=this.receipts.start(key,original.name);admitted=true;
      const value=await withWikiFs(this.config.vaultPath,true,signal,()=>original.execute(input),()=>attempted=true,original.name==='wiki_scaffold');
      this.receipts.finish(receipt,'completed');return {content:original.output.render(input,value),details:{outcome:'completed',value}};
     }catch(error){const outcome=attempted?'unknown':'failed-before-dispatch';if(receipt)try{this.receipts.finish(receipt,attempted?'unknown':'refused');}catch{/* The preserved started receipt still blocks another mutation. */}return reply((error as Error).message+(attempted?' The vault change is unconfirmed; do not replay automatically.':''),outcome,!admitted||attempted||(error as NodeJS.ErrnoException).code==='EEXIST');
     }finally{try{release?.();}catch(error){return reply('Wiki lock cleanup is unconfirmed: '+(error as Error).message,'unknown');}}
    });
   }
  };pi.registerTool(definition);
 }};
}
export function configuredWiki(configDir:string,stateDir:string){const config=wikiConfig(configDir);return config?new WikiBinding(config,stateDir):undefined;}
