// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {InputMode} from '../../prompt-library/src/input-mode.js';
import {createHash} from 'node:crypto';
import type {SessionEntry} from '@earendil-works/pi-coding-agent';
import {systemTextPresence} from '../../observation/src/provider-system.js';
import {CONTEXT_LIMIT} from './context.js';

export const PI_MEMORY_SNAPSHOT_TYPE='augmentor.memory-context.v1';
export type PiMemoryDisposition='present'|'empty'|'not-present'|'unavailable';
export interface PiMemorySnapshot {version:1;sourceSession:string;mode:InputMode;boundary:'provider-system-payload-after-hooks';disposition:PiMemoryDisposition;context:string;sha256:string}
const hash=(text:string)=>createHash('sha256').update(text).digest('hex');
const fields=['boundary','context','disposition','mode','sha256','sourceSession','version'];
function valid(value:unknown):value is PiMemorySnapshot {
 if(!value||typeof value!=='object'||Array.isArray(value))return false;
 const row=value as PiMemorySnapshot;
 return Object.keys(row).sort().join(',')===fields.join(',')&&row.version===1&&(row.mode==='text'||row.mode==='voice')&&row.boundary==='provider-system-payload-after-hooks'&&
  typeof row.sourceSession==='string'&&row.sourceSession.length>0&&row.sourceSession.length<=512&&typeof row.context==='string'&&row.context.length<=CONTEXT_LIMIT&&
  ['present','empty','not-present','unavailable'].includes(row.disposition)&&(row.disposition==='present'?row.context.length>0:row.context.length===0)&&
  typeof row.sha256==='string'&&row.sha256===hash(row.context);
}
/** Native conversation state, separate from optional diagnostic payload capture. */
export function piMemorySnapshot(sourceSession:string,context:string,disposition:PiMemoryDisposition=context?'present':'empty',mode:InputMode='text'):PiMemorySnapshot {
 const value:PiMemorySnapshot={version:1,sourceSession,mode,boundary:'provider-system-payload-after-hooks',disposition,context,sha256:hash(context)};
 if(!valid(value))throw Error('Managed memory is outside the native snapshot contract.');
 return value;
}
/** Only the selected native ancestry is eligible. Never fall back past a damaged
 * latest record or an explicitly empty brief to a different historical context.
 */
export function readPiMemorySnapshot(entries:readonly SessionEntry[]):
 {state:'retained';entryId:string;value:PiMemorySnapshot}|{state:'missing'|'invalid'|'unavailable'} {
 const entry=entries.findLast(row=>row.type==='custom'&&row.customType===PI_MEMORY_SNAPSHOT_TYPE);
 if(!entry)return {state:'missing'};
 if(entry.type!=='custom'||!valid(entry.data))return {state:'invalid'};
 if(!['present','empty'].includes(entry.data.disposition))return {state:'unavailable'};
 return {state:'retained',entryId:entry.id,value:structuredClone(entry.data)};
}

/** Shared strict provider-system recognizer; diagnostic text matching uses the same API shapes. */
export function providerMemoryDisposition(payload:unknown,context:string,api?:string):PiMemoryDisposition {return systemTextPresence(payload,context,api);}
