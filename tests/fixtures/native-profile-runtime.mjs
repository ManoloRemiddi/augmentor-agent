// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFile,writeFile} from 'node:fs/promises';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';import sharp from 'sharp';
import {planFixture} from './plans.mjs';
const {inspectNativeProfile,importNativeProfile}=await import(pathToFileURL(resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.','dist/runtime/src/native-profile-import.js')));
async function vision(f){await f.stop();const path=join(f.config,'agent/models.json'),v=JSON.parse(await readFile(path));v.providers.fixture.models[0].input=['text','image'];await writeFile(path,JSON.stringify(v),{mode:0o600});await f.start();}
export async function nativeProfileFixture(t){
 const source=await planFixture(t,{policy:'read-only'}),target=await planFixture(t,{policy:'read-only',attachmentMode:true});await vision(source);await vision(target);
 const sid='relocated-native',child='relocated-branch';await source.call('session.create',{sessionId:sid,cwd:source.workspace,selection:source.selection});
 const link=await source.link(),url=new URL(link.url),headers={Authorization:'Bearer '+new URLSearchParams(url.hash.slice(1)).get('token')};
 const fileBytes=Buffer.from('EXACT-RELOCATED-ATTACHMENT\n'),pixels=await sharp({create:{width:3,height:2,channels:3,background:'#a30'}}).png().toBuffer();
 const upload=async(name,bytes,mediaType)=>{const q=new URLSearchParams({sessionId:sid,name});if(mediaType)q.set('mediaType',mediaType);const response=await fetch(url.origin+'/api/attachments/upload?'+q,{method:'POST',headers,body:bytes});assertResponse(response);return response.json();};
 const file=await upload('source-note.txt',fileBytes),image=await upload('source-image.png',pixels,'image/png');
 await source.call('session.prompt',{sessionId:sid,requestId:'source-uploaded-turn',content:[{type:'text',text:'SOURCE-NATIVE-WORK. Literal source state quote: '+source.state},{type:'file',attachment:file.file,receiptId:file.receiptId},{type:'image',attachment:image.attachment,receiptId:image.receiptId}]});await source.settled(sid);
 const history=await source.call('session.history',{sessionId:sid}),last=history.events.filter(x=>x.event.type==='assistant/message'&&x.event.data.message.stopReason==='stop').at(-1);if(!last)throw Error('Source native turn did not finish.');
 await source.call('session.branch',{sessionId:sid,newSessionId:child,messageSeq:last.event.seq,mode:'reply'});
 await source.call('draft.text',{sessionId:sid,expectedTextRevision:0,text:'UNSENT-SOURCE-DRAFT'});
 await target.call('session.create',{sessionId:'destination-native',cwd:target.workspace,selection:target.selection});await target.prompt('destination-native',{kind:'read',tag:'DESTINATION-NATIVE-WORK'});
 const original=await source.native(sid),branch=await source.native(child),destination=await target.native('destination-native'),memory=await target.call('memory.status');
 await source.stop();await target.stop();const inspected=inspectNativeProfile(source.state);
 return {source,target,sid,child,file,image,fileBytes,pixels,original,branch,destination,memory,inspected,transfer:()=>importNativeProfile(source.state,target.state,inspected.stateSha256)};
}
function assertResponse(response){if(!response.ok)throw Error('Authored native upload failed: '+response.status);}
