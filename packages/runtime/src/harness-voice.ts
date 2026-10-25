// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createRequire} from 'node:module';
import {identifier,type Data} from '../../protocol/src/index.js';
const {WebSocket}=createRequire(import.meta.url)('ws');
type Call=(method:string,params:Data)=>Promise<any>;
interface Seat {clientId:string;sessionId:string;openId:string;socket:any;events:Data[];bytes:number;seen:number;timer:ReturnType<typeof setInterval>;submitted:Set<string>;ready:boolean;recording:boolean;transcribing:boolean;captureEnded:boolean;audioSeq:number;opening:Promise<void>;closed:boolean}
/** Browser mic/speaker transport for the existing scoped companion. No desktop
 * audio devices, second agent loop, credentials in clients, or automatic replay. */
export class HarnessVoice {
 private seat?:Seat;
 constructor(private call:Call,private socketFactory=(url:string)=>new WebSocket(url,{handshakeTimeout:5000,maxPayload:1024*1024,perMessageDeflate:false})){}
 private push(s:Seat,event:Data){
  if(s.closed)return;const size=Buffer.byteLength(JSON.stringify(event));
  if(s.bytes+size>2*1024*1024||s.events.length>=256){void this.retire(s);return;}
  s.bytes+=size;s.events.push(event);
 }
 private async retire(s:Seat){
  if(s.closed)return;s.closed=true;clearInterval(s.timer);s.socket?.terminate();
  await s.opening.catch(()=>{});
  await this.call('voice.close',{sessionId:s.sessionId,openId:s.openId}).catch(()=>{});
  if(this.seat===s)this.seat=undefined;
 }
 async close(){if(this.seat)await this.retire(this.seat);}
 async operation(action:string,p:Data){
  const clientId=identifier(p.clientId),sessionId=identifier(p.sessionId),openId=identifier(p.openId);
  if(action==='open'){
   if(this.seat)throw Error('Voice is already open or closing. Close it before opening another.');
   const s:Seat={clientId,sessionId,openId,socket:undefined,events:[],bytes:0,seen:Date.now(),timer:undefined as any,submitted:new Set(),ready:false,recording:false,transcribing:false,captureEnded:false,audioSeq:0,opening:Promise.resolve(),closed:false};this.seat=s;
   s.timer=setInterval(()=>{if(Date.now()-s.seen>8000)void this.retire(s);},2000);s.timer.unref();
   s.opening=(async()=>{
    const ticket=await this.call('voice.ticket',{sessionId,surface:'linux',openId});
    if(s.closed)return;
    if(ticket.protocol!=='resonant-voice/1'||ticket.sessionId!==sessionId||!/^ws:\/\/127\.0\.0\.1:\d+\/voice$/.test(ticket.url)||!/^[a-f0-9]{64}$/.test(ticket.ticket))throw Error('Invalid scoped speech connection.');
    const ws=s.socket=this.socketFactory(ticket.url);
    ws.on('open',()=>{if(!s.closed)ws.send(JSON.stringify({type:'auth',ticket:ticket.ticket,textSource:'plugin',profile:'main'}));});
    ws.on('message',(data:Buffer,binary:boolean)=>{
     if(s.closed)return;
     try{
      if(binary){this.push(s,{type:'pcm',data:Buffer.from(data).toString('base64')});return;}
      const e=JSON.parse(data.toString());
      if(e.type==='ready')s.ready=true;
      if(e.type==='recording-ended'){s.recording=false;s.transcribing=true;s.captureEnded=true;}
      if(['transcript','empty-transcript'].includes(e.type))s.transcribing=false;
      if(e.type==='timing'&&['asr-final','first-pcm'].includes(e.stage)&&Number.isFinite(e.elapsedMs))this.push(s,{type:'timing',stage:e.stage,elapsedMs:e.elapsedMs});
      if(e.type==='transcript'){
       if(typeof e.requestId!=='string'||!/^[a-f0-9-]{36}$/.test(e.requestId)||typeof e.text!=='string'||e.text.length>8192)throw Error('Invalid speech transcript.');
       if(!s.submitted.has(e.requestId)){s.submitted.add(e.requestId);void this.submit(s,e).catch(error=>this.push(s,{type:'error',message:error.message}));}
      }
      // Only protocol events, never service tickets or arbitrary diagnostic data.
      if(['ready','listening','recording-ended','transcript','transcript-partial','empty-transcript','speaking','speech-idle','turn-complete','clear','error'].includes(e.type))this.push(s,e);
     }catch{this.push(s,{type:'error',message:'Invalid speech response. Close voice; nothing was replayed.'});void this.retire(s);}
    });
    ws.on('error',()=>{this.push(s,{type:'error',message:'Voice disconnected. Inspect the conversation; nothing was resent.'});s.ready=false;});
    ws.on('close',()=>{s.ready=false;this.push(s,{type:'error',message:'Voice connection closed. Reopen voice to continue.'});});
   })();
   try{await s.opening;return {opened:true};}catch(error){await this.retire(s);throw error;}
  }
  const s=this.seat;if(!s||s.closed||s.clientId!==clientId||s.sessionId!==sessionId||s.openId!==openId)throw Error('This voice connection is no longer active. Nothing was replayed.');s.seen=Date.now();
  if(action==='close'){await this.retire(s);return {closed:true};}
  if(action==='events'){const events=s.events;s.events=[];s.bytes=0;return {events};}
  if(!s.ready)throw Error('Speech is not ready.');
  if(action==='audio'){
   if(p.seq!==s.audioSeq||typeof p.data!=='string'||p.data.length>24000||!/^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(p.data))throw Error('Audio stream interrupted. Close voice; audio was not retried.');
   const bytes=Buffer.from(p.data,'base64');if(bytes.length%2)throw Error('Use mono signed 16-bit PCM.');s.audioSeq++;if(!s.recording&&s.captureEnded)return {accepted:true,ended:true};if(!s.recording)throw Error('Microphone is not recording.');s.socket.send(bytes);return {accepted:true};
  }
  if(action==='control'&&['begin','end','interrupt'].includes(p.type)){
   if(p.type==='begin'){if(s.recording||s.transcribing)throw Error('Wait for the current recording to finish.');s.recording=true;s.captureEnded=false;}
   if(p.type==='end'){if(!s.recording&&s.captureEnded)return {accepted:true,ended:true};if(!s.recording)throw Error('Microphone is not recording.');s.recording=false;s.transcribing=true;s.captureEnded=true;}
   s.socket.send(JSON.stringify({type:p.type}));return {accepted:true};
  }
  throw Error('Unknown voice operation.');
 }
 private async submit(s:Seat,e:Data){
  if(s.closed)return;
  const queue=await this.call('session.queue',{sessionId:s.sessionId});
  if(s.closed)return;
  if(queue.items.some((x:Data)=>x.canResolve))throw Error('Inspect unconfirmed input before speaking again.');
  // Canonical speech identity is retained by AH. A lost reply is never retried.
  try{await this.call('session.prompt',{sessionId:s.sessionId,requestId:'resonant-voice:'+e.requestId,inputMode:'voice',content:[{type:'text',text:e.text}],mode:queue.activeTurnId?'steer':'queue',resumeQueue:true,...(queue.activeTurnId?{expectedTurnId:queue.activeTurnId}:{})});}
  catch{throw Error('Voice submission is unconfirmed. Inspect this conversation before sending again.');}
 }
}
