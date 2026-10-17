// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// One original Wasm entry operation, owned by the Linux supervisor.
import {readSync,writeSync,fstatSync} from 'node:fs';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {discoverRuntime,createConverter} from '../vendor/office-entry/index.js';
import {OFFICE_PROCESS_SCHEMA,OFFICE_PROCESS_REQUEST_BYTES,OFFICE_PROCESS_ERRORS,processRequest,processReply,type ProcessReply} from './office-process-protocol.js';
import {processFileReceipt as receipt,processFileData} from './office-process-files.js';
let converter:Awaited<ReturnType<typeof createConverter>>|undefined,reply:ProcessReply,privateOutput:string|undefined;
try{
 if(process.platform!=='linux'||process.env.AUGMENTOR_OFFICE_SUPERVISED!=='1')throw Error('Unsupervised Office renderer.');
 const bytes=Buffer.alloc(OFFICE_PROCESS_REQUEST_BYTES+1);let used=0;
 for(;;){const n=readSync(0,bytes,used,bytes.length-used,null);if(!n)break;used+=n;if(used>=bytes.length)throw Error('Oversized Office request.');}
 const request=processRequest(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(0,used))));
 const input='/proc/self/fd/198/source.'+request.request.extension,output='/proc/self/fd/198/converted.pdf';
 const publication=()=>{const info=fstatSync(199,{bigint:true});if(!info.isFile()||info.uid!==BigInt(process.getuid!())||Number(info.mode&0o777n)!==0o600||String(info.dev)!==request.request.publication.dev||String(info.ino)!==request.request.publication.ino||info.nlink!==1n)throw Error('Changed Office publication descriptor.');return info;};
 if(publication().size!==0n)throw Error('Office publication is not empty.');
 const sourceUnchanged=async()=>{try{if(JSON.stringify(await receipt(input,request.options.maxInputBytes!,undefined,request.request.input))===JSON.stringify(request.request.input))return;}catch{}throw Object.assign(Error('Office source identity changed.'),{code:'source-changed'});};
 await sourceUnchanged();
 if((await discoverRuntime()).backend!=='wasm')throw Error('Office process backend must be Wasm.');
 privateOutput=await mkdtemp(join(tmpdir(),'publication-'));converter=await createConverter(request.options);const result=await converter.render({inputPath:input,outputPath:join(privateOutput,'result.pdf')});
 await sourceUnchanged();
 const rendered=await processFileData(join(privateOutput,'result.pdf'),request.options.maxOutputBytes!);
 if(rendered.data.subarray(0,5).toString()!=='%PDF-'||publication().size!==0n)throw Error('Invalid Office publication.');
 let at=0;while(at<rendered.data.length){const n=writeSync(199,rendered.data,at,rendered.data.length-at,at);if(!n)throw Error('Office publication write failed.');at+=n;}
 publication();const published=await receipt(output,request.options.maxOutputBytes!,undefined,request.request.publication);
 if(published.sha256!==rendered.receipt.sha256)throw Error('Changed Office publication bytes.');
 reply=processReply({schema:OFFICE_PROCESS_SCHEMA,type:'result',missingFonts:result.missingFonts,output:published});
}catch(error){const code=typeof error==='object'&&error!==null&&'code' in error&&typeof error.code==='string'&&OFFICE_PROCESS_ERRORS.has(error.code)?error.code:'failed';reply={schema:OFFICE_PROCESS_SCHEMA,type:'result',error:{code}};}
finally{try{await converter?.dispose();if(privateOutput)await rm(privateOutput,{recursive:true,force:true});}catch{reply={schema:OFFICE_PROCESS_SCHEMA,type:'result',error:{code:'failed'}};}}
process.stdout.write(JSON.stringify(processReply(reply!))+'\n');
