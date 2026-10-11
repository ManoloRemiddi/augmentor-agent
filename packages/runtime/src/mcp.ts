// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync,readFileSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {createCodemodeExtension,createMcpExtension,createToolSearchExtension,type ExtensionAPI,type ExtensionContext,type ExtensionFactory,type McpServerConfig,type RegisteredCommand} from '@earendil-works/pi-coding-agent';
import {privateDir} from './storage.js';
import {createManagedMcpTransport} from './mcp-transport.js';
import {MCP_TRANSPORT_ORIGINAL_TYPE} from './mcp-originals.js';
import {MCP_AUTHORIZATION_TYPE,savedMcpAuthorization,type McpAuthorizationObservation} from './mcp-authorization.js';
import type {McpManagementAction} from './mcp-management.js';

const discovery=new Set(['codemode','tool_search','list_mcp_resources','list_mcp_resource_templates','read_mcp_resource']);
const object=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value);
/** Managed global configuration only. The SDK validates registrations and owns
 * MCP transport, OAuth and nested tool execution; this is no second tool loop.
 */
export class ManagedMcp {
 private api?:ExtensionAPI;
 private command?:RegisteredCommand['handler'];
 private manager?:ExtensionContext['sessionManager'];
 private authorizationGaps=new Map<string,McpAuthorizationObservation>();
 private errors:string[]=[];
 private readTools=new Set<string>();
 private entries:Record<string,unknown>={};
 private autoEnableCodemode=true;
 private retainLogs=false;
 readonly source:string;
 constructor(agentDir:string,private stateDir:string,private sessionId:string,private authorizationChanged?:(event:McpAuthorizationObservation,retained:boolean)=>void,private openAuthorization?:(url:string)=>void){
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
  pi.on('session_start',(_event,ctx)=>{this.manager=ctx.sessionManager;});
  for(const [name,config] of Object.entries(this.entries)){
   const namespace=name.replaceAll('-','_');
   try{
    if(name.length>128||namespaces.has(namespace))throw Error('identity');
    pi.registerMcpServer(name,config as McpServerConfig);namespaces.add(namespace);
   }catch{this.errors.push('A managed MCP server could not be registered; check its name and configuration.');}
  }
 };
 factories():ExtensionFactory[]{const builtin=createMcpExtension({
  // Registrations above are validated by public ExtensionAPI. Do not admit
  // project files or Pi's default global config outside this managed profile.
  loadConfig:()=>({servers:[],errors:[...this.errors],autoEnableCodemode:this.autoEnableCodemode}),
  createTransport:createManagedMcpTransport(original=>{
   if(!this.api)return false;
   this.api.appendEntry(MCP_TRANSPORT_ORIGINAL_TYPE,original);return true;
  },event=>{
   if(!this.api)return false;
   let retained=false;try{this.api.appendEntry(MCP_AUTHORIZATION_TYPE,event);retained=true;this.authorizationGaps.delete(event.server);}catch{this.authorizationGaps.set(event.server,event);}
   this.authorizationChanged?.(event,retained);return retained;
  }),
  logPath:this.retainLogs?join(privateDir(join(this.stateDir,'mcp-logs')),this.sessionId+'.log'):process.platform==='win32'?'NUL':'/dev/null',
  // The operator surface presents this ephemeral URL. The SDK must not launch
  // an unrelated default browser or place the URL in retained notifications.
  openUrl:url=>{if(!this.openAuthorization)throw Error('Open MCP management to sign in.');this.openAuthorization(url);},
 });
  const managed:ExtensionFactory=pi=>builtin(new Proxy(pi,{get:(target,key)=>{
   if(key==='registerCommand')return (name:string,options:Omit<RegisteredCommand,'name'|'sourceInfo'>)=>{if(name==='mcp')this.command=options.handler;target.registerCommand(name,options);};
   return Reflect.get(target,key);
  }}));
  return [createCodemodeExtension({models:false}),createToolSearchExtension(),this.register,managed];
 }
 managementCommand(action:McpManagementAction,name:string){
  if(!this.command||!this.api)throw Error('MCP management is unavailable for this conversation.');
  const server=this.api.getMcpServers().find(row=>row.name===name);
  if(!server||server.config.enabled===false)throw Error('Choose an enabled registered MCP server.');
  if(action!=='reconnect'&&!this.managementActions(server.config).includes(action))throw Error('This MCP server does not support OAuth management.');
  return this.command;
 }
 private managementActions(config:McpServerConfig):McpManagementAction[]{
  if(config.enabled===false)return [];
  const oauth='url' in config&&!Object.keys(config.headers??{}).some(name=>name.toLowerCase()==='authorization');
  return oauth?['login','logout','reconnect']:['reconnect'];
 }
 isRead(name:string){
  if(discovery.has(name))return true;
  return this.readTools.has(name)&&this.api?.getAllTools().some(tool=>tool.name===name)===true;
 }
 describe(){
  const tools=this.api?.getAllTools()??[],active=new Set(this.api?.getActiveTools()??[]),servers=this.api?.getMcpServers()??[];let remaining=256;
  const authorization=new Map<string,McpAuthorizationObservation>();
  for(const entry of this.manager?.getBranch()??[])if(entry.type==='custom'&&entry.customType===MCP_AUTHORIZATION_TYPE){const row=savedMcpAuthorization(entry.data);if(row)authorization.set(row.server,row);}
  return {available:!!this.api,source:'managed-profile-mcp.json',projectConfiguration:false,modelsInCodemode:false,retainServerLogs:this.retainLogs,configurationErrors:this.errors.length,
   coverage:'registered MCP tool catalog; not a connection health probe',serverCount:servers.length,omittedServers:Math.max(0,servers.length-64),servers:servers.slice(0,64).map(entry=>{
    const namespace='mcp__'+entry.name.replaceAll('-','_'),registered=tools.filter(tool=>tool.namespace?.name===namespace),shown=registered.filter(tool=>tool.name.length<=256).slice(0,remaining);remaining-=shown.length;
    const lastObserved=authorization.get(entry.name)??null,gap=this.authorizationGaps.get(entry.name);
    return {name:entry.name,enabled:entry.config.enabled!==false,transport:'url' in entry.config?'http':'stdio',exposure:entry.config.exposure??'codemode',managementActions:this.managementActions(entry.config),toolCount:registered.length,omittedToolNames:registered.length-shown.length,toolNames:shown.map(tool=>tool.name),declaredToolNames:shown.filter(tool=>active.has(tool.name)).map(tool=>tool.name),readOnlyToolNames:shown.filter(tool=>this.readTools.has(tool.name)).map(tool=>tool.name),authorization:{coverage:'last recorded HTTP authorization observation on the selected Pi branch; not current credential health',lastObserved,unsaved:gap??null,retention:gap?'native-append-failed':lastObserved?'sdk-native-entry-policy':'not-observed'}};
   })};
 }
}
