// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Deliberately killable/stoppable owner for actual kernel lifecycle faults.
import {spawn} from 'node:child_process';import {once} from 'node:events';
import {open,writeFile,stat} from 'node:fs/promises';import {join} from 'node:path';import {fileURLToPath} from 'node:url';
import {createLinuxOfficeScratch} from '../../dist/runtime/src/office-scratch-linux.js';
import {processFileReceipt} from '../../dist/runtime/src/office-process-files.js';
import {processRequest,OFFICE_PROCESS_SCHEMA as schema} from '../../dist/runtime/src/office-process-protocol.js';
const [control,timeout]=process.argv.slice(2),scratch=await createLinuxOfficeScratch(),root=await open(scratch.directory,'r'),publication=await open(join(scratch.directory,'converted.pdf'),'wx+',0o600),pub=await publication.stat({bigint:true});
await writeFile(join(scratch.directory,'source.docx'),'AUTHORED',{mode:0o600});
const packet=processRequest({schema,request:{extension:'docx',input:await processFileReceipt(join(scratch.directory,'source.docx'),20),publication:{dev:String(pub.dev),ino:String(pub.ino)}},options:{timeoutMs:Number(timeout)}});
const child=spawn('/usr/bin/python3',['-I','-B',fileURLToPath(new URL('../../dist/runtime/src/office-process-linux.py',import.meta.url)),String(process.pid),scratch.directory,String(scratch.identity.dev),String(scratch.identity.ino),process.execPath,join(control,'actor.mjs')],{detached:true,stdio:['pipe','pipe','ignore',root.fd,publication.fd]});
let output='';child.stdin.on('error',()=>{});child.stdout.on('data',b=>output+=b);const closed=once(child,'close');child.stdin.end(JSON.stringify(packet));
const until=async fn=>{const end=Date.now()+5000;while(!await fn()){if(Date.now()>end)throw Error('Fixture readiness expired');await new Promise(r=>setTimeout(r,5));}};
await until(()=>output.includes('"type": "ready"'));
const actor=JSON.parse(output.split('\n').find(s=>s.includes('"type": "ready"'))).actor;
await until(()=>stat(join(scratch.directory,'started')).then(()=>true,()=>false));
process.send({phase:'ready',root:scratch.directory,guard:child.pid,actor});
await closed;await publication.close();await root.close();await scratch.dispose();
process.send({phase:'done',terminal:JSON.parse(output.trim().split('\n').at(-1))},()=>process.disconnect());
