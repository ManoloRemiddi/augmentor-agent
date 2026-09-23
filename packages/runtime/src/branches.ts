// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {SessionManager} from '@earendil-works/pi-coding-agent';
import {type DisplayEvent} from '../../protocol/src/index.js';

const messageText=(content:any):string=>typeof content==='string'?content:(content??[]).filter((p:any)=>p.type==='text').map((p:any)=>p.text).join('\n');

export function branchContext(file:string, directory:string, events:DisplayEvent[], seq:number, mode:'reply'|'edit') {
  const target=events.find(e=>e.seq===seq);
  const type=mode==='edit'?'user/message':'assistant/message';
  if(!target||target.type!==type)throw new Error('Choose a message from this conversation.');
  if(mode==='edit'&&events.filter(e=>e.type==='user/message').at(-1)?.seq!==seq)throw new Error('Only the latest user message can be edited. Reload the conversation.');
  // createBranchedSession changes its manager's active file. Use a separate
  // manager so the source conversation's live agent and leaf remain untouched.
  const manager=SessionManager.open(file,directory);
  const role=mode==='edit'?'user':'assistant';
  const ordinal=events.filter(e=>e.type===type&&e.seq<=seq).length-1;
  const entry=manager.getBranch().filter(e=>e.type==='message'&&e.message.role===role)[ordinal];
  const content=mode==='edit'?target.data.content:target.data.message?.content;
  if(!entry||entry.type!=='message'||messageText((entry.message as any).content)!==messageText(content))throw new Error('Cannot locate this message in Pi history. Reload the conversation.');
  if(mode==='reply'&&entry.message.role==='assistant'&&entry.message.content.some(p=>p.type==='toolCall'))throw new Error('Choose the reply after the tools have finished.');
  const leaf=mode==='edit'?entry.parentId:entry.id;
  const branchFile=leaf?manager.createBranchedSession(leaf):undefined;
  let cutoff=seq;
  if(mode==='edit')cutoff=events.findLast(e=>e.seq<seq&&e.type==='turn/start')?.seq??seq;
  const inherited=events.filter(e=>mode==='edit'?e.seq<cutoff:e.seq<=cutoff);
  return {manager:leaf?manager:undefined,file:branchFile,events:inherited};
}
