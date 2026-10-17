// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {existsSync,readFileSync,statSync} from 'node:fs';
import {DefaultResourceLoader,SettingsManager,type ExtensionAPI,type McpServerConfig} from '@earendil-works/pi-coding-agent';
import {atomicJson} from './storage.js';

const object=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value);
export const mcpDigest=(text:string)=>createHash('sha256').update(text).digest('hex');
export interface McpProfile {
 document:Record<string,unknown>;servers:Map<string,McpServerConfig>;readTools:Set<string>;autoEnableCodemode:boolean;retainLogs:boolean;
}
export function readMcpProfile(file:string){
 try{if(!existsSync(file))return {text:'{\n  "mcpServers": {}\n}\n',revision:'missing'};
  if(statSync(file).size>1024*1024)throw Error('size');const text=readFileSync(file,'utf8');return {text,revision:mcpDigest(text)};
 }catch{throw Error('The managed MCP profile could not be read within its limits.');}
}
export function parseMcpProfile(text:unknown){
 try{
  if(typeof text!=='string'||Buffer.byteLength(text)>1024*1024)throw Error('size');const document:unknown=JSON.parse(text);
  if(!object(document)||!object(document.mcpServers)||Object.keys(document.mcpServers).length>64)throw Error('shape');
  if(document.autoEnableCodemode!==undefined&&typeof document.autoEnableCodemode!=='boolean')throw Error('discovery');
  const augmentor=document.augmentor??{};if(!object(augmentor))throw Error('policy');
  if(augmentor.retainServerLogs!==undefined&&typeof augmentor.retainServerLogs!=='boolean')throw Error('logging');
  const readTools=augmentor.readOnlyTools??[];
  if(!Array.isArray(readTools)||readTools.length>256||readTools.some(name=>typeof name!=='string'||name.length>256||!/^mcp__[a-zA-Z0-9_]+$/.test(name)))throw Error('read tools');
  const names=new Set<string>();for(const name of Object.keys(document.mcpServers)){const namespace=name.replaceAll('-','_');if(!/^[-a-zA-Z0-9_]{1,128}$/.test(name)||names.has(namespace))throw Error('name');names.add(namespace);}
  return {document,readTools:new Set(readTools as string[]),autoEnableCodemode:document.autoEnableCodemode!==false,retainLogs:augmentor.retainServerLogs===true};
 }catch{throw Error('The MCP profile must be valid JSON with at most 64 distinct server namespaces and valid Augmentor policy settings.');}
}
/** Public registration validation only: no AgentSession, MCP factory, transport,
 * provider request or trusted configuration command is created/executed here.
 */
export async function prepareMcpProfile(text:unknown,cwd:string,agentDir:string):Promise<McpProfile>{
 const parsed=parseMcpProfile(text);let api:ExtensionAPI|undefined;
 const loader=new DefaultResourceLoader({cwd,agentDir,settingsManager:SettingsManager.inMemory({packages:[],enableInstallTelemetry:false,enableAnalytics:false,cacheWarming:'off',defaultProjectTrust:'never'}),noExtensions:true,noSkills:true,noContextFiles:true,noThemes:true,noPromptTemplates:true,
  extensionFactories:[pi=>{api=pi;for(const [name,config] of Object.entries(parsed.document.mcpServers as Record<string,unknown>))pi.registerMcpServer(name,config as McpServerConfig);} ]});
 try{await loader.reload();if(loader.getExtensions().errors.length||!api)throw Error('registration');return {...parsed,servers:new Map(api.getMcpServers().map(row=>[row.name,row.config]))};}
 catch{throw Error('Pi rejected an MCP server definition. Check its transport, exposure, authentication and timeout fields. No profile was saved.');}
}
export function saveMcpProfile(file:string,expectedRevision:string,profile:McpProfile,beforeWrite:()=>void=()=>{}){
 const serialized=JSON.stringify(profile.document,null,2)+'\n';if(Buffer.byteLength(serialized)>1024*1024)throw Error('The formatted MCP profile exceeds its storage limit. No profile was saved.');
 if(readMcpProfile(file).revision!==expectedRevision)throw Error('The MCP profile changed since it was read. Reload it before saving.');
 beforeWrite();atomicJson(file,profile.document);return mcpDigest(serialized);
}
