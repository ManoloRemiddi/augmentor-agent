// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createHash} from 'node:crypto';
import {authoredDshProject} from './dsh-project.mjs';
export function authoredFileDshProject(cwd,{bytes=Buffer.from('AUTHORED-DOCUMENT: continue using these exact stored bytes.\n'),name='authored-history.txt',where='user'}={}){
 const value=authoredDshProject(cwd),fileAttachment={attachmentId:'sha256:'+createHash('sha256').update(bytes).digest('hex'),name,bytes:bytes.length},part={type:'file',attachment:fileAttachment};
 const session=value.sessions[0],seq=where==='user'?1:where==='assistant'?5:4,event=session.records[seq].event;
 (where==='user'?event.data:event.data.message).content.push(structuredClone(part));
 value.files=[{attachmentId:fileAttachment.attachmentId,bytes:bytes.length,data:bytes.toString('base64')}];
 return {value,fileAttachment,fileBytes:bytes,filePart:part,fileSeq:seq};
}
