// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync,statSync} from 'node:fs';
import {atomicJson,readJson} from './storage.js';
import {identifier} from '../../protocol/src/index.js';

type Record={schema:'augmentor-session-organization/1';revision:number;pinnedSessionIds:string[];archivedSessionIds:string[]};
function validate(value:Record){
  if(!value||value.schema!=='augmentor-session-organization/1'||!Number.isSafeInteger(value.revision)||value.revision<0)throw Error('Invalid session organization record. Preserve it for recovery.');
  for(const values of [value.pinnedSessionIds,value.archivedSessionIds]){if(!Array.isArray(values)||values.length>5000||new Set(values).size!==values.length)throw Error('Invalid session organization set.');for(const id of values)identifier(id);}
  if(value.pinnedSessionIds.some(id=>value.archivedSessionIds.includes(id)))throw Error('An archived conversation cannot be pinned.');
  if(Buffer.byteLength(JSON.stringify(value),'utf8')>2*1024*1024)throw Error('Session organization exceeds its size bound. Preserve it for recovery.');return value;
}
/** Presentation membership only: never deletes a conversation, log or file. */
export class SessionOrganization {
  private data:Record;
  constructor(private file:string){if(existsSync(file)&&statSync(file).size>2*1024*1024)throw Error('Session organization exceeds its size bound. Preserve it for recovery.');this.data=validate(readJson(file,{schema:'augmentor-session-organization/1',revision:0,pinnedSessionIds:[],archivedSessionIds:[]}));}
  snapshot(){return structuredClone(this.data);}
  archived(id:string){return this.data.archivedSessionIds.includes(id);}
  check(revision:unknown){if(revision!==this.data.revision)throw Error('Conversation organization changed. Refresh and review before trying again.');}
  mutate(action:unknown,id:unknown,revision:unknown){
    this.check(revision);const sid=identifier(id),next=this.snapshot();
    if(action==='pin'){if(this.archived(sid))throw Error('Restore the conversation before pinning it.');next.pinnedSessionIds=[sid,...next.pinnedSessionIds.filter(x=>x!==sid)];}
    else if(action==='unpin')next.pinnedSessionIds=next.pinnedSessionIds.filter(x=>x!==sid);
    else if(action==='archive'){next.pinnedSessionIds=next.pinnedSessionIds.filter(x=>x!==sid);if(!next.archivedSessionIds.includes(sid))next.archivedSessionIds.push(sid);}
    else if(action==='restore')next.archivedSessionIds=next.archivedSessionIds.filter(x=>x!==sid);
    else throw Error('Choose a supported conversation organization action.');
    if(JSON.stringify(next)===JSON.stringify(this.data))return this.snapshot();
    next.revision++;validate(next);atomicJson(this.file,next);this.data=next;return this.snapshot();
  }
}
