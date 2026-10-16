// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import sharp from 'sharp';
import {createHash} from 'node:crypto';
import {authoredDshProject} from './dsh-project.mjs';
export async function authoredRichDshProject(cwd){
 const value=authoredDshProject(cwd),bytes=await sharp({create:{width:3,height:2,channels:3,background:'#315add'}}).png().toBuffer();
 const attachment={attachmentId:'sha256:'+createHash('sha256').update(bytes).digest('hex'),mediaType:'image/png',bytes:bytes.length,width:3,height:2,name:'authored-history.png'},image={type:'image',attachment};
 const rows=value.sessions[0].records;
 rows[1].event.data.content.push(structuredClone(image),structuredClone(image));
 rows[2].event.data.message.content.unshift({type:'reasoning',text:'AUTHORED-REASONING: compare the historical blue image.',signature:'OPAQUE-REPLAY-MUST-NOT-ENTER-CONTEXT'});
 rows[2].event.data.message.source={kind:'model',provider:'old-fixture',model:'old-model',replayState:{opaque:'OPAQUE-REPLAY-MUST-NOT-ENTER-CONTEXT'}};
 rows[4].event.data.message.content.push(structuredClone(image));
 rows.splice(rows.length-1,0,{type:'event',event:{type:'image/offload',time:1700000000008,data:{targets:[{seq:1,imageIndexes:[1]}]}}});
 rows.forEach((row,i)=>row.event.seq=i);value.sessions[0].opening.cursor=rows.length-1;
 value.attachments=[{attachmentId:attachment.attachmentId,bytes:bytes.length,data:bytes.toString('base64')}];
 return {value,attachment,bytes};
}
