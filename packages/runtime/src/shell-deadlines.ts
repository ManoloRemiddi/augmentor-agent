// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';

export const DEFAULT_FOREGROUND_SHELL_SECONDS=120;
export function foregroundShellSeconds(env:NodeJS.ProcessEnv=process.env){
 const value=env.AUGMENTOR_FOREGROUND_SHELL_SECONDS;
 if(value===undefined)return DEFAULT_FOREGROUND_SHELL_SECONDS;
 const seconds=Number(value);
 if(!Number.isFinite(seconds)||seconds<0||seconds>2147483)return DEFAULT_FOREGROUND_SHELL_SECONDS;
 return seconds;
}
export const SHELL_DEADLINE_GUIDANCE='Foreground shell calls without an explicit timeout use the configured foreground deadline (normally 120 seconds). Supply an explicit timeout for known longer work, or use the existing bounded shell jobs. A timeout stops the command and its descendants; partial side effects remain. Inspect the outcome before any retry. Use the supported artifact opener for generated files instead of waiting for a GUI program to exit.';

/** The supported SDK hook also covers tool calls nested inside codemode. */
export function piShellDeadlines(seconds=foregroundShellSeconds()){return(pi:ExtensionAPI)=>{
 pi.on('tool_call',event=>{
  const input=event.input as Record<string,unknown>;
  if(seconds>0&&['bash','powershell'].includes(event.toolName)&&input.timeout===undefined)input.timeout=seconds;
 });
 pi.on('tool_result',event=>{
  if(!['bash','powershell'].includes(event.toolName)||!event.isError)return;
  if(!event.content.some(part=>part.type==='text'&&/Command timed out after/.test(part.text)))return;
  return {content:[...event.content,{type:'text' as const,text:'The foreground command was stopped at its deadline. Partial output and side effects may remain; this is not a rollback. Inspect the result before continuing. For future long work, choose an explicit timeout or the existing shell job tools. No action was replayed.'}],...(event.structuredContent===undefined?{}:{structuredContent:event.structuredContent})};
 });
};}
