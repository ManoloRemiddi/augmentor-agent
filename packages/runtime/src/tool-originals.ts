// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {SessionManager,ToolResultEvent} from '@earendil-works/pi-coding-agent';
import type {ToolResultMessage} from '@earendil-works/pi-ai';

export const TOOL_ORIGINAL_TYPE='augmentor-tool-original/1';
// Leave room for the SDK's entry envelope under the native index's 64 MiB limit.
export const TOOL_ORIGINAL_MAX_BYTES=63*1024*1024;
type OriginalEvent=Pick<ToolResultEvent,'toolName'|'toolCallId'|'content'|'details'|'structuredContent'|'usage'|'isError'|'parentToolCallId'>&{input:unknown};
type SavedToolOriginal={schema:typeof TOOL_ORIGINAL_TYPE;toolName:string;toolCallId:string;parentToolCallId?:string;
 boundary:'sdk-nested-result-before-result-hooks'|'sdk-root-result-before-result-hooks';coverage:'saved'|'oversize'|'non-json';maxBytes:number;
 input?:unknown;result?:{content:ToolResultMessage['content'];details?:unknown;structuredContent?:ToolResultEvent['structuredContent'];usage?:ToolResultEvent['usage'];isError:boolean}};

/** Durable branch evidence, not a message or a model-context contribution.
 * Snapshot before result handlers can mutate the object retained by the SDK.
 */
export function saveToolOriginal(manager:Pick<SessionManager,'appendCustomEntry'>,event:OriginalEvent){
 if(!event.parentToolCallId&&!event.toolName.startsWith('mcp__'))return;
 const identity={schema:TOOL_ORIGINAL_TYPE as typeof TOOL_ORIGINAL_TYPE,toolName:event.toolName,toolCallId:event.toolCallId,parentToolCallId:event.parentToolCallId,
  boundary:event.parentToolCallId?'sdk-nested-result-before-result-hooks' as const:'sdk-root-result-before-result-hooks' as const,maxBytes:TOOL_ORIGINAL_MAX_BYTES};
 let data:SavedToolOriginal;
 try{
  const serialized=JSON.stringify({...identity,coverage:'saved',input:event.input,result:{content:event.content,details:event.details,structuredContent:event.structuredContent,usage:event.usage,isError:event.isError}});
  data=Buffer.byteLength(serialized)>TOOL_ORIGINAL_MAX_BYTES?{...identity,coverage:'oversize'}:JSON.parse(serialized);
 }catch{data={...identity,coverage:'non-json'};}
 const entryId=manager.appendCustomEntry(TOOL_ORIGINAL_TYPE,data);
 return {entryId,toolName:event.toolName,toolCallId:event.toolCallId,parentToolCallId:event.parentToolCallId,coverage:data.coverage,boundary:data.boundary,maxBytes:data.maxBytes};
}

export function savedToolOriginal(data:unknown):SavedToolOriginal|undefined{
 if(!data||typeof data!=='object')return;
 const record=data as SavedToolOriginal;
 if(record.schema!==TOOL_ORIGINAL_TYPE||typeof record.toolName!=='string'||typeof record.toolCallId!=='string'||(record.parentToolCallId!==undefined&&typeof record.parentToolCallId!=='string')||!['sdk-nested-result-before-result-hooks','sdk-root-result-before-result-hooks'].includes(record.boundary)||!['saved','oversize','non-json'].includes(record.coverage))return;
 if(record.coverage==='saved'&&(!record.result||typeof record.result.isError!=='boolean'||!Array.isArray(record.result.content)||record.result.content.some(part=>!part||typeof part!=='object'||!['text','image'].includes(part.type)||(part.type==='text'&&typeof part.text!=='string'))))return;
 return record;
}
