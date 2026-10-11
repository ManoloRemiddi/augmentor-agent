// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Browser-owned drafts; public DSH renders every card, drop target and viewer. */
export class DshAttachments {
 sessions=new Map();listeners=new Set();revision=0;busy=false;
 constructor(controller){this.controller=controller;}
 subscribe=fn=>{this.listeners.add(fn);return()=>this.listeners.delete(fn);};
 snapshot=()=>this.revision;
 changed(){this.revision++;for(const fn of this.listeners)fn();}
 draft(sid=this.controller.state.sessionId){if(!this.sessions.has(sid))this.sessions.set(sid,{items:[],uploads:{}});return this.sessions.get(sid);}
 add=(files,directories)=>{
  const sid=this.controller.state.sessionId;if(!sid)return 'Choose a conversation before adding attachments.';
  const d=this.draft(sid);if(d.items.length+files.length>16)return 'Choose at most sixteen attachments.';
  if(files.some(f=>directories?.has(f)||f.size>20*1024*1024))return 'Choose files smaller than twenty MiB; directories cannot be attached.';
  for(const file of files){const image=['image/png','image/jpeg','image/webp','image/gif'].includes(file.type),item={id:crypto.randomUUID(),kind:image?'image':'file',file,...(image?{previewUrl:URL.createObjectURL(file)}:{})};d.items.push(item);if(!image)void this.upload(sid,item);}
  this.changed();return null;
 };
 async upload(sid,item){
  const d=this.draft(sid),abort=new AbortController();item.abort?.abort();item.abort=abort;d.uploads[item.id]={status:'uploading',loaded:0,total:item.file.size};this.changed();
  try{const value=await this.transfer(sid,item.file,abort.signal);if(abort.signal.aborted||!d.items.includes(item))return;d.uploads[item.id]={status:'ready',...value};}
  catch(error){if(abort.signal.aborted||!d.items.includes(item))return;d.uploads[item.id]={status:'error',message:error.message};}
  finally{if(item.abort===abort)delete item.abort;this.changed();}
 }
 async transfer(sid,file,signal){
  const q=new URLSearchParams({sessionId:sid,name:file.name});if(['image/png','image/jpeg','image/webp','image/gif'].includes(file.type))q.set('mediaType',file.type);
  const response=await this.controller.fetcher('/api/attachments/upload?'+q,{method:'POST',headers:{Authorization:'Bearer '+this.controller.token,'Content-Type':'application/octet-stream'},body:file,signal});
  const value=await response.json();if(!response.ok)throw Error(value.error?.message||'Upload failed. Retry the upload explicitly.');return value;
 }
 remove=(id,sid=this.controller.state.sessionId)=>{const d=this.draft(sid),item=d.items.find(x=>x.id===id);if(!item)return;item.abort?.abort();if(item.previewUrl)URL.revokeObjectURL(item.previewUrl);d.items=d.items.filter(x=>x!==item);delete d.uploads[id];this.changed();};
 retry=id=>{const sid=this.controller.state.sessionId,item=this.draft(sid).items.find(x=>x.id===id);if(item?.kind==='file')void this.upload(sid,item);};
 async content(sid,items){
  const d=this.draft(sid),parts=[];
  for(const item of items){
   if(item.kind==='file'){const upload=d.uploads[item.id];if(upload?.status!=='ready')throw Error('Finish or retry the file upload before sending.');parts.push({type:'file',attachment:upload.file,receiptId:upload.receiptId});}
   else{item.receipt??=await this.transfer(sid,item.file);parts.push({type:'image',...item.receipt});}
  }
  return parts;
 }
 loaders=new Map();
 loader(sid){if(!this.loaders.has(sid)){const cache=new Map();const load=async attachment=>{const key=JSON.stringify(attachment);if(cache.has(key))return cache.get(key);const response=await this.controller.fetcher('/api/attachments/image?'+new URLSearchParams({sessionId:sid,ref:key}),{headers:{Authorization:'Bearer '+this.controller.token}});if(!response.ok)throw Error('Image could not be loaded.');const url=URL.createObjectURL(await response.blob());cache.set(key,url);return url;};load.peek=attachment=>cache.get(JSON.stringify(attachment));this.loaders.set(sid,load);}return this.loaders.get(sid);}
}
