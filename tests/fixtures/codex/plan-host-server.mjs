// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored scripted native protocol peer. Never calls a provider.
import {createInterface} from 'node:readline';
import {readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
const path=join(process.env.CODEX_HOME,'synthetic-thread.json');let state;
try{state=JSON.parse(readFileSync(path));}catch{state={threadId:'synthetic-plan-thread',turns:[]};}
let nativeBusy=false,dropNext=false;
const save=()=>writeFileSync(path,JSON.stringify(state),{mode:0o600});
const send=value=>process.stdout.write(JSON.stringify(value)+'\n');
createInterface({input:process.stdin}).on('line',line=>{
  const request=JSON.parse(line),p=request.params??{};
  const answer=result=>send({id:request.id,result});
  if(request.method==='initialize')answer({userAgent:'synthetic-plan-peer'});
  else if(request.method==='thread/start'){save();answer({thread:{id:state.threadId}});}
  else if(request.method==='thread/resume'){
    if(state.rejectResume){delete state.rejectResume;save();send({id:request.id,error:{code:-32000,message:'Synthetic resume refusal'}});}
    else answer({thread:{id:state.threadId}});
  }
  else if(request.method==='thread/loaded/list')answer({data:[state.threadId,'synthetic-child'],nextCursor:null});
  else if(request.method==='thread/read')answer({thread:{id:p.threadId,status:{type:(p.threadId==='synthetic-child'?nativeBusy:state.turns.some(turn=>turn.status==='inProgress'))?'active':'idle'}}});
  else if(request.method==='thread/backgroundTerminals/list')answer({data:[],nextCursor:null});
  else if(request.method==='thread/goal/get')answer({goal:null});
  else if(request.method==='thread/turns/list')answer({data:[...state.turns].reverse().map(({items,...turn})=>turn),nextCursor:null});
  else if(request.method==='thread/items/list')answer({data:state.turns.filter(turn=>!p.turnId||turn.id===p.turnId).flatMap(turn=>turn.items.map(item=>({turnId:turn.id,item}))),nextCursor:null});
  else if(request.method==='turn/start'){
    const turn={id:'synthetic-turn-'+(state.turns.length+1),status:'inProgress',items:[{id:'user-'+p.clientUserMessageId,type:'userMessage',clientId:p.clientUserMessageId,content:p.input}]};state.turns.push(turn);save();
    if(dropNext){dropNext=false;return;}
    answer({turn:{id:turn.id}});send({method:'turn/started',params:{threadId:state.threadId,turn}});
    send({method:'item/completed',params:{threadId:state.threadId,turnId:turn.id,item:turn.items[0]}});
  }
  else if(request.method==='fixture/complete'){
    const turn=state.turns.find(turn=>turn.status==='inProgress');turn.status='completed';save();answer({});send({method:'turn/completed',params:{threadId:state.threadId,turn}});
  }
  else if(request.method==='fixture/busy'){nativeBusy=p.busy;answer({});}
  else if(request.method==='fixture/drop-next-ack'){dropNext=true;answer({});}
  else if(request.method==='fixture/reject-next-resume'){state.rejectResume=true;save();answer({});}
  else if(request.method==='fixture/marker')answer({pid:process.pid,marker:createHash('sha256').update(process.env.AUGMENTOR_CODEX_CREDENTIAL).digest('hex'),turns:state.turns.map(turn=>turn.items[0].clientId)});
  else if(request.method==='turn/interrupt'){
    const turn=state.turns.find(turn=>turn.id===p.turnId);turn.status='interrupted';save();answer({});send({method:'turn/completed',params:{threadId:state.threadId,turn}});
  }
  else if(request.id!==undefined)send({id:request.id,error:{code:-32601,message:'Unsupported synthetic operation'}});
});
