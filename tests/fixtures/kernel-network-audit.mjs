// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Test-only Linux syscall observations. No production hook or OS firewall.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {readFile,readdir,mkdir} from 'node:fs/promises';
import {join} from 'node:path';
export async function traceNetwork(command,args,{directory,label,env,cwd}={}){
 assert(/^[a-z][a-z0-9-]*$/.test(label));await mkdir(directory,{recursive:true,mode:0o700});
 const prefix=join(directory,label);assert(!(await readdir(directory)).some(name=>name===label||name.startsWith(label+'.')),'Do not overwrite an earlier trace.');
 const child=spawn('strace',['-ff','-qq','-s','0','-e','trace=connect,sendto,sendmsg,sendmmsg','-o',prefix,command,...args],{env,cwd,stdio:['ignore','pipe','pipe']});let stdout='',stderr='';
 child.stdout.on('data',data=>stdout+=data);child.stderr.on('data',data=>stderr+=data);
 const settled=new Promise((resolve,reject)=>{child.once('error',reject);child.once('close',(code,signal)=>resolve({code,signal}));});
 return {child,settled,get stdout(){return stdout;},get stderr(){return stderr;},async records(){const files=(await readdir(directory)).filter(name=>name.startsWith(label+'.'));assert(files.length,'Kernel tracing produced no task files.');let raw='';const records=[];
  for(const name of files){const pid=Number(name.slice(label.length+1)),text=await readFile(join(directory,name),'utf8');assert(Number.isSafeInteger(pid));raw+=text;
   for(const line of text.split('\n')){
    if(!/^(connect|sendto|sendmsg|sendmmsg)\(/.test(line)||!line.includes('AF_INET'))continue;
    let matched=false;
    for(const row of line.matchAll(/sin_port=htons\((\d+)\), sin_addr=inet_addr\("([^"]+)"\)|sin6_port=htons\((\d+)\),[^}]*inet_pton\(AF_INET6, "([^"]+)"/g)){
     matched=true;records.push({pid,family:row[2]?'ipv4':'ipv6',operation:line.slice(0,line.indexOf('(')),host:row[2]??row[4],port:Number(row[1]??row[3])});
    }
    assert(matched,'Unparsed IP syscall; this trace cannot establish destination coverage.');
   }
  }
  return {records,taskFiles:files.length,raw};
 }};
}
export function unexpectedDestinations(records,allowed){return records.filter(row=>!allowed.some(endpoint=>endpoint.host===row.host&&endpoint.port===row.port));}
