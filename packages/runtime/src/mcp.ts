// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync,readFileSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {createCodemodeExtension,createMcpExtension,createToolSearchExtension,type ExtensionAPI,type ExtensionFactory,type McpServerConfig} from '@earendil-works/pi-coding-agent';
import {privateDir} from './storage.js';
import {createManagedMcpTransport} from './mcp-transport.js';

const discovery=new Set(['codemode','tool_search','list_mcp_resources','list_mcp_resource_templates','read_mcp_resource']);
const object=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value);
/** Managed global configuration only. The SDK validates registrations and owns
 * MCP transport, OAuth and nested tool execution; this is no second tool loop.
 */
export class ManagedMcp {
 private api?:ExtensionAPI;
 private errors:string[]=[];
 private readTools=new Set<string>();
 private entries:Record<string,unknown>={};
 private autoEnableCodemode=true;
 private retainLogs=false;
 readonly source:string;
 constructor(agentDir:string,private stateDir:string,private sessionId:string){
  this.source=join(agentDir,'mcp.json');
  try{
   if(!existsSync(this.source))return;
   if(statSync(this.source).size>1024*1024)throw Error('size');
   const config:unknown=JSON.parse(readFileSync(this.source,'utf8'));
   if(!object(config)||!object(config.mcpServers)||Object.keys(config.mcpServers).length>64)throw Error('shape');
   if(config.autoEnableCodemode!==undefined&&typeof config.autoEnableCodemode!=='boolean')throw Error('discovery');
   const augmentor=config.augmentor??{};if(!object(augmentor))throw Error('policy');
   if(augmentor.retainServerLogs!==undefined&&typeof augmentor.retainServerLogs!=='boolean')throw Error('logging');
   const readTools=augmentor.readOnlyTools??[];
   if(!Array.isArray(readTools)||readTools.length>256||readTools.some(name=>typeof name!=='string'||name.length>256||!/^mcp__[a-zA-Z0-9_]+$/.test(name)))throw Error('read tools');
   this.entries=config.mcpServers;this.autoEnableCodemode=config.autoEnableCodemode!==false;this.retainLogs=augmentor.retainServerLogs===true;this.readTools=new Set(readTools);
  }catch{this.errors=['Managed MCP configuration is invalid or exceeds its limits; no configured server was admitted.'];}
 }
 private register:ExtensionFactory=pi=>{
  this.api=pi;const namespaces=new Set<string>();
  for(const [name,config] of Object.entries(this.entries)){
   const namespace=name.replaceAll('-','_');
   try{
    if(name.length>128||namespaces.has(namespace))throw Error('identity');
    pi.registerMcpServer(name,config as McpServerConfig);namespaces.add(namespace);
   }catch{this.errors.push('A managed MCP server could not be registered; check its name and configuration.');}
  }
 };
 factories():ExtensionFactory[]{return [createCodemodeExtension({models:false}),createToolSearchExtension(),this.register,createMcpExtension({
  // Registrations above are validated by public ExtensionAPI. Do not admit
  // project files or Pi's default global config outside this managed profile.
  loadConfig:()=>({servers:[],errors:[...this.errors],autoEnableCodemode:this.autoEnableCodemode}),
  createTransport:createManagedMcpTransport(original=>{
   if(!this.api)return false;
   this.api.appendEntry('augmentor-mcp-transport/1',original);return true;
  }),
  logPath:this.retainLogs?join(privateDir(join(this.stateDir,'mcp-logs')),this.sessionId+'.log'):process.platform==='win32'?'NUL':'/dev/null',
 })];}
 isRead(name:string){
  if(discovery.has(name))return true;
  return this.readTools.has(name)&&this.api?.getAllTools().some(tool=>tool.name===name)===true;
 }
 describe(){
  const tools=this.api?.getAllTools()??[],active=new Set(this.api?.getActiveTools()??[]),servers=this.api?.getMcpServers()??[];let remaining=256;
  return {available:!!this.api,source:'managed-profile-mcp.json',projectConfiguration:false,modelsInCodemode:false,retainServerLogs:this.retainLogs,configurationErrors:this.errors.length,
   coverage:'registered MCP tool catalog; not a connection health probe',serverCount:servers.length,omittedServers:Math.max(0,servers.length-64),servers:servers.slice(0,64).map(entry=>{
    const namespace='mcp__'+entry.name.replaceAll('-','_'),registered=tools.filter(tool=>tool.namespace?.name===namespace),shown=registered.filter(tool=>tool.name.length<=256).slice(0,remaining);remaining-=shown.length;
    return {name:entry.name,enabled:entry.config.enabled!==false,transport:'url' in entry.config?'http':'stdio',exposure:entry.config.exposure??'codemode',toolCount:registered.length,omittedToolNames:registered.length-shown.length,toolNames:shown.map(tool=>tool.name),declaredToolNames:shown.filter(tool=>active.has(tool.name)).map(tool=>tool.name),readOnlyToolNames:shown.filter(tool=>this.readTools.has(tool.name)).map(tool=>tool.name)};
   })};
 }
}
