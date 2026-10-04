// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import type {promptCall} from '../../prompt-library/src/client.js';

export interface WorkspaceIdentity {id:string; preset:string; cwd:string; connection:string}
export interface ApplicationTool {name:string; description:string; inputSchema:Record<string,unknown>}
export interface WorkspaceBinding {
 identity:WorkspaceIdentity; instructions:string; tools:ApplicationTool[]; grants:string[];
 execute:(name:string,args:unknown,execution:{sessionId:string;callId:string;signal:AbortSignal})=>Promise<unknown>;
 memoryCall:(call:typeof promptCall)=>typeof promptCall;
}

/** The registry, policy and memory binding stay owned by the product's existing workspace service. */
export class CodexWorkspaces {
 async load(id:string,expected?:WorkspaceIdentity):Promise<WorkspaceBinding>{
  const {loadProfile}=await import(new URL('../../../services/workspaces/profiles.mjs',import.meta.url).href);
  const {validatePolicy}=await import(new URL('../../../services/workspaces/policy.mjs',import.meta.url).href);
  const {profileMemoryCall}=await import(new URL('../../../services/workspaces/memory.mjs',import.meta.url).href);
  const profile=loadProfile(id);validatePolicy(profile);
  if(profile.harness!=='codex'||typeof profile.connection!=='string')throw Error('This workspace does not have an explicit Codex connection');
  const identity={id:profile.id,preset:profile.preset,cwd:profile.cwd,connection:profile.connection};
  if(expected&&Object.keys(identity).some(key=>identity[key as keyof WorkspaceIdentity]!==expected[key as keyof WorkspaceIdentity]))throw Error('Codex application workspace identity changed; the conversation was not resumed');
  const instructions=(profile.instructions as string[]).map(path=>readFileSync(path,'utf8')).join('\n\n');
  if(!instructions.trim()||Buffer.byteLength(instructions)>32768)throw Error('Application instructions are missing or exceed 32 KiB');
  const tools:ApplicationTool[]=[],executors=new Map<string,WorkspaceBinding['execute']>();
  for(const plugin of profile.tools??[]){
   if(!Array.isArray(plugin.names)||plugin.names.length===0)throw Error('Codex application plugins require explicit declared tool names');
   const digest=createHash('sha256').update(readFileSync(plugin.module)).digest('hex');
   const module=await import(pathToFileURL(plugin.module).href+'?v='+digest);
   if(typeof module.applicationTools!=='function')throw Error('This plugin requires the harness-neutral applicationTools SDK export');
   const application=await module.applicationTools(plugin.config??{});
   if(!Array.isArray(application?.tools)||typeof application.execute!=='function')throw Error('Invalid application tool adapter');
   const names=application.tools.map((tool:ApplicationTool)=>tool.name);
   if(names.length!==plugin.names.length||plugin.names.some((name:string)=>!names.includes(name)))throw Error('Application plugin tools differ from its installed declaration');
   for(const tool of application.tools as ApplicationTool[]){
    if(!/^[A-Za-z][A-Za-z0-9_]{0,127}$/.test(tool.name)||executors.has(tool.name)||!tool.inputSchema||typeof tool.inputSchema!=='object'||Array.isArray(tool.inputSchema)||typeof tool.description!=='string'||Buffer.byteLength(tool.description)>32768)throw Error('Invalid or duplicate application tool');
    if(['request_user_input','get_goal','create_goal','update_goal'].includes(tool.name))throw Error('Application tool name is reserved by the harness');
    executors.set(tool.name,application.execute.bind(application));
    if(profile.policy.tools.includes(tool.name))tools.push(tool);
   }
  }
  return {identity,instructions,tools,grants:profile.policy.tools,
   execute:async(name,args,execution)=>{
    // Read the registry again at dispatch: a conversation snapshot never restores a revoked grant.
    const live=loadProfile(id);validatePolicy(live);
    if(live.harness!=='codex'||live.preset!==identity.preset||live.cwd!==identity.cwd||live.connection!==identity.connection||!live.policy.tools.includes(name))throw Error('Application tool grant or workspace identity was revoked');
    const execute=executors.get(name);if(!execute)throw Error('Application tool is unavailable');
    execution.signal.throwIfAborted();return execute(name,args,execution);
   },memoryCall:call=>profileMemoryCall(profile,call)};
 }
 async guard(identity:WorkspaceIdentity,name:string):Promise<void>{
  const {loadProfile}=await import(new URL('../../../services/workspaces/profiles.mjs',import.meta.url).href);
  const {validatePolicy}=await import(new URL('../../../services/workspaces/policy.mjs',import.meta.url).href);
  const p=loadProfile(identity.id);validatePolicy(p);
  if(p.harness!=='codex'||p.preset!==identity.preset||p.cwd!==identity.cwd||p.connection!==identity.connection||!p.policy.tools.includes(name))throw Error('This tool is not granted to the application workspace');
 }
}

/** Keep native tools out of app workers; request_user_input remains an owner interaction. */
export function restrictWorkspaceRuntime<T extends {args:string[]}>(options:T):T {
 const args=[...options.args];
 for(const name of ['shell_tool','unified_exec','view_image','image_generation','multi_agent','skill_search','sleep_tool','tool_suggest','goals','default_mode_request_user_input'])args.push('-c',`features.${name}=false`);
 args.push('-c','web_search="disabled"','-c','sandbox_mode="read-only"');
 return {...options,args};
}
