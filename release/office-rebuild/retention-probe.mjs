// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Attribute retained memory with real providers; no production runtime changes.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {fork} from 'node:child_process';
import {once} from 'node:events';
import {fileURLToPath} from 'node:url';
import v8 from 'node:v8';

assert.equal(process.cwd(),'/work');assert.equal(process.version,'v24.19.0');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function values(text){return Object.fromEntries(text.trim().split('\n').map(row=>{const [key,value]=row.trim().split(/[:\s]+/);return [key,Number(value)];}));}
async function sample(label){
 const proc=values(await readFile('/proc/self/smaps_rollup','utf8').then(s=>s.split('\n').slice(1).join('\n')));
 const cgroup=values(await readFile('/sys/fs/cgroup/memory.stat','utf8'));
 return {label,pid:process.pid,usage:process.memoryUsage(),heap:v8.getHeapStatistics(),code:v8.getHeapCodeStatistics(),
  anonymousKiB:proc.Anonymous,rssKiB:proc.Rss,filePssKiB:proc.Pss_File,
  threads:(await readdir('/proc/self/task')).length,activeResources:process.getActiveResourcesInfo(),
  cgroup:{currentBytes:Number(await readFile('/sys/fs/cgroup/memory.current','utf8')),peakBytes:Number(await readFile('/sys/fs/cgroup/memory.peak','utf8')),anon:cgroup.anon,file:cgroup.file,kernel:cgroup.kernel}};
}
async function render(indices){
 const {PiOfficePreview}=await import('/app/dist/runtime/src/office-preview.js');
 const {PiFilePreview}=await import('/app/dist/runtime/src/file-preview.js');
 const files=new PiFilePreview(),provider=new PiOfficePreview((scope,kind,params,signal)=>files.read(scope.workspaceRoot,kind,params,signal));
 const samples=[await sample('before')],documents=[];
 try {
  for(const index of indices){
   const path='/work/fixtures/'+index+'.docx',before=await readFile(path);
   const result=await provider.render({sessionId:'contained-memory',workspaceRoot:'/work/fixtures'},{path},new AbortController().signal);
   const end=Date.now()+12000;while(provider.busy){assert(Date.now()<end);await sleep(10);}
   assert.deepEqual(await readFile(path),before);const pdf='pdfs/'+index+'.pdf';await writeFile('/work/'+pdf,result.data,{flag:'wx',mode:0o600});
   documents.push({index,inputSha256:sha(before),pdf,pdfSha256:sha(result.data),sourceBytesUnchanged:true});
   samples.push(await sample('after-'+index));
  }
 }finally{await provider.close();}
 assert(!provider.busy);samples.push(await sample('closed'));await sleep(500);samples.push(await sample('idle'));
 assert.equal(typeof global.gc,'function');global.gc();await sleep(50);global.gc();await sleep(50);
 samples.push(await sample('forced-gc-diagnostic-only'));
 return {samples,documents,providerIdleAfterClose:true};
}
async function main(){
 if(process.argv[2]==='worker'){
  const index=Number(process.argv[3]);assert([0,1].includes(index));
  const result=await render([index]);process.send({result});process.disconnect();return;
 }
 const style=process.env.RETENTION_STYLE;assert(['same','fresh'].includes(style));
 const {zipSync,unzipSync,strFromU8,strToU8}=createRequire('/app/package.json')('fflate');
 const bytes=await readFile('/fixtures/authored.docx'),manifest=JSON.parse(await readFile('/fixtures/fixtures.json','utf8'));
 assert.equal(sha(bytes),manifest.fixtures.find(row=>row.extension==='docx').sha256);
 await mkdir('/work/fixtures',{mode:0o700});await mkdir('/work/pdfs',{mode:0o700});
 const doc=unzipSync(bytes);for(const index of [0,1]){
  const parts={...doc},text=strFromU8(parts['word/document.xml']);assert(text.includes('RICH_WRITER_PAGE_1'));
  parts['word/document.xml']=strToU8(text.replace('RICH_WRITER_PAGE_1','RETENTION_DOCUMENT_'+index));
  await writeFile('/work/fixtures/'+index+'.docx',zipSync(parts,{level:6}),{flag:'wx',mode:0o600});
 }
 const parentSamples=[await sample('parent-before')],runs=[];
 if(style==='same')runs.push(await render([0,1]));
 else for(const index of [0,1]){
  const child=fork(fileURLToPath(import.meta.url),['worker',String(index)],{execArgv:['--expose-gc','--max-old-space-size=1536'],stdio:['ignore','pipe','pipe','ipc']});
  let result,stderr='';child.stdout.resume();child.stderr.on('data',bytes=>stderr+=bytes);child.on('message',value=>{assert(!result);result=value.result;});
  const [code,signal]=await once(child,'exit');assert.equal(code,0,stderr);assert.equal(signal,null);assert(result);
  runs.push({...result,childExitObserved:true});parentSamples.push(await sample('parent-after-child-'+index));
 }
 const cgroup={};for(const name of ['memory.max','memory.peak','memory.swap.max','memory.events','cpu.max','pids.max','pids.peak'])cgroup[name]=(await readFile('/sys/fs/cgroup/'+name,'utf8')).trim();
 assert.equal(cgroup['memory.max'],'3221225472');assert.equal(cgroup['memory.swap.max'],'0');assert.equal(cgroup['cpu.max'],'100000 100000');assert.equal(cgroup['pids.max'],'128');assert.match(cgroup['memory.events'],/oom_kill 0(?:\n|$)/);
 await writeFile('/work/result.json',JSON.stringify({schema:'augmentor-office-retention-probe/1',engine:process.env.PROBE_ENGINE,style,probeSha256:sha(await readFile(fileURLToPath(import.meta.url))),runs,parentSamples,cgroup,forcedGcIsDiagnosticOnly:true,installedChanges:0,publicRedistributionQualified:false},null,2)+'\n',{flag:'wx',mode:0o600});
}
const watchdog=setTimeout(()=>{console.error('Retained-memory diagnostic deadline');process.exit(2);},90000);
try{await main();}finally{clearTimeout(watchdog);}
