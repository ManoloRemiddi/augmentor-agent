// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import type {JsonRpcId} from '@earendil-works/pi-mcp';
import {savedMcpAgentCall,type McpAgentCall} from './mcp-call-context.js';

export const MCP_TRANSPORT_ORIGINAL_TYPE='augmentor-mcp-transport/1';
export const MCP_BODY_MAX_BYTES=1024*1024;
export interface McpFailureOriginal {
 server:string;requestId:JsonRpcId;method:'tools/call';params:unknown;status:number;contentType:string|null;
 agentCall?:McpAgentCall;
 body:{coverage:'complete'|'partial'|'unavailable';reason?:string;retainedBytes:number;prefixSha256:string;text:string;base64:string};
}

/** Persisted entries are evidence. Admit only the recorded bounded byte prefix,
 * with matching length, digest and decoded text; never infer an agent call ID.
 */
export function savedMcpFailureOriginal(data:unknown):McpFailureOriginal|undefined{
 if(!data||typeof data!=='object')return;
 const record=data as McpFailureOriginal,body=record.body;
 if(typeof record.server!=='string'||!record.server||record.server.length>128||record.method!=='tools/call'||
  !(typeof record.requestId==='string'||(typeof record.requestId==='number'&&Number.isFinite(record.requestId)))||
  !Number.isInteger(record.status)||record.status<100||record.status>599||!(record.contentType===null||typeof record.contentType==='string')||
  !body||typeof body!=='object'||!['complete','partial','unavailable'].includes(body.coverage)||
  !Number.isSafeInteger(body.retainedBytes)||body.retainedBytes<0||body.retainedBytes>MCP_BODY_MAX_BYTES||
  typeof body.text!=='string'||body.text.length>MCP_BODY_MAX_BYTES||typeof body.base64!=='string'||body.base64.length>Math.ceil(MCP_BODY_MAX_BYTES/3)*4||
  typeof body.prefixSha256!=='string'||!/^[a-f0-9]{64}$/.test(body.prefixSha256)||
  (body.reason!==undefined&&typeof body.reason!=='string')||(body.coverage!=='complete'&&!body.reason)||
  (body.coverage==='unavailable'&&body.retainedBytes!==0))return;
 const bytes=Buffer.from(body.base64,'base64');
 if(bytes.length!==body.retainedBytes||bytes.toString('base64')!==body.base64||bytes.toString('utf8')!==body.text||createHash('sha256').update(bytes).digest('hex')!==body.prefixSha256)return;
 const agentCall=record.agentCall===undefined?undefined:savedMcpAgentCall(record.agentCall);if(record.agentCall!==undefined&&(!agentCall||!agentCall.toolName.startsWith('mcp__'+record.server.replaceAll('-','_')+'__')))return;
 return {...record,...(agentCall?{agentCall}:{})};
}
