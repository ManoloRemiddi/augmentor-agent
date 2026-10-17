// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Diagnostic-only observation of real supervised processes. No substitute actor.
import {createRequire,syncBuiltinESMExports} from 'node:module';
const require=createRequire('/app/package.json'),children=require('node:child_process'),spawn=children.spawn;
export const rendererProcesses=[];
export const lookupHelpers=[];
children.spawn=function(command,args,options){
 const child=spawn(command,args,options);
 if(command==='/usr/bin/python3'&&args?.[2]==='/app/dist/runtime/src/office-scratch-linux.py'){
  const row={pid:child.pid,kind:'scratch-owner',closed:false};lookupHelpers.push(row);child.once('close',(code,signal)=>{row.closed=code===0&&!signal;});
 }
 if(command==='/usr/bin/python3'&&args?.[2]==='/app/dist/runtime/src/office-process-linux.py'){
  const row={supervisorPid:child.pid,closed:false};rendererProcesses.push(row);let frame=Buffer.alloc(0),size=0,terminal=false,invalid=false;
  child.stdout.on('data',bytes=>{
   size+=bytes.length;if(size>266240){invalid=true;return;}frame=Buffer.concat([frame,bytes]);let end;
   while((end=frame.indexOf(10))>=0){const line=frame.subarray(0,end);frame=frame.subarray(end+1);
    try{const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(line));
     if(value.schema!=='augmentor-office-process/1')throw Error();
     if(value.type==='ready'){if(row.pid||terminal)throw Error();row.pid=value.actor.pid;row.start=value.actor.start;}
     else if(value.type==='result'){if(terminal)throw Error();terminal=true;}else throw Error();
    }catch{invalid=true;}
   }
  });
  child.once('close',(code,signal)=>{row.supervisorExitCode=code;row.supervisorSignal=signal;row.closed=!!row.pid&&code===0&&!signal&&terminal&&!invalid&&!frame.length;});
 }
 return child;
};
syncBuiltinESMExports();
const {createLinuxProcessOfficeConverter}=await import('/app/dist/runtime/src/office-process-linux.js');
export const createProcessConverter=createLinuxProcessOfficeConverter;
