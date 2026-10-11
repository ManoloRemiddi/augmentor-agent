// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {join} from 'node:path';
import {createCodemodeExtension,createMcpExtension,createToolSearchExtension,type ExtensionAPI,type ExtensionContext,type ExtensionFactory,type McpServerConfig,type RegisteredCommand} from '@earendil-works/pi-coding-agent';
import {privateDir} from './storage.js';
import {createManagedMcpTransport} from './mcp-transport.js';
import {MCP_TRANSPORT_ORIGINAL_TYPE} from './mcp-originals.js';
import {MCP_AUTHORIZATION_TYPE,savedMcpAuthorization,type McpAuthorizationObservation} from './mcp-authorization.js';
import type {McpManagementAction} from './mcp-management.js';
import {readMcpProfile,type McpProfile} from './mcp-profile.js';
import {MCP_CONNECTION_TYPE,savedMcpConnection,connectionSummary,type McpConnectionSummary,type McpConnectionObservation} from './mcp-connection.js';
import {McpCallContext} from './mcp-call-context.js';

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
 private owned=new Set<string>();
 private revision='missing';
 private pending=false;
 private requestedOptions?:{autoEnableCodemode:boolean;retainLogs:boolean};
 private reloadPending=false;
 private autoCodemodeActivated=false;
 private inheritedAutoCodemode=false;
 private registrationWait?:{snapshot:string;finish:()=>void};
 private connections=new Map<string,{summary:McpConnectionSummary;unsaved:number}>();
 private connectionTrackingDropped=0;
 private calls:McpCallContext;
 readonly source:string;
 constructor(agentDir:string,private stateDir:string,private sessionId:string,private authorizationChanged?:(event:McpAuthorizationObservation,retained:boolean)=>void,private openAuthorization?:(url:string)=>void,private connectionChanged?:(event:McpConnectionObservation,retained:boolean)=>void,owner?:()=>{hostTurnId?:string;hostRequestId?:string;modelRequestObservationId?:string}){
  this.calls=new McpCallContext(sessionId,owner);
  this.source=join(agentDir,'mcp.json');
  try{
   const initial=readMcpProfile(this.source);this.revision=initial.revision;
   if(initial.revision==='missing')return;
   const config:unknown=JSON.parse(initial.text);
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
  this.calls.observe(pi);
  this.api=pi;const namespaces=new Set<string>();
  pi.on('session_start',(_event,ctx)=>{this.manager=ctx.sessionManager;});
  for(const [name,config] of Object.entries(this.entries)){
   const namespace=name.replaceAll('-','_');
   try{
    if(name.length>128||namespaces.has(namespace))throw Error('identity');
    pi.registerMcpServer(name,config as McpServerConfig);namespaces.add(namespace);this.owned.add(name);
   }catch{this.errors.push('A managed MCP server could not be registered; check its name and configuration.');}
  }
 };
 factories():ExtensionFactory[]{
  const managed:ExtensionFactory=pi=>{this.autoCodemodeActivated=this.inheritedAutoCodemode;this.inheritedAutoCodemode=false;const builtin=createMcpExtension({
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
  },event=>{
   let retained=false;try{this.api?.appendEntry(MCP_CONNECTION_TYPE,event);retained=!!this.api;}catch{}
   const previous=this.connections.get(event.server);
   if(event.event==='created'||!previous||previous.summary.instanceId===event.instanceId){
    if(!previous&&this.connections.size>=256){this.connections.delete(this.connections.keys().next().value!);this.connectionTrackingDropped++;}
    const same=previous?.summary.instanceId===event.instanceId;this.connections.set(event.server,{summary:connectionSummary(same?previous.summary:undefined,event),unsaved:(same?previous.unsaved:0)+(retained?0:1)});
   }
   this.connectionChanged?.(event,retained);
  },server=>this.calls.current(server)),
  logPath:this.retainLogs?join(privateDir(join(this.stateDir,'mcp-logs')),this.sessionId+'.log'):process.platform==='win32'?'NUL':'/dev/null',
  // The operator surface presents this ephemeral URL. The SDK must not launch
  // an unrelated default browser or place the URL in retained notifications.
  openUrl:url=>{if(!this.openAuthorization)throw Error('Open MCP management to sign in.');this.openAuthorization(url);},
 });
  return builtin(new Proxy(pi,{get:(target,key)=>{
   if(key==='registerTool')return (definition:Parameters<ExtensionAPI['registerTool']>[0])=>target.registerTool(this.calls.wrap(definition));
   if(key==='setActiveTools')return (names:string[])=>{if(names.includes('codemode')&&!target.getActiveTools().includes('codemode'))this.autoCodemodeActivated=true;target.setActiveTools(names);};
   if(key==='registerCommand')return (name:string,options:Omit<RegisteredCommand,'name'|'sourceInfo'>)=>{if(name==='mcp')this.command=options.handler;target.registerCommand(name,options);};
   if(key==='on')return (event:string,handler:(event:any,ctx:ExtensionContext)=>unknown)=>{
    const guarded=async(value:any,ctx:ExtensionContext)=>{
     const ui=new Proxy(ctx.ui,{get:(ui,key)=>key==='notify'?(_message:string,type?:string)=>ui.notify('MCP connection setup reported a problem. Inspect its registration and recorded authorization status; current connection health is unverified.',type==='error'?'error':'warning'):Reflect.get(ui,key)});
     try{return await handler(value,new Proxy(ctx,{get:(context,key)=>key==='ui'?ui:Reflect.get(context,key)}));}
     catch{throw Error('MCP connection setup failed; inspect its registration and recorded authorization status.');}
    };
    target.on(event as 'mcp_servers_change',(event==='mcp_servers_change'||event==='session_start'?guarded:handler) as any);
   };
   return Reflect.get(target,key);
  }}));};
  // SDK event dispatch awaits handlers in factory order. This observer runs
  // after the built-in handler's close/connect work for the matching snapshot;
  // registration return alone is not settlement or connection health.
  const observer:ExtensionFactory=pi=>{pi.on('mcp_servers_change',event=>{const wait=this.registrationWait;if(wait&&this.snapshot(event.servers)===wait.snapshot){this.registrationWait=undefined;wait.finish();}});};
  return [createCodemodeExtension({models:false}),createToolSearchExtension(),this.register,managed,observer];
 }
 private snapshot(servers:ReturnType<ExtensionAPI['getMcpServers']>){return JSON.stringify(servers.map(row=>[row.name,row.config,row.extensionPath]));}
 preflight(profile:McpProfile){
  if(!this.api)throw Error('Load the Native conversation before changing MCP configuration.');
  const other=this.api.getMcpServers().filter(row=>!this.owned.has(row.name));
  if([...profile.servers.keys()].some(name=>other.some(row=>row.name.replaceAll('-','_')===name.replaceAll('-','_'))))throw Error('A configured MCP name conflicts with a server owned by another extension. No profile was saved.');
 }
 assertReady(){if(this.pending)throw Error('MCP configuration has not settled for this conversation. Inspect its configuration receipt before sending a prompt.');}
 takeResultIdentity(toolCallId:string,toolName:string){return this.calls.takeResult(toolCallId,toolName);}
 markPending(){this.pending=true;}
 needsSessionReload(profile:McpProfile){return this.reloadPending||profile.autoEnableCodemode!==this.autoEnableCodemode||profile.retainLogs!==this.retainLogs;}
 prepareSessionReload(profile:McpProfile){
  const removeAutoCodemode=this.autoCodemodeActivated&&!profile.autoEnableCodemode;
  this.inheritedAutoCodemode=this.autoCodemodeActivated&&profile.autoEnableCodemode;
  this.reloadPending=true;this.entries=profile.document.mcpServers as Record<string,unknown>;this.readTools=new Set(profile.readTools);
  this.autoEnableCodemode=profile.autoEnableCodemode;this.retainLogs=profile.retainLogs;this.requestedOptions=undefined;this.errors=[];this.owned.clear();
  return {removeAutoCodemode};
 }
 finishSessionReload(revision:string){this.reloadPending=false;this.pending=false;this.revision=revision;}
 async apply(profile:McpProfile,revision:string){
  this.preflight(profile);const api=this.api!;
  const change=(mutate:()=>void)=>new Promise<void>((resolve,reject)=>{
   // Install before the synchronous registration emits its asynchronous event.
   const wait={snapshot:'',finish:resolve};this.registrationWait=wait;
   try{mutate();wait.snapshot=this.snapshot(api.getMcpServers());}catch{if(this.registrationWait===wait)this.registrationWait=undefined;reject(Error('An MCP registration could not be changed. The saved profile may be ahead of this conversation.'));}
  });
  for(const name of [...this.owned])if(!profile.servers.has(name)){await change(()=>api.unregisterMcpServer(name));this.owned.delete(name);}
  for(const [name,config] of profile.servers){
   const current=api.getMcpServers().find(row=>row.name===name);
   if(!current||JSON.stringify(current.config)!==JSON.stringify(config)){await change(()=>api.registerMcpServer(name,config));this.owned.add(name);}
  }
  this.readTools=new Set(profile.readTools);this.entries=profile.document.mcpServers as Record<string,unknown>;this.errors=[];this.revision=revision;this.pending=false;
  this.requestedOptions={autoEnableCodemode:profile.autoEnableCodemode,retainLogs:profile.retainLogs};
 }
 managementCommand(action:McpManagementAction,name:string){
  this.assertReady();
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
  // Public reload invalidates the old API before constructing the new runner.
  // Inspection during that interval must not claim a live catalog or throw
  // through a captured stale context.
  let catalog:undefined|{tools:ReturnType<ExtensionAPI['getAllTools']>;active:string[];servers:ReturnType<ExtensionAPI['getMcpServers']>};
  try{if(this.api)catalog={tools:this.api.getAllTools(),active:this.api.getActiveTools(),servers:this.api.getMcpServers()};}catch{}
  const tools=catalog?.tools??[],active=new Set(catalog?.active??[]),servers=catalog?.servers??[];let remaining=256;
  const authorization=new Map<string,McpAuthorizationObservation>();
  const history=new Map<string,McpConnectionSummary>(),visible=new Set(servers.slice(0,64).map(row=>row.name));
  for(const entry of this.manager?.getBranch()??[])if(entry.type==='custom'&&entry.customType===MCP_AUTHORIZATION_TYPE){const row=savedMcpAuthorization(entry.data);if(row)authorization.set(row.server,row);}
  for(const entry of this.manager?.getBranch()??[])if(entry.type==='custom'&&entry.customType===MCP_CONNECTION_TYPE){const row=savedMcpConnection(entry.data);if(!row||!visible.has(row.server))continue;const previous=history.get(row.server);if(row.event==='created'||!previous||previous.instanceId===row.instanceId)history.set(row.server,connectionSummary(previous?.instanceId===row.instanceId?previous:undefined,row));}
  return {available:!!catalog,source:'managed-profile-mcp.json',projectConfiguration:false,modelsInCodemode:false,retainServerLogs:this.retainLogs,configurationErrors:this.errors.length,
   configuration:{loadedRevision:this.revision,registrationPending:this.pending,pendingSessionOptions:this.reloadPending||(this.requestedOptions?this.requestedOptions.autoEnableCodemode!==this.autoEnableCodemode||this.requestedOptions.retainLogs!==this.retainLogs:false),optionApplication:'changed log retention and automatic codemode options use an idle public session reload; connection health is separate'},
   activeDiscoveryTools:[...discovery].filter(name=>active.has(name)),callCorrelation:this.calls.describe(),
   coverage:'registered MCP tool catalog and public transport observations; no health probe or private SDK connection state',connectionTrackingDropped:this.connectionTrackingDropped,serverCount:servers.length,omittedServers:Math.max(0,servers.length-64),servers:servers.slice(0,64).map(entry=>{
    const namespace='mcp__'+entry.name.replaceAll('-','_'),registered=tools.filter(tool=>tool.namespace?.name===namespace),shown=registered.filter(tool=>tool.name.length<=256).slice(0,remaining);remaining-=shown.length;
    const lastObserved=authorization.get(entry.name)??null,gap=this.authorizationGaps.get(entry.name);
    const connection=this.connections.get(entry.name);
    return {name:entry.name,enabled:entry.config.enabled!==false,transport:'url' in entry.config?'http':'stdio',exposure:entry.config.exposure??'codemode',managementActions:this.managementActions(entry.config),toolCount:registered.length,omittedToolNames:registered.length-shown.length,toolNames:shown.map(tool=>tool.name),declaredToolNames:shown.filter(tool=>active.has(tool.name)).map(tool=>tool.name),readOnlyToolNames:shown.filter(tool=>this.readTools.has(tool.name)).map(tool=>tool.name),connection:{coverage:'observed public transport lifecycle; no active service or credential probe',current:connection?.summary??null,unsavedObservations:connection?.unsaved??0,lastSaved:history.get(entry.name)??null,retention:connection?.unsaved?'native-append-gap':'sdk-native-entry-policy'},authorization:{coverage:'last recorded HTTP authorization observation on the selected Pi branch; not current credential health',lastObserved,unsaved:gap??null,retention:gap?'native-append-failed':lastObserved?'sdk-native-entry-policy':'not-observed'}};
   })};
 }
}
