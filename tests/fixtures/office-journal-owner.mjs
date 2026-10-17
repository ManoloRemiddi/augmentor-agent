// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual separate owner; the test may stop/kill every one of its own processes.
import {writeFile,readFile,readdir,stat} from 'node:fs/promises';import {join} from 'node:path';
import {createLinuxManagedOfficeConverter} from '../../dist/runtime/src/office-process-linux.js';
import {ownedProcesses,processIdentity,signalOwned} from './native-office-processes.mjs';
import {previewDocx} from './preview-office.mjs';
const [state,mode]=process.argv.slice(2),converter=await createLinuxManagedOfficeConverter({},state),scratch=await converter.createScratch();
await writeFile(join(scratch.directory,'source.docx'),mode==='render'?previewDocx('DURABLE_ACTIVE_CONVERSION','Liberation Sans'):'AUTHORED_PRIVATE_SNAPSHOT',{mode:0o600});
let active;
if(mode==='render'){
 void converter.render({inputPath:join(scratch.directory,'source.docx'),outputPath:join(scratch.directory,'converted.pdf')}).catch(()=>{});
 const end=Date.now()+10000;let entered=false;
 while(Date.now()<end){const names=await readdir(join(scratch.directory,'entry-temp')).catch(()=>[]);for(const name of names.filter(n=>n.startsWith('publication-')))if(await stat(join(scratch.directory,'entry-temp',name,'result.pdf')).then(()=>true,()=>false))entered=true;if(entered)break;await new Promise(r=>setTimeout(r,2));}
 if(!entered)throw Error('Real Office entry did not open its output.');
 const record=JSON.parse((await readFile(join(scratch.directory,'actors.jsonl'),'utf8')).trim());const actor=await processIdentity(record.pid);if(actor?.start!==record.start)throw Error('Actual renderer identity lost.');await signalOwned(actor,'SIGSTOP');
 const guard=(await ownedProcesses()).find(p=>p.name==='aug-office-proc');if(!guard)throw Error('No actual renderer supervisor.');active={actor,guard};
}else await writeFile(join(scratch.directory,'converted.pdf'),'%PDF-AUTHORED_PRIVATE_OUTPUT',{mode:0o600});
const cleaner=(await ownedProcesses()).find(p=>p.name==='aug-office-temp');if(!cleaner)throw Error('No actual scratch cleanup owner.');
process.send({directory:scratch.directory,cleaner,...active});
process.on('message',async message=>{if(message==='close'){await scratch.dispose();await converter.dispose();process.disconnect();}});
