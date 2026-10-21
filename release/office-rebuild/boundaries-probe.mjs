// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Synthetic, contained original-provider diagnostic. Not an installed sandbox.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {createHash} from 'node:crypto';
import {join} from 'node:path';

assert.equal(process.platform,'linux');assert.equal(process.version,'v24.19.0');
assert.equal(process.cwd(),'/work');
const {unzipSync,zipSync,strFromU8,strToU8}=createRequire('/app/package.json')('fflate');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const {PiOfficePreview}=await import('/app/dist/runtime/src/office-preview.js');
const {PiFilePreview}=await import('/app/dist/runtime/src/file-preview.js');
const {discoverRuntime}=await import('/app/dist/runtime/vendor/office-entry/index.js');
assert.equal((await discoverRuntime()).backend,'wasm');
const engineName=process.env.PROBE_ENGINE==='thin'?'@augmentor/office-engine-wasm':'@deepseek-ai/libreoffice-kit-wasm';
const enginePackage=JSON.parse(await readFile('/app/node_modules/'+engineName+'/package.json','utf8'));
const originalDoc=await readFile('/fixtures/authored.docx'),originalSheet=await readFile('/fixtures/authored.xlsx');
const manifest=JSON.parse(await readFile('/fixtures/fixtures.json','utf8'));
for(const [extension,bytes] of [['docx',originalDoc],['xlsx',originalSheet]])assert.equal(sha(bytes),manifest.fixtures.find(row=>row.extension===extension).sha256);
const doc=unzipSync(originalDoc),sheet=unzipSync(originalSheet),picture=doc['word/media/image1.png'];assert(picture?.length);
for(const name of ['fixtures','outside','pdfs'])await mkdir('/work/'+name,{mode:0o700});
const canaryImage='/work/outside/only-on-host.png',canaryText='/work/outside/only-on-host.txt';
const fileMarker='HOST_FILE_CANARY_MUST_STAY_OUTSIDE';await writeFile(canaryImage,picture);await writeFile(canaryText,fileMarker);
assert.deepEqual(readFileSync(canaryImage),Buffer.from(picture));assert.equal(readFileSync(canaryText,'utf8'),fileMarker);
let requests=0;const networkMarker='NETWORK_CANARY_MUST_STAY_OUTSIDE';
const server=createServer((request,response)=>{requests++;response.writeHead(200,{'Content-Type':request.url==='/picture'?'image/png':'text/plain'});response.end(request.url==='/picture'?picture:networkMarker);});
server.listen(0,'127.0.0.1');await once(server,'listening');
const origin='http://127.0.0.1:'+server.address().port;
assert.equal(await fetch(origin+'/calibration').then(r=>r.text()),networkMarker);assert.equal(requests,1);requests=0;
const reader=new PiFilePreview(),reads=[],processSeat=process.env.PROBE_PROCESS_BOUNDARY==='2'?await import('./supervised-observer.mjs'):process.env.PROBE_PROCESS_BOUNDARY==='1'?await import('./process-converter.mjs'):undefined;
const provider=new PiOfficePreview((scope,kind,params,signal)=>{reads.push({kind,path:params.path});return reader.read(scope.workspaceRoot,kind,params,signal);},processSeat?.createProcessConverter);
const scope={sessionId:'contained-office-boundaries',workspaceRoot:'/work/fixtures'};
const results=[];const watchdog=setTimeout(()=>{console.error('Contained diagnostic watchdog expired');process.exit(2);},180_000);
const text=part=>strFromU8(part),xml=s=>strToU8(s),zip=parts=>Buffer.from(zipSync(parts,{level:6}));
const replace=(value,from,to)=>{assert(value.includes(from),from);return value.replace(from,to);};
function externalImage(target){
 const parts={...doc};let count=0;
 parts['word/_rels/document.xml.rels']=xml(text(parts['word/_rels/document.xml.rels']).replace(/Target="media\/image1.png"/g,()=>{count++;return 'Target="'+target+'" TargetMode="External"';}));
 assert.equal(count,3);delete parts['word/media/image1.png'];return zip(parts);
}
function field(target){
 const parts={...doc},instruction=' INCLUDETEXT "'+target+'" ';
 const paragraph='<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve">'+instruction+'</w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>CACHED_FIELD_VALUE</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>';
 parts['word/document.xml']=xml(replace(text(parts['word/document.xml']),'<w:body>','<w:body>'+paragraph));return zip(parts);
}
function declaredOversize(){
 const bytes=zip(doc),end=bytes.lastIndexOf(Buffer.from([0x50,0x4b,0x05,0x06]));assert(end>=0);
 let cursor=bytes.readUInt32LE(end+16),patched=false;
 while(bytes.readUInt32LE(cursor)===0x02014b50){
  const size=bytes.readUInt16LE(cursor+28),name=bytes.subarray(cursor+46,cursor+46+size).toString();
  if(name==='word/document.xml'){
   const local=bytes.readUInt32LE(cursor+42);bytes.writeUInt32LE(251*1024*1024,cursor+24);bytes.writeUInt32LE(251*1024*1024,local+22);patched=true;break;
  }
  cursor+=46+size+bytes.readUInt16LE(cursor+30)+bytes.readUInt16LE(cursor+32);
 }
 assert(patched);return bytes;
}
async function idle(){const end=Date.now()+12_000;while(provider.busy){assert(Date.now()<end,'Actual provider teardown must settle');await new Promise(r=>setTimeout(r,20));}}
async function run(name,bytes,{reject=false,images,required='AUGMENTOR_AUTHORED_NATIVE'}={}){
 const path=join(scope.workspaceRoot,name);await writeFile(path,bytes,{flag:'wx',mode:0o600});const started=performance.now();let outcome;
 try {
  const result=await provider.render(scope,{path},new AbortController().signal);assert(!reject,'Over-limit input was accepted');
  assert.equal(Buffer.from(result.data).subarray(0,5).toString(),'%PDF-');
  const pdf='pdfs/'+name+'.pdf';await writeFile('/work/'+pdf,result.data,{flag:'wx',mode:0o600});
  outcome={name,accepted:true,pdf,pdfSha256:sha(result.data),required,images,forbidden:[fileMarker,networkMarker]};
 }catch(error){
  if(!reject)throw error;
  assert.equal(error.code,'document-render/failed');assert.equal(error.details?.reason,'invalid-document');
  outcome={name,accepted:false,reason:error.details.reason};
 }
 await idle();assert.deepEqual(await readFile(path),Buffer.from(bytes));assert.equal(requests,0,'Document tried to access the live HTTP canary');
 results.push({...outcome,inputSha256:sha(bytes),sourceBytesUnchanged:true,observedMs:performance.now()-started,memoryCurrentBytes:Number(await readFile('/sys/fs/cgroup/memory.current','utf8'))});
 await writeFile('/work/progress.json',JSON.stringify(results,null,2)+'\n');
}
try {
 await run('embedded-control.docx',originalDoc,{images:3});
 await run('http-image.docx',externalImage(origin+'/picture'),{images:0});
 await run('file-image.docx',externalImage('file://'+canaryImage),{images:0});
 await run('file-field.docx',field('file://'+canaryText),{images:3,required:'CACHED_FIELD_VALUE'});
 await run('http-field.docx',field(origin+'/text'),{images:3,required:'CACHED_FIELD_VALUE'});
 const linked={...sheet};linked['xl/worksheets/sheet2.xml']=xml(replace(text(linked['xl/worksheets/sheet2.xml']),'Numbers!D5/2','WEBSERVICE(&quot;'+origin+'/formula&quot;)'));
 await run('webservice.xlsx',zip(linked),{images:0,required:'RICH_SECOND_SHEET'});
 await run('declared-oversize.docx',declaredOversize(),{reject:true});
 const many={...doc};for(let n=0;n<10_001-Object.keys(doc).length;n++)many['bounded-entry-'+n+'.txt']=new Uint8Array();
 await run('too-many-entries.docx',zip(many),{reject:true});
 // Abort only after a converter thread actually opens its Wasm, not while a
 // fake wait or authorized source stat is pending. Retain teardown until idle.
 const cancelParts={...doc};cancelParts['word/document.xml']=xml(replace(text(cancelParts['word/document.xml']),'RICH_WRITER_PAGE_1','CANCEL_DISTINCT_DOCUMENT'));
 const cancelBytes=zip(cancelParts),cancelPath=join(scope.workspaceRoot,'cancel-startup.docx');await writeFile(cancelPath,cancelBytes);
 const controller=new AbortController(),before=(await readFile('/work/trace.log','utf8')).length;
 let settled=false;
 const pending=provider.render(scope,{path:cancelPath},controller.signal).then(()=>{settled=true;return {completed:true};},error=>{settled=true;return {error};});
 const end=Date.now()+12_000;let observed=false;
 while(!observed){
  assert(!settled&&Date.now()<end,'Observe a real converter Wasm open before cancellation');
  const trace=(await readFile('/work/trace.log','utf8')).slice(before);
  observed=trace.split('\n').some(line=>line.includes('soffice.wasm')&&line.includes('O_RDONLY')&&/\)\s+=\s+\d+$/.test(line)&&Number(line.match(/^\d+/)?.[0])!==process.pid);
  if(!observed)await new Promise(r=>setTimeout(r,10));
 }
 assert(provider.busy);controller.abort();const outcome=await pending;assert.equal(outcome.error?.code,'gateway/cancelled');await idle();
 assert.deepEqual(await readFile(cancelPath),cancelBytes);results.push({name:'cancel-startup.docx',realConverterWasmOpenObserved:true,reason:outcome.error.code,teardownSettled:true,sourceBytesUnchanged:true});
 const recoveryParts={...doc};recoveryParts['word/document.xml']=xml(replace(text(recoveryParts['word/document.xml']),'RICH_WRITER_PAGE_1','RECOVERY_AFTER_REAL_CANCEL'));
 await run('after-cancel.docx',zip(recoveryParts),{images:3,required:'RECOVERY_AFTER_REAL_CANCEL'});
 assert.deepEqual(readFileSync(canaryImage),Buffer.from(picture));assert.equal(readFileSync(canaryText,'utf8'),fileMarker);
 await provider.close();assert(!provider.busy);assert.equal(requests,0);
 const cgroup={};for(const name of ['memory.max','memory.peak','memory.swap.max','memory.events','cpu.max','pids.max','pids.peak'])cgroup[name]=(await readFile('/sys/fs/cgroup/'+name,'utf8')).trim();
 assert.equal(cgroup['memory.max'],'3221225472');assert.equal(cgroup['memory.swap.max'],'0');assert.equal(cgroup['cpu.max'],'100000 100000');assert.equal(cgroup['pids.max'],'128');
 assert(Number(cgroup['memory.peak'])<=Number(cgroup['memory.max']));assert.match(cgroup['memory.events'],/oom_kill 0(?:\n|$)/);
 const temporary=await readdir('/tmp');assert(!temporary.some(name=>name.startsWith('dsh-office-to-pdf-')||name.startsWith('libreoffice-kit-')||name.startsWith('libreoffice-convert-')));
 const renderers=processSeat?.rendererProcesses??[],lookupHelpers=processSeat?.lookupHelpers??[];assert(renderers.every(row=>row.closed)&&lookupHelpers.every(row=>row.closed));
 await writeFile('/work/result.json',JSON.stringify({schema:'augmentor-office-contained-boundaries/1',probeSha256:sha(readFileSync(new URL(import.meta.url))),engine:enginePackage.name+'@'+enginePackage.version,driverPid:process.pid,canaryPort:server.address().port,positiveHttpCalibrationRequests:1,documentHttpCanaryRequests:requests,canaryImageAndTextUnchanged:true,expectedDriverCanaryReadsEach:2,authorizedReaderCalls:reads.length,cases:results,cgroup,providerIdleAfterClose:true,conversionScratchAbsent:true,diagnosticProcessBoundary:!!processSeat,rendererProcesses:renderers,lookupHelpers,installedSandboxQualified:false,publicRedistributionQualified:false},null,2)+'\n',{flag:'wx',mode:0o600});
}finally{clearTimeout(watchdog);await provider.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
