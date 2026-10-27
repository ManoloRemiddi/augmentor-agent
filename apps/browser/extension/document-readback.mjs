// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Read only one bounded HTML entry from the standard Docs ZIP export. No paths
// are extracted to disk and no archive code or document script is executed.
const TEXT_LIMIT=1024*1024,DOWNLOAD_LIMIT=2*1024*1024
async function bounded(stream,limit){
 const reader=stream.getReader(),chunks=[];let length=0
 try{for(;;){const part=await reader.read();if(part.done)break;length+=part.value.byteLength;if(length>limit)throw Error('Document readback exceeds its supported size.');chunks.push(part.value)}}finally{await reader.cancel().catch(()=>{})}
 const bytes=new Uint8Array(length);let at=0;for(const chunk of chunks){bytes.set(chunk,at);at+=chunk.byteLength}return bytes
}
export async function decodeDocument(bytes,format){
 if(bytes[0]!==80||bytes[1]!==75){if(bytes.length>TEXT_LIMIT)throw Error('Document readback exceeds 1 MiB.');return new TextDecoder('utf-8',{fatal:true}).decode(bytes)}
 if(format!=='html')throw Error('Unexpected archive in plain-text export.')
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);let end=-1
 for(let at=bytes.length-22;at>=Math.max(0,bytes.length-65557);at--)if(view.getUint32(at,true)===0x06054b50&&at+22+view.getUint16(at+20,true)===bytes.length){end=at;break}
 if(end<0||view.getUint16(end+4,true)||view.getUint16(end+6,true))throw Error('Unsupported document archive.')
 const count=view.getUint16(end+10,true),size=view.getUint32(end+12,true),offset=view.getUint32(end+16,true)
 if(count>1024||offset+size>end)throw Error('Document archive directory exceeds its bound.')
 const html=[];let at=offset
 for(let n=0;n<count;n++){
  if(at+46>offset+size||view.getUint32(at,true)!==0x02014b50)throw Error('Invalid document archive directory.')
  const nameLength=view.getUint16(at+28,true),extra=view.getUint16(at+30,true),comment=view.getUint16(at+32,true),next=at+46+nameLength+extra+comment
  if(next>offset+size)throw Error('Invalid document archive entry.')
  const name=new TextDecoder().decode(bytes.subarray(at+46,at+46+nameLength))
  if(/\.html?$/i.test(name))html.push({flags:view.getUint16(at+8,true),method:view.getUint16(at+10,true),compressed:view.getUint32(at+20,true),size:view.getUint32(at+24,true),local:view.getUint32(at+42,true)})
  at=next
 }
 if(html.length!==1)throw Error('Document export did not contain one unambiguous HTML document.')
 const row=html[0],local=row.local
 if(row.flags&1||row.size>TEXT_LIMIT||local+30>offset||view.getUint32(local,true)!==0x04034b50)throw Error('Unsupported or oversized document HTML entry.')
 const data=local+30+view.getUint16(local+26,true)+view.getUint16(local+28,true)
 if(data+row.compressed>offset)throw Error('Invalid document HTML range.')
 const compressed=bytes.subarray(data,data+row.compressed)
 const plain=row.method===0?compressed:row.method===8?await bounded(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('deflate-raw')),TEXT_LIMIT):undefined
 if(!plain||plain.length!==row.size)throw Error('Document HTML decompression was incomplete.')
 return new TextDecoder('utf-8',{fatal:true}).decode(plain)
}
export async function fetchDocument(endpoint,format,{offset=0,expectedSha256}={}){
 if(!Number.isInteger(offset)||offset<0)throw Error('Use a nonnegative document offset.')
 // Extension host permissions permit this authenticated export across Google's
 // redirect hosts; an injected page fetch would be constrained by page CORS.
 const response=await fetch(endpoint,{credentials:'include',signal:AbortSignal.timeout(12000)})
 if(!response.ok)throw Error('Document export readback returned HTTP '+response.status)
 if(response.url&&new URL(response.url).hostname==='accounts.google.com')throw Error('The selected document export requires sign-in.');
 const bytes=await bounded(response.body,DOWNLOAD_LIMIT),text=await decodeDocument(bytes,format)
 if(format==='html'&&bytes[0]!==80&&!response.headers.get('content-disposition'))throw Error('The HTML response was not a document attachment. Verify sign-in and document access.');
 if(/^\s*<!doctype html/i.test(text)&&format==='txt')throw Error('Google returned a sign-in/error page instead of document text.')
 const contentSha256=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))].map(byte=>byte.toString(16).padStart(2,'0')).join('')
 if(expectedSha256!==undefined&&expectedSha256!==contentSha256)throw Error('The saved export changed between pages. Read again before claiming verification.')
 if(offset>text.length)throw Error('The document offset exceeds its current content.')
 let end=Math.min(text.length,offset+65536)
 // JSON permits lone surrogates, but keep a normal emoji whole across pages.
 if(end<text.length&&text.charCodeAt(end-1)>=0xD800&&text.charCodeAt(end-1)<=0xDBFF)end--
 return {ok:true,offset,totalCharacters:text.length,...(end<text.length?{nextOffset:end}:{}),contentSha256,contentType:response.headers.get('content-type'),bytes:bytes.length,text:text.slice(offset,end),verification:'Exported saved document content. Compare the requested text or styles; input acknowledgement alone is not verification.'}
}
