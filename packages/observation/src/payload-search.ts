// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {createHash,createHmac,randomBytes,timingSafeEqual} from 'node:crypto';
import {atomicJson,readJson} from '../../runtime/src/storage.js';
import {PayloadIndex,PayloadUnavailable,PAYLOAD_BLOCK} from './payload-index.js';
import type {Observation,ObservationStore} from './store.js';
import type {ObservationIndex} from './journal-index.js';
export type SearchScope='metadata'|'payloads'|'all';
export interface SearchOptions {query?:unknown;scope?:unknown;cursor?:unknown;limit?:unknown}
type Current={seq:number;id:string;hash:string;offset:number;mask:number;metadataMask:number};
type Cursor={version:1;sessionId:string;query:string;scope:SearchScope;ceiling:number;total:number;before:number;inclusive:boolean;current?:Current};
const digest=(text:string)=>createHash('sha256').update(text).digest('hex');
// Per-code-point lowercase avoids contextual case changes at chunk boundaries.
const fold=(text:string)=>text.replace(/./gsu,character=>character.toLowerCase()).replace(/ς/g,'σ');
const maskFor=(text:string,terms:string[])=>{const lower=fold(text);return terms.reduce((mask,term,i)=>mask|(lower.includes(term)?1<<i:0),0);};
function decoded(bytes:Buffer){let start=0,end=bytes.length;while(start<end&&(bytes[start]!&0xc0)===0x80)start++;let last=end-1;while(last>=start&&(bytes[last]!&0xc0)===0x80)last--;if(last>=start){const b=bytes[last]!,length=b<0x80?1:b<0xe0?2:b<0xf0?3:4;if(end-last<length)end=last;}return {text:new TextDecoder('utf8',{fatal:true}).decode(bytes.subarray(start,end)),start};}
function preview(text:string,terms:string[],base:number){const lower=fold(text),term=terms.find(term=>lower.includes(term));if(!term)return undefined;const at=lower.indexOf(term);let original=0,folded=0;for(const character of text){if(folded>=at)break;folded+=fold(character).length;original+=character.length;}const from=Math.max(0,original-80),to=Math.min(text.length,original+term.length+160);let start=from,end=to;if(start>0&&/[\uDC00-\uDFFF]/.test(text[start]!))start--;if(end<text.length&&/[\uDC00-\uDFFF]/.test(text[end]!))end++;return {offset:base+Buffer.byteLength(text.slice(0,start)),units:'utf8-bytes',text:text.slice(start,end)};}
/** Stateless, authenticated progress survives owner restart. Private bodies stay
 * in their existing capture files; a cursor carries only positions/hashes/masks.
 */
export class PayloadSearch {
 private key?:string;
 constructor(readonly store:ObservationStore,readonly index:(sessionId:string)=>ObservationIndex,readonly payloadIndex:(sessionId:string,eventId:string)=>PayloadIndex){}
 private secret(){if(this.key)return this.key;const file=join(this.store.root,'search-key.json');if(existsSync(file)){const value=readJson<{key:string}>(file,{key:''});if(!/^[a-f0-9]{64}$/.test(value.key))throw Error('Private search key is damaged.');this.key=value.key;}else{this.key=randomBytes(32).toString('hex');atomicJson(file,{key:this.key});}return this.key;}
 private sign(value:string){return createHmac('sha256',Buffer.from(this.secret(),'hex')).update(value).digest('base64url');}
 private encode(cursor:Cursor){const value=Buffer.from(JSON.stringify(cursor)).toString('base64url');return value+'.'+this.sign(value);}
 private decode(value:unknown):Cursor{if(typeof value!=='string'||value.length>4096)throw Error('Invalid retained search cursor');const [body,signature,...extra]=value.split('.');if(!body||!signature||extra.length||signature.length!==43||!timingSafeEqual(Buffer.from(signature),Buffer.from(this.sign(body))))throw Error('Invalid retained search cursor');let cursor:Cursor;try{cursor=JSON.parse(Buffer.from(body,'base64url').toString('utf8'));}catch{throw Error('Invalid retained search cursor');}if(cursor.version!==1)throw Error('Unsupported retained search cursor');return cursor;}
 page(sessionId:string,options:SearchOptions={}){
  const query=options.query;if(typeof query!=='string'||!query.trim()||query.length>256)throw Error('Search 1–256 characters of retained records.');const terms=query.trim().split(/\s+/).map(fold);if(terms.length>16)throw Error('Search up to 16 literal terms.');
  const scope=options.scope??'all';if(!['metadata','payloads','all'].includes(String(scope)))throw Error('Choose metadata, payloads or all search scope.');const limit=options.limit??100;if(!Number.isSafeInteger(limit)||Number(limit)<1||Number(limit)>100)throw Error('Invalid retained search limit');
  const index=this.index(sessionId),snapshot=index.snapshot(),cursor:Cursor=options.cursor===undefined?{version:1,sessionId,query,scope:scope as SearchScope,ceiling:snapshot.lastSeq??0,total:snapshot.count,before:snapshot.lastSeq??0,inclusive:true}:this.decode(options.cursor);
  if(cursor.sessionId!==sessionId||cursor.query!==query||cursor.scope!==scope)throw Error('Retained search cursor belongs to another conversation, query or scope.');
  const records:Observation[]=[],matches:Record<string,unknown>[]=[],unavailable:Record<string,number>={};let visits=0,completed=0,metadataBytes=0,payloadBytes=0,buildBytes=0,responseBytes=0,examined=0;const allMask=(1<<terms.length)-1;
  const unavailablePayload=(reason:string)=>{unavailable[reason]=(unavailable[reason]??0)+1;};
  let finished=false;
  while(visits<1000&&metadataBytes<512*1024&&records.length<Number(limit)){
   if(buildBytes||payloadBytes>=(512*1024-PAYLOAD_BLOCK*2))break;
   const page=index.page({before:cursor.current?.seq??cursor.before,after:0,forward:false,limit:1,terms:[],inclusiveBefore:!!cursor.current||cursor.inclusive});const record=page.records[0];if(!record){finished=true;break;}
   const json=JSON.stringify(record),identity=digest(json);if(cursor.current&&(cursor.current.id!==record.id||cursor.current.seq!==record.seq||cursor.current.hash!==identity))throw Error('Retained search record changed. Start a new search.');
   const possibleBytes=Buffer.byteLength(json)+2048;if(responseBytes+possibleBytes>1024*1024-8192){if(!records.length)throw Error('A retained search result exceeds the connection limit; original history is preserved.');break;}
   visits++;metadataBytes+=page.journalBytesRead;
   const metadataMask=cursor.current?.metadataMask??maskFor(json,terms);let payloadMask=cursor.current?.mask??0,offset=cursor.current?.offset??0,excerpt:ReturnType<typeof preview>,done=true,payloadMatched=false;
   let matched=scope!=='payloads'&&metadataMask===allMask;
   if(!matched&&scope!=='metadata'){
    if(record.payload?.state!=='retained')unavailablePayload(record.payload?.state??'not-recorded');
    else{
     const body=this.payloadIndex(sessionId,record.id),before=body.buildBytesRead;let examinedBytes=0;examined++;
     try{body.withReader(record.payload.sha256??'',reader=>{try{
       if(record.payload?.bytes!==reader.size||offset>reader.size||offset%PAYLOAD_BLOCK!==0)throw new PayloadUnavailable('capture-boundary-changed');
       while(offset<reader.size){
        if(payloadBytes+reader.bytes()>512*1024-PAYLOAD_BLOCK*2){done=false;break;}
        const position=offset/PAYLOAD_BLOCK,current=reader.block(position),prior=position?reader.block(position-1).subarray(-1024):Buffer.alloc(0),window=decoded(Buffer.concat([prior,current])),base=offset-prior.length+window.start;
        payloadMask|=maskFor(window.text,terms);offset+=current.length;
        matched=(scope==='all'?metadataMask|payloadMask:payloadMask)===allMask;
        if(matched){payloadMatched=true;excerpt=preview(window.text,terms,base);break;}
       }
      }finally{examinedBytes=reader.bytes();}});
     }catch(error){done=true;matched=false;unavailablePayload(error instanceof PayloadUnavailable?error.reason:'read-failed');}
     payloadBytes+=examinedBytes;buildBytes+=body.buildBytesRead-before;
    }
   }
   if(!done){cursor.current={seq:record.seq,id:record.id,hash:identity,offset,mask:payloadMask,metadataMask};break;}
   completed++;cursor.current=undefined;cursor.before=record.seq;cursor.inclusive=false;
   if(matched){records.push(record);matches.push({eventId:record.id,source:payloadMatched?(scope==='all'&&metadataMask?'metadata-and-payload':'payload'):'metadata',metadataTerms:metadataMask,payloadTerms:payloadMask,...(payloadMatched?{payloadSha256:record.payload!.sha256,excerpt}: {})});responseBytes+=possibleBytes;}
   if(!page.hasMore){finished=true;break;}
  }
  records.reverse();matches.reverse();
  return {protocol:'augmentor-observation/1',records,matches,hasMore:!finished,nextCursor:finished?null:this.encode(cursor),coverage:{scope:'retained-'+scope+'-literal-search',snapshotLatestSeq:cursor.ceiling,totalRecords:cursor.total,metadataVisits:visits,completedRecords:completed,examinedPayloads:examined,unavailablePayloads:unavailable,metadataBytesRead:metadataBytes,payloadBytesRead:payloadBytes,indexBuildBytesRead:buildBytes,partialPayload:!!cursor.current,query,credentialFields:'existing capture redactions',attachments:'inline serialized JSON only',nativeHistory:false,index:'augmentor-payload-index/1'}};
 }
}
