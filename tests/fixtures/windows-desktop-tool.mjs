// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Explicit Windows qualification invokes the actual registered Pi tool boundary.
import {desktopPackage,control} from '../../dist/desktop/src/index.js';
let raw='';for await(const bytes of process.stdin)raw+=bytes;
const request=JSON.parse(raw);
try{
 let result;
 if(request.method==='status'||request.method==='shutdown')result=await control(request.method,request.owner);
 else{
  const tools=[];desktopPackage(request.owner)({registerTool:tool=>tools.push(tool)});
  const name={connect:'linux_desktop_connect',capture:'linux_desktop_snapshot',action:'linux_desktop_action',stop:'linux_desktop_stop'}[request.method];
  const tool=tools.find(row=>row.name===name);if(!tool)throw Error('Unknown authored tool request');
  const reply=await tool.execute('authored-windows-proof',request.params??{},new AbortController().signal,()=>{},{model:{input:['text','image']}});
  result=JSON.parse(reply.content.find(row=>row.type==='text').text);const image=reply.content.find(row=>row.type==='image');
  if(image)result.image={data:image.data,mimeType:image.mimeType,...result.imageSize};
 }
 process.stdout.write(JSON.stringify({ok:true,result}));
}catch(error){process.stdout.write(JSON.stringify({ok:false,error:error.message}));process.exitCode=1;}
