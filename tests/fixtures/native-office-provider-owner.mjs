// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Authored original-provider crash fixture; only its own document and processes.
import {writeFile,mkdir} from 'node:fs/promises';import {join} from 'node:path';
import {PiOfficePreview} from '../../dist/runtime/src/office-preview.js';
import {PiFilePreview} from '../../dist/runtime/src/file-preview.js';
import {createLinuxNativeOfficeConverter} from '../../dist/runtime/src/office-native-linux.js';
import {previewDocx} from './preview-office.mjs';
const root=process.argv[2],workspace=join(root,'workspace');await mkdir(workspace);
const input=join(workspace,'authored.docx');await writeFile(input,previewDocx('AUTHORED_PROVIDER_CRASH_'+ 'x'.repeat(100000)));
if(process.argv[3]==='pre-copy'){
 const converter=await createLinuxNativeOfficeConverter(),scratch=await converter.createScratch();
 await writeFile(join(root,'allocated.json'),JSON.stringify({directory:scratch.directory}));setInterval(()=>{},1000);
}else{
const reader=new PiFilePreview(),provider=new PiOfficePreview((scope,kind,params,signal)=>reader.read(scope.workspaceRoot,kind,params,signal),createLinuxNativeOfficeConverter);
const abort=new AbortController();process.once('SIGUSR1',()=>abort.abort());
setInterval(()=>{},1000);
provider.render({sessionId:'authored-provider-crash',workspaceRoot:workspace},{path:input},abort.signal)
 .then(async()=>{await provider.close();await writeFile(join(root,'settled.json'),JSON.stringify({failed:false}));},async()=>{await provider.close();await writeFile(join(root,'settled.json'),JSON.stringify({failed:true}));});
}
