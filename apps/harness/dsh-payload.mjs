// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Read every retained page against its immutable payload identity. */
export async function readDshPayload(rpc,sessionId,record,{maxBytes=Infinity}={}){
  let offset=0,text='',bytes=0;
  for(let pages=0;pages<4096;pages++){
    const page=await rpc('observation.payload',{sessionId,eventId:record.id,offset,...(record.payload?.sha256?{sha256:record.payload.sha256}:{})});
    if(!page.available)return {available:false,reason:page.reason};
    bytes+=new TextEncoder().encode(page.text).length;if(bytes>maxBytes)throw Error('Recorded body exceeds this dashboard’s 1 MiB limit; use the raw inspector.');text+=page.text;
    if(!page.hasMore)return {available:true,value:JSON.parse(text),raw:text};
    if(!Number.isSafeInteger(page.nextOffset)||page.nextOffset<=offset)throw Error('Retained payload pagination did not advance.');
    offset=page.nextOffset;
  }
  throw Error('Retained payload exceeds the inspection page limit.');
}
