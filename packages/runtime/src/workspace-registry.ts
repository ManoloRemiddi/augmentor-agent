// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {stat} from 'node:fs/promises';
import {existsSync,statSync} from 'node:fs';
import {basename,isAbsolute,resolve} from 'node:path';
import {atomicJson,readJson} from './storage.js';
import {text} from '../../protocol/src/index.js';

type Workspace={workspaceId:string;cwd:string;title:string};
type Registry={schema:'augmentor-workspaces/1';revision:number;items:Workspace[];removed:string[]};
const empty=():Registry=>({schema:'augmentor-workspaces/1',revision:0,items:[],removed:[]});
export const workspacePath=(value:unknown)=>{const path=text(value,4096);if(!isAbsolute(path)||path.includes('\0'))throw Error('Choose an absolute workspace folder.');return resolve(path);};
const pathOf=workspacePath;
const titleOf=(value:unknown)=>text(value,200).trim();
const nameKey=(value:string)=>value.normalize('NFKC').toLowerCase();
function validate(value:Registry){
  if(value.schema!=='augmentor-workspaces/1'||!Number.isSafeInteger(value.revision)||value.revision<0||!Array.isArray(value.items)||!Array.isArray(value.removed)||value.items.length>1000||value.removed.length>2000||Buffer.byteLength(JSON.stringify(value))>2*1024*1024)throw Error('Invalid workspace registry. Preserve it for recovery.');
  const paths=new Set<string>();
  for(const item of value.items){if(pathOf(item.cwd)!==item.cwd||item.workspaceId!==item.cwd||!titleOf(item.title)||paths.has(item.cwd))throw Error('Invalid workspace registration. Preserve it for recovery.');paths.add(item.cwd);}
  const removed=new Set<string>();for(const path of value.removed){if(pathOf(path)!==path||paths.has(path)||removed.has(path))throw Error('Invalid removed workspace registration.');removed.add(path);}
  return value;
}

/** Operator-owned presentation metadata. Never moves/deletes directories or session logs. */
export class WorkspaceRegistry {
  private data:Registry;
  constructor(private file:string,private legacyPaths:()=>string[]){if(existsSync(file)&&statSync(file).size>2*1024*1024)throw Error('Workspace registry exceeds its size bound. Preserve it for recovery.');this.data=validate(readJson(file,empty()));}
  snapshot(){
    const data=structuredClone(this.data),known=new Set([...data.items.map(x=>x.cwd),...data.removed]);
    for(const value of this.legacyPaths()){const cwd=pathOf(value);if(!known.has(cwd)){data.items.push({workspaceId:cwd,cwd,title:basename(cwd)||cwd});known.add(cwd);}}
    return validate(data);
  }
  private before(revision:unknown){if(revision!==this.data.revision)throw Error('Workspaces changed. Refresh and review before trying again.');return this.snapshot();}
  private commit(data:Registry){data.revision=this.data.revision+1;validate(data);atomicJson(this.file,data);this.data=data;return this.snapshot();}
  async adopt(path:unknown,revision:unknown){
    const cwd=pathOf(path);if(!(await stat(cwd)).isDirectory())throw Error('Choose an existing workspace folder.');
    const next=this.before(revision);const row=next.items.find(x=>x.cwd===cwd);
    if(row&&this.data.items.some(x=>x.cwd===cwd))return next;
    if(!row)next.items.push({workspaceId:cwd,cwd,title:basename(cwd)||cwd});next.removed=next.removed.filter(x=>x!==cwd);return this.commit(next);
  }
  rename(workspaceId:unknown,title:unknown,revision:unknown){
    const cwd=pathOf(workspaceId),name=titleOf(title),next=this.before(revision),row=next.items.find(x=>x.cwd===cwd);
    if(!row)throw Error('This workspace is no longer registered.');if(!name)throw Error('Supply a workspace name.');
    if(row.title===name)return next;
    if(next.items.some(x=>x.cwd!==cwd&&nameKey(x.title)===nameKey(name)))throw Error('Another workspace already has that name.');
    row.title=name;return this.commit(next);
  }
  remove(workspaceId:unknown,revision:unknown){
    const cwd=pathOf(workspaceId),next=this.before(revision);if(next.removed.includes(cwd))return next;
    if(!next.items.some(x=>x.cwd===cwd))throw Error('This workspace is no longer registered.');
    next.items=next.items.filter(x=>x.cwd!==cwd);next.removed.push(cwd);return this.commit(next);
  }
  move(workspaceId:unknown,beforeWorkspaceId:unknown,revision:unknown){
    const cwd=pathOf(workspaceId),anchor=beforeWorkspaceId===undefined?undefined:pathOf(beforeWorkspaceId),next=this.before(revision),row=next.items.find(x=>x.cwd===cwd);
    if(!row||anchor!==undefined&&!next.items.some(x=>x.cwd===anchor))throw Error('This workspace is no longer registered.');
    if(cwd===anchor)return next;
    next.items=next.items.filter(x=>x.cwd!==cwd);const index=anchor===undefined?next.items.length:next.items.findIndex(x=>x.cwd===anchor);next.items.splice(index,0,row);return this.commit(next);
  }
}
