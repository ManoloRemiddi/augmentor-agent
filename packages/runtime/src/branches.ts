// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {SessionManager,CURRENT_SESSION_VERSION} from '@earendil-works/pi-coding-agent';
import {constants,openSync,closeSync,readSync,fstatSync,lstatSync,existsSync,writeFileSync,fsyncSync} from 'node:fs';
import {type DisplayEvent} from '../../protocol/src/index.js';
import {identifier} from '../../protocol/src/index.js';
import {GOAL_ROUND_TYPE,goalUserHash,goalProjection} from './goals.js';

const messageText=(content:any):string=>typeof content==='string'?content:(content??[]).filter((p:any)=>p.type==='text').map((p:any)=>p.text).join('\n');

export function inspectBranchContext(file:string, directory:string, events:DisplayEvent[], seq:number, mode:'reply'|'edit') {
  const target=events.find(e=>e.seq===seq);
  const type=mode==='edit'?'user/message':'assistant/message';
  if(!target||target.type!==type)throw new Error('Choose a message from this conversation.');
  if(mode==='edit'&&events.filter(e=>e.type==='user/message').at(-1)?.seq!==seq)throw new Error('Only the latest user message can be edited. Reload the conversation.');
  // createBranchedSession changes its manager's active file. Use a separate
  // manager so the source conversation's live agent and leaf remain untouched.
  // SDK open migrates old native headers in place. Preparation is read-only:
  // unsupported source formats need a separately reviewed migration instead.
  const fd=openSync(file,constants.O_RDONLY|(constants.O_NOFOLLOW??0)|(constants.O_NONBLOCK??0));
  try{
    if(!fstatSync(fd).isFile())throw Error('The native branch source is not a regular file; originals were preserved.');
    const buffer=Buffer.alloc(64*1024),bytes=readSync(fd,buffer,0,buffer.length,0),end=buffer.subarray(0,bytes).indexOf(10);let header;
    try{header=JSON.parse(buffer.subarray(0,end<0?bytes:end).toString('utf8'));}catch{throw Error('The native branch header is unavailable; originals were preserved.');}
    if(header?.type!=='session'||header.version!==CURRENT_SESSION_VERSION)throw Error('This native session format needs a reviewed migration before branching; originals were preserved.');
  }finally{closeSync(fd);}
  const manager=SessionManager.open(file,directory);
  const role=mode==='edit'?'user':'assistant';
  const ordinal=events.filter(e=>e.type===type&&e.seq<=seq).length-1;
  const entry=manager.getBranch().filter(e=>e.type==='message'&&e.message.role===role)[ordinal];
  const content=mode==='edit'?target.data.content:target.data.message?.content;
  if(!entry||entry.type!=='message'||messageText((entry.message as any).content)!==messageText(content))throw new Error('Cannot locate this message in Pi history. Reload the conversation.');
  if(mode==='reply'&&entry.message.role==='assistant'&&entry.message.content.some(p=>p.type==='toolCall'))throw new Error('Choose the reply after the tools have finished.');
  let leaf=mode==='edit'?entry.parentId:entry.id;
  if(mode==='edit'&&target.data.source?.kind==='goal'){
    const ancestors=manager.getBranch(entry.id);goalProjection(ancestors);
    const admission=ancestors.findLast(e=>e.type==='custom'&&e.customType===GOAL_ROUND_TYPE&&(e.data as any)?.requestId===target.data.source.rpcId&&(e.data as any)?.userHash===goalUserHash(entry.message));
    if(!admission)throw Error('Cannot locate this goal input admission in Pi history.');
    // Editing excludes the removed input's admission too; retaining it would
    // falsely attribute the replacement user message to the old goal round.
    leaf=admission.parentId;
  }
  let cutoff=seq;
  if(mode==='edit'){
    const start=events.findLast(e=>e.seq<seq&&e.type==='turn/start')?.seq??seq;
    // A steered correction shares the host turn with earlier native messages.
    // Its parent includes those messages; only an initial input cuts at start.
    cutoff=events.some(e=>e.type==='user/message'&&e.seq>start&&e.seq<seq)?seq:start;
  }
  const inherited=events.filter(e=>mode==='edit'?e.seq<cutoff:e.seq<=cutoff);
  return {manager,leaf,events:inherited};
}

export function branchContext(file:string,directory:string,events:DisplayEvent[],seq:number,mode:'reply'|'edit'){
  const info=lstatSync(directory);
  if(!info.isDirectory()||info.isSymbolicLink()||process.platform!=='win32'&&(info.uid!==process.getuid!()||(info.mode&0o077)!==0))throw Error('Use the private branch directory; originals were preserved.');
  const plan=inspectBranchContext(file,directory,events,seq,mode);
  const fileName=plan.leaf?plan.manager.createBranchedSession(plan.leaf):undefined;
  let manager=plan.leaf?plan.manager:undefined;
  if(manager&&fileName&&!existsSync(fileName)){
    // The SDK defers a custom-only branch until its first conversation message.
    // Persist its exact public header/entries without inventing a message or
    // loading extensions/an AgentSession just to force a file into existence.
    const header=manager.getHeader();if(!header||header.version!==CURRENT_SESSION_VERSION)throw Error('The native branch header is unavailable; originals were preserved.');
    const fd=openSync(fileName,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|(constants.O_NOFOLLOW??0),0o600);
    try{for(const entry of [header,...manager.getEntries()])writeFileSync(fd,JSON.stringify(entry)+'\n');fsyncSync(fd);}finally{closeSync(fd);}
    if(process.platform!=='win32'){
      const fd=openSync(directory,constants.O_RDONLY|(constants.O_DIRECTORY??0)|(constants.O_NOFOLLOW??0));try{fsyncSync(fd);}finally{closeSync(fd);}
    }
    // A fresh supported manager recognizes the existing file and appends once;
    // the original deferred manager must not later try to create it with "wx".
    manager=SessionManager.open(fileName,directory);
  }
  return {manager,file:fileName,events:plan.events};
}

/** Public SDK projection prepared in memory before filesystem publication. */
export function branchPublicationContext(file:string,events:DisplayEvent[],seq:number,mode:'reply'|'edit'){
  const plan=inspectBranchContext(file,'',events,seq,mode);
  if(!plan.leaf)return {events:plan.events};
  const manager=SessionManager.inMemory(plan.manager.getCwd(),undefined,[plan.manager.getHeader()!,...plan.manager.getEntries()]);
  manager.createBranchedSession(plan.leaf);
  const header=manager.getHeader();if(!header||header.version!==CURRENT_SESSION_VERSION)throw Error('The projected branch header is unavailable.');
  const name=identifier(header.id)+'.jsonl';
  // parentSession is a documented native header field. The in-memory SDK has
  // no source filename; retain the same original-file lineage as persisted SDK branching.
  const native=[{...header,parentSession:file},...manager.getEntries()].map(row=>JSON.stringify(row)+'\n').join('');
  return {events:plan.events,native,name};
}
