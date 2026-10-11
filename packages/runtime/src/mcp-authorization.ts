// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {JsonRpcId} from '@earendil-works/pi-mcp';
export const MCP_AUTHORIZATION_TYPE='augmentor-mcp-authorization/1';
export interface McpAuthorizationObservation {
 server:string;requestId?:JsonRpcId;status:401|403;
 boundary:'http-tool-response'|'http-request-response'|'http-get-response'|'http-control-response';
 state:'challenge-observed'|'sign-in-required'|'refresh-failed'|'challenge-handled';observedAt:string;
}
/** Private native metadata is historical evidence, not current credential health. */
export function savedMcpAuthorization(value:unknown):McpAuthorizationObservation|undefined{
 if(!value||typeof value!=='object')return;
 const row=value as McpAuthorizationObservation;
 if(typeof row.server!=='string'||!row.server||row.server.length>128||![401,403].includes(row.status)||
  !['http-tool-response','http-request-response','http-get-response','http-control-response'].includes(row.boundary)||
  !['challenge-observed','sign-in-required','refresh-failed','challenge-handled'].includes(row.state)||
  typeof row.observedAt!=='string'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(row.observedAt)||!Number.isFinite(Date.parse(row.observedAt))||
  !(row.requestId===undefined||(typeof row.requestId==='string'&&row.requestId.length<=256)||(typeof row.requestId==='number'&&Number.isSafeInteger(row.requestId))))return;
 if(new Date(row.observedAt).toISOString()!==row.observedAt)return;
 return {server:row.server,status:row.status,boundary:row.boundary,state:row.state,observedAt:row.observedAt,...(row.requestId===undefined?{}:{requestId:row.requestId})};
}
