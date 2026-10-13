// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {constants,existsSync,lstatSync,realpathSync,mkdirSync,readdirSync,openSync,fstatSync,readSync,readFileSync,writeFileSync,fsyncSync,closeSync,renameSync,unlinkSync,type Stats} from 'node:fs';
import {createHash,randomUUID} from 'node:crypto';
import {dirname,join,resolve} from 'node:path';
export const wikiDigest=(value:string|Uint8Array)=>createHash('sha256').update(value).digest('hex');
export const wikiActionKey=(owner:string,entry:string,call:string)=>wikiDigest(JSON.stringify([owner,entry,call]));
export type WikiReceipt={schema:'augmentor-wiki-action/1';key:string;tool:string;state:'started'|'completed'|'refused'|'unknown'};
type Lock={schema:'augmentor-wiki-lock/1';pid:number;processStart:string;bootId:string;nonce:string;kind:'action'|'review'};
type Review={schema:'augmentor-wiki-review/1';key:string;sha256:string;decision:'permit-future-changes';reviewId:string;reviewedAt:number;operatorUid:number};
const keyPattern=/^[a-f0-9]{64}$/,tools=['wiki_write','wiki_rename','wiki_scaffold','wiki_archive','wiki_lint'];
function owned(info:Stats){if(!info.isFile()||info.nlink!==1||info.uid!==process.getuid!()||(info.mode&0o077)!==0||info.size>16384)throw Error('Wiki receipt/lock is not a private bounded file; preserve its original.');}
function read(path:string){const before=lstatSync(path);owned(before);const fd=openSync(path,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);try{const now=fstatSync(fd);owned(now);if(now.ino!==before.ino||now.dev!==before.dev)throw Error('Wiki receipt changed during inspection.');const buffer=Buffer.alloc(16385),n=readSync(fd,buffer,0,buffer.length,0);if(n>16384)throw Error('Wiki receipt exceeds its bound.');const bytes=buffer.subarray(0,n);return {bytes,sha256:wikiDigest(bytes),ino:now.ino,dev:now.dev};}finally{closeSync(fd);}}
function processIdentity(pid:number){const info=lstatSync('/proc/'+pid);if(info.uid!==process.getuid!())throw Error('Wiki lock process ownership cannot be verified.');const stat=readFileSync('/proc/'+pid+'/stat','utf8'),start=stat.slice(stat.lastIndexOf(')')+2).trim().split(/\s+/)[19];if(!/^\d+$/.test(start))throw Error('Wiki process identity is unavailable.');return {processStart:start,bootId:readFileSync('/proc/sys/kernel/random/boot_id','utf8').trim()};}
function lockState(bytes:Buffer):'live'|'orphaned'|'unattested'{
 let row:Lock;try{row=JSON.parse(bytes.toString('utf8'));}catch{return 'unattested';}
 if(!row||Object.keys(row).some(k=>!['schema','pid','processStart','bootId','nonce','kind'].includes(k))||row.schema!=='augmentor-wiki-lock/1'||!Number.isSafeInteger(row.pid)||row.pid<1||typeof row.processStart!=='string'||!/^\d+$/.test(row.processStart)||typeof row.bootId!=='string'||!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(row.bootId)||typeof row.nonce!=='string'||!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(row.nonce)||!['action','review'].includes(row.kind))return 'unattested';
 try{const now=processIdentity(row.pid);return now.processStart===row.processStart&&now.bootId===row.bootId?'live':'orphaned';}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return 'orphaned';throw error;}
}
/** Metadata-only review. Original unknown receipts and every native call stay intact. */
export class WikiReceipts {
 readonly root:string;
 constructor(stateDir:string,readonly vaultPath:string){this.root=join(stateDir,'wiki-actions',wikiDigest(vaultPath));}
 private directory(create=false){
  if(process.platform!=='linux')throw Error('Wiki receipt review currently requires Linux.');
  let path=this.root;const missing:string[]=[];while(!existsSync(path)){try{lstatSync(path);throw Error('Linked Wiki receipt parent is unsafe.');}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}missing.unshift(path);path=dirname(path);}
  if(realpathSync(path)!==resolve(path))throw Error('Linked Wiki receipt parent is unsafe.');if(missing.length&&!create)return false;for(const next of missing)mkdirSync(next,{mode:0o700});
  const info=lstatSync(this.root);if(!info.isDirectory()||info.uid!==process.getuid!()||(info.mode&0o077)!==0||realpathSync(this.root)!==resolve(this.root))throw Error('Wiki receipt directory is unsafe.');return true;
 }
 private flush(){const fd=openSync(this.root,constants.O_RDONLY|constants.O_DIRECTORY|constants.O_NOFOLLOW);try{fsyncSync(fd);}finally{closeSync(fd);}}
 private publish(name:string,value:unknown,exclusive=true){const path=join(this.root,name),temp=exclusive?path:path+'.'+randomUUID()+'.tmp';let published=false;try{const fd=openSync(temp,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);try{writeFileSync(fd,JSON.stringify(value)+'\n');fsyncSync(fd);}finally{closeSync(fd);}if(!exclusive)renameSync(temp,path);published=true;this.flush();}finally{if(!published&&!exclusive&&existsSync(temp))unlinkSync(temp);}}
 describe(omitLock=false){
  const files:Array<{name:string;sha256:string}>=[],rows:Array<WikiReceipt&{sha256:string;reviewed:boolean;review:Review|null}>=[],reviews:Review[]=[];
  let lock:{state:'live'|'orphaned'|'unattested';sha256:string;pid:number|null;kind:string|null}|null=null;
  if(this.directory()){
   const names=readdirSync(this.root).sort();if(names.length>6145)throw Error('Wiki receipt store exceeds its review bounds; preserve it.');
   for(const name of names){if(name==='.operation-lock'&&omitLock)continue;const file=read(join(this.root,name));files.push({name,sha256:file.sha256});
    if(name==='.operation-lock'){const state=lockState(file.bytes),value=state==='unattested'?null:JSON.parse(file.bytes.toString('utf8'));lock={state,sha256:file.sha256,pid:value?.pid??null,kind:value?.kind??null};continue;}
    let value;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(file.bytes));}catch{throw Error('Invalid Wiki receipt JSON; preserve '+name);}
    if(/^review-(?:[a-f0-9]{64}|operation-lock)-[a-f0-9]{64}\.json$/.test(name)){
     if(Object.keys(value).some(k=>!['schema','key','sha256','decision','reviewId','reviewedAt','operatorUid'].includes(k))||value.schema!=='augmentor-wiki-review/1'||!((keyPattern.test(value.key)||value.key==='operation-lock')&&keyPattern.test(value.sha256))||name!==`review-${value.key}-${value.sha256}.json`||value.decision!=='permit-future-changes'||typeof value.reviewId!=='string'||!Number.isSafeInteger(value.reviewedAt)||value.reviewedAt<1||value.operatorUid!==process.getuid!())throw Error('Invalid Wiki review; its original is preserved.');reviews.push(value);continue;
    }
    if(/^lease-[a-f0-9]{64}\.json$/.test(name)){if(name!==`lease-${file.sha256}.json`||lockState(file.bytes)==='unattested')throw Error('Invalid preserved Wiki lease.');continue;}
    if(Object.keys(value).some(k=>!['schema','key','tool','state'].includes(k))||!keyPattern.test(value.key)||name!==value.key+'.json'||value.schema!=='augmentor-wiki-action/1'||!tools.includes(value.tool)||!['started','completed','refused','unknown'].includes(value.state))throw Error('Invalid Wiki receipt; its original is preserved.');
    rows.push({...value,sha256:file.sha256,reviewed:false,review:null});
   }
  }
  if(rows.length>2048)throw Error('Wiki actions exceed their review bounds; preserve them.');for(const row of rows){row.review=reviews.find(review=>review.key===row.key&&review.sha256===row.sha256)??null;row.reviewed=!!row.review;}
  return {vaultId:wikiDigest(this.vaultPath),revision:wikiDigest(JSON.stringify(files)),rows,lock,blocked:!!lock||rows.some(row=>['started','unknown'].includes(row.state)&&!row.reviewed)};
 }
 acquire(kind:'action'|'review'='action'){
  this.directory(true);const path=join(this.root,'.operation-lock'),fd=openSync(path,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);const info=fstatSync(fd);
  let sha256:string;
  try{const identity=processIdentity(process.pid),value:Lock={schema:'augmentor-wiki-lock/1',pid:process.pid,...identity,nonce:randomUUID(),kind},bytes=JSON.stringify(value)+'\n';sha256=wikiDigest(bytes);writeFileSync(fd,bytes);fsyncSync(fd);this.flush();}catch(error){closeSync(fd);const now=lstatSync(path);if(now.ino===info.ino&&now.dev===info.dev)unlinkSync(path);throw error;}
  return ()=>{try{const now=read(path);if(now.ino!==info.ino||now.dev!==info.dev||now.sha256!==sha256)throw Error('Wiki operation lock changed; preserve its replacement.');unlinkSync(path);this.flush();}finally{closeSync(fd);}};
 }
 start(key:string,tool:string){if(!keyPattern.test(key)||!tools.includes(tool))throw Error('Invalid Wiki native action identity.');const row:WikiReceipt={schema:'augmentor-wiki-action/1',key,tool,state:'started'};this.publish(key+'.json',row);return row;}
 finish(row:WikiReceipt,state:WikiReceipt['state']){this.publish(row.key+'.json',{...row,state},false);}
 review(input:{key:string;sha256:string;expectedRevision:string;acknowledgeUnknownOutcome:boolean;reviewId:string}){
  if(input.acknowledgeUnknownOutcome!==true||typeof input.reviewId!=='string'||!/^[a-f0-9-]{36}$/.test(input.reviewId))throw Error('Explicitly acknowledge the unknown outcome after inspecting the recorded action and vault.');
  const before=this.describe();if(before.revision!==input.expectedRevision)throw Error('Wiki receipts changed. Refresh before reviewing.');
  const target=input.key==='operation-lock'?before.lock:before.rows.find(row=>row.key===input.key);
  if(!target||target.sha256!==input.sha256||input.key!=='operation-lock'&&!['started','unknown'].includes((target as WikiReceipt).state))throw Error('Choose the exact uncertain Wiki receipt shown in the current inspection.');
  if(before.lock&&before.lock.state!=='orphaned')throw Error('A live or unattested Wiki operation lock cannot be released through review.');
  let release:(()=>void)|undefined;
  try{
   if(!before.lock)release=this.acquire('review');const current=this.describe(!!release);if(current.revision!==before.revision)throw Error('Wiki receipts changed during review. Refresh before continuing.');
   const name=`review-${input.key}-${input.sha256}.json`,record:Review={schema:'augmentor-wiki-review/1',key:input.key,sha256:input.sha256,decision:'permit-future-changes',reviewId:input.reviewId,reviewedAt:Date.now(),operatorUid:process.getuid!()};
   if(!existsSync(join(this.root,name)))this.publish(name,record);
   if(before.lock){
    const path=join(this.root,'.operation-lock'),old=read(path);if(old.sha256!==before.lock.sha256||lockState(old.bytes)!=='orphaned')throw Error('Wiki lock ownership changed; preserve it.');
    const archive=join(this.root,`lease-${old.sha256}.json`);if(!existsSync(archive)){const fd=openSync(archive,constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);try{writeFileSync(fd,old.bytes);fsyncSync(fd);}finally{closeSync(fd);}this.flush();}else if(read(archive).sha256!==old.sha256)throw Error('Preserved Wiki lease differs; no lock is removed.');
    const now=read(path);if(now.sha256!==old.sha256||now.ino!==old.ino||now.dev!==old.dev)throw Error('Wiki lock changed before release; preserve it.');unlinkSync(path);this.flush();
   }
  }finally{release?.();}
  return this.describe();
 }
}
