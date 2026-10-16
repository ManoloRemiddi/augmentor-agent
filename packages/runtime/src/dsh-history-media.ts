// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {AgentSession} from '@earendil-works/pi-coding-agent';
import type {ImageContent,TextContent} from '@earendil-works/pi-ai';
import {PiAttachments,promptAttachments} from './attachments.js';
import type {Data} from '../../protocol/src/index.js';

export const DSH_MEDIA_TYPE='augmentor.dsh-media.v1';
export const DSH_MEDIA_SCHEMA='augmentor-dsh-media/1';
/** Public Agent transform, deliberately outside the extension event runner:
 * a missing/corrupt/unauthorized image must abort rather than be swallowed as
 * an extension warning followed by a request with silently missing images. */
export class PiDshHistoryMedia {
 private undo?:()=>void;
 constructor(private attachments:PiAttachments,private sid:string){}
 install(session:AgentSession){
  this.dispose();const previous=session.agent.transformContext;
  const hook:typeof previous=async(messages,signal)=>{
   const transformed=previous?await previous(messages,signal):messages;
   let imageBytes=0,imageCount=0;
   const output=[];
   for(const message of transformed){
    if(signal?.aborted)throw signal.reason??Error('Stopped while resolving historical images.');
    if(message.role!=='custom'||message.customType!==DSH_MEDIA_TYPE){output.push(message);continue;}
    const details=message.details as Data|undefined;
    if(details?.schema!==DSH_MEDIA_SCHEMA||typeof message.content!=='string'||!Array.isArray(details.images))throw Error('Imported media context is invalid.');
    const content:(TextContent|ImageContent)[]=[{type:'text',text:message.content}];
    for(const raw of details.images){
     const [part]=promptAttachments([{type:'image',attachment:raw.attachment}]);
     if(part.type!=='image'||raw.offloaded!==undefined&&raw.offloaded!==true)throw Error('Imported image reference is invalid.');
     if(raw.offloaded){content.push({type:'text',text:'Historical image explicitly offloaded in DSH. Read-only stored image: '+this.attachments.historicalImagePath(this.sid,part.attachment)});continue;}
     if(!session.model?.input.includes('image'))throw Error('This imported history contains images. Select a model with image input before continuing.');
     imageBytes+=part.attachment.bytes;imageCount++;
     if(imageBytes>20*1024*1024||imageCount>64)throw Error('Active imported image context exceeds 20 MiB or 64 images. Compact or branch the conversation before continuing.');
     const image=await this.attachments.image(this.sid,part.attachment);
     if(signal?.aborted)throw signal.reason??Error('Stopped while resolving historical images.');
     content.push({type:'image',mimeType:part.attachment.mediaType,data:Buffer.from(image.data).toString('base64')});
    }
    output.push({...message,content});
   }
   return output;
  };
  session.agent.transformContext=hook;
  this.undo=()=>{if(session.agent.transformContext===hook)session.agent.transformContext=previous;};
 }
 dispose(){this.undo?.();this.undo=undefined;}
}
