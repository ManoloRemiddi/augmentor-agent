// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual MX user-manager qualification. Opt in only with a real private user bus.
import test from 'node:test';import assert from 'node:assert/strict';
import {spawn,fork,execFile} from 'node:child_process';import {once} from 'node:events';import {promisify} from 'node:util';
import {open,mkdtemp,writeFile,readFile,rm,stat,readdir} from 'node:fs/promises';
import {join} from 'node:path';import {tmpdir} from 'node:os';import {fileURLToPath} from 'node:url';
import {createLinuxOfficeScratch} from '../dist/runtime/src/office-scratch-linux.js';
import {createLinuxManagedOfficeConverter} from '../dist/runtime/src/office-process-linux.js';
import {officeProcessScope} from '../dist/runtime/src/office-process-scope.js';
import {processFileReceipt} from '../dist/runtime/src/office-process-files.js';
import {processRequest,OFFICE_PROCESS_SCHEMA as schema} from '../dist/runtime/src/office-process-protocol.js';
import {processIdentity,signalOwned,stillOwned} from './fixtures/native-office-processes.mjs';
import {previewDocx} from './fixtures/preview-office.mjs';
const skip=process.platform!=='linux'||process.arch!=='x64'||process.env.AUGMENTOR_MANAGED_OFFICE_TEST!=='1';
const run=promisify(execFile),pause=ms=>new Promise(r=>setTimeout(r,ms));
const helper=fileURLToPath(new URL('../dist/runtime/src/office-process-linux.py',import.meta.url));
async function until(fn,label,max=10000){const end=Date.now()+max;while(Date.now()<end){if(await fn())return;await pause(10);}throw Error(label);}
async function fixture(t,{timeoutMs=1000,actor='hang',memory,expectedUnit,unbounded=false}={}){
 const control=await mkdtemp(join(tmpdir(),'augmentor-office-managed-')),scratch=await createLinuxOfficeScratch(),root=await open(scratch.directory,'r'),publication=await open(join(scratch.directory,'converted.pdf'),'wx+',0o600),pub=await publication.stat({bigint:true});
 const scope=await officeProcessScope(timeoutMs);let child,closed,output='',stderr='';
 const worker=join(control,'actor.py');await writeFile(worker,`import os,json,pathlib,time\npacket=json.loads(os.read(0,65536))\ngroup='/sys/fs/cgroup'+pathlib.Path('/proc/self/cgroup').read_text().strip().split('::',1)[1]\npathlib.Path('/proc/self/fd/198/started').write_text(json.dumps({'pid':os.getpid(),'ppid':os.getppid(),'group':group,'limits':{n:pathlib.Path(group,n).read_text().strip() for n in ['memory.max','memory.swap.max','memory.oom.group','cpu.max','pids.max']}}))\n${actor==='memory'?"while not pathlib.Path('/proc/self/fd/198/allocate').exists():time.sleep(.01)\nchunks=[]\nfor _ in range(256):\n chunks.append(bytearray(1024*1024));time.sleep(.001)\n":"while True:time.sleep(1)\n"}`);
 await writeFile(join(scratch.directory,'source.docx'),'AUTHORED',{mode:0o600});
 const packet=processRequest({schema,request:{extension:'docx',input:await processFileReceipt(join(scratch.directory,'source.docx'),20),publication:{dev:String(pub.dev),ino:String(pub.ino)}},options:{timeoutMs}});
 // Retain only this fixture's failed unit for independent OOM Result evidence.
 let args=scope.args.filter(a=>a!=='--collect');if(memory)args=args.map(a=>a.startsWith('--property=MemoryMax=')?'--property=MemoryMax='+memory:a);
 if(unbounded)args=args.filter(a=>!a.startsWith('--property=MemoryMax='));
 t.after(async()=>{if(child?.exitCode===null&&child.signalCode===null)child.kill('SIGKILL');if(closed)await closed;await run('/usr/bin/systemctl',['--user','stop',scope.unit],{env:{...process.env,...scope.env}}).catch(()=>{});await run('/usr/bin/systemctl',['--user','reset-failed',scope.unit],{env:{...process.env,...scope.env}}).catch(()=>{});await publication.close();await root.close();await scratch.dispose();await rm(control,{recursive:true,force:true});});
 return {scratch,scope,start(){child=spawn(scope.executable,[...args,'/usr/bin/python3','-I','-B',helper,String(process.pid),scratch.directory,String(scratch.identity.dev),String(scratch.identity.ino),'/usr/bin/python3',worker,expectedUnit??scope.unit],{env:{PATH:'/usr/bin:/bin',HOME:process.env.HOME,LANG:'C.UTF-8',...scope.env},stdio:['pipe','pipe','pipe',root.fd,publication.fd]});child.stdin.on('error',()=>{});child.stdout.on('data',b=>output+=b);child.stderr.on('data',b=>stderr+=b);closed=once(child,'close');child.stdin.end(JSON.stringify(packet));return child;},async ready(){let info;await until(async()=>{assert.equal(child.exitCode,null,output+stderr);try{info=JSON.parse(await readFile(join(scratch.directory,'started'),'utf8'));return true;}catch{return false;}},'managed actor admission');return info;},async finish(){await closed;return {child,output,stderr,frames:output.trim()?output.trim().split('\n').map(JSON.parse):[]};}};
}
test('MX scope preserves supervisor parent/descriptors and enforces actual cgroup controls before actor admission',{skip,timeout:15000},async t=>{
 const f=await fixture(t,{timeoutMs:500}),child=f.start(),info=await f.ready(),actor=await processIdentity(info.pid);assert.equal(info.ppid,child.pid);assert.equal(info.limits['memory.max'],'3221225472');assert.equal(info.limits['memory.swap.max'],'0');assert.equal(info.limits['memory.oom.group'],'1');assert.equal(info.limits['pids.max'],'128');assert.equal(info.limits['cpu.max'],'100000 100000');assert(info.group.endsWith('/'+f.scope.unit));
 const membership=(await readFile('/proc/'+child.pid+'/cgroup','utf8')).trim();assert.equal('/sys/fs/cgroup'+membership.slice(3),info.group);for(const [key,value] of Object.entries(info.limits))assert.equal((await readFile(join(info.group,key),'utf8')).trim(),value);t.diagnostic(JSON.stringify({case:'admission',limits:info.limits}));
 const end=await f.finish();assert.equal(end.child.exitCode,0,end.stderr);assert.equal(end.frames.at(-1).error.code,'timeout');assert.equal(await stillOwned(actor),false);
});
test('MX managed admission refuses a wrong scope and missing effective memory cap without parser work',{skip,timeout:15000},async t=>{
 for(const options of [{expectedUnit:'augmentor-office-'+'0'.repeat(32)+'.scope'},{unbounded:true}]){
  const f=await fixture(t,{timeoutMs:1000,...options});f.start();const result=await f.finish();assert.equal(result.frames.length,1,result.stderr);assert.equal(result.frames[0].error.code,'failed');await assert.rejects(stat(join(f.scratch.directory,'started')),e=>e.code==='ENOENT');
 }
});
test('MX external manager deadline terminates a stopped supervisor and stopped actor without owner intervention',{skip,timeout:15000},async t=>{
 const f=await fixture(t,{timeoutMs:700}),child=f.start(),info=await f.ready(),actor=await processIdentity(info.pid),guard=await processIdentity(child.pid);
 await signalOwned(actor,'SIGSTOP');await signalOwned(guard,'SIGSTOP');const end=await f.finish();await until(async()=>!await stillOwned(actor),'scope actor terminated');assert(end.frames.filter(f=>f.type==='result').every(f=>f.error),'manager termination cannot produce successful conversion metadata');
 const {stdout}=await run('/usr/bin/systemctl',['--user','show',f.scope.unit,'--property=Result'],{env:{...process.env,...f.scope.env}});assert.equal(stdout.trim(),'Result=timeout');
 t.diagnostic(JSON.stringify({case:'frozen-supervisor-renderer',managerResult:'timeout',successfulTerminalFrames:0}));
});
test('MX manager terminates admitted work while the actual Node owner, supervisor and renderer are all stopped',{skip,timeout:15000},async t=>{
 const control=await mkdtemp(join(tmpdir(),'augmentor-office-managed-owner-'));await writeFile(join(control,'actor.mjs'),"import {readFileSync,writeFileSync} from 'node:fs';readFileSync(0);writeFileSync('/proc/self/fd/198/started','ready');setInterval(()=>{},1000);");
 const owner=fork(new URL('./fixtures/office-process-owner.mjs',import.meta.url),[control,'700','managed'],{stdio:['ignore','ignore','pipe','ipc']});let ready,stderr='';owner.stderr.on('data',b=>stderr+=b);owner.on('message',m=>{if(m.phase==='ready')ready=m;});const ended=once(owner,'close');
 t.after(async()=>{if(owner.exitCode===null&&owner.signalCode===null){owner.kill('SIGCONT');owner.kill('SIGKILL');}await ended;await rm(control,{recursive:true,force:true});});
 await until(()=>{assert.equal(owner.exitCode,null,stderr);return ready;},'managed owner admission');
 const actor=await processIdentity(ready.actor.pid),guard=await processIdentity(ready.guard),ownerToken=await processIdentity(owner.pid);assert.equal(actor.start,ready.actor.start);
 await signalOwned(actor,'SIGSTOP');await signalOwned(guard,'SIGSTOP');await signalOwned(ownerToken,'SIGSTOP');
 await until(async()=>!await stillOwned(actor),'actor terminated while owner stays stopped');await until(async()=>!await stillOwned(guard)||(await processIdentity(guard.pid))?.state==='Z','guard terminated while owner stays stopped');assert.equal((await processIdentity(owner.pid)).state,'T');
 owner.kill('SIGCONT');await ended;assert.equal(owner.exitCode,0,stderr);await assert.rejects(stat(ready.root),e=>e.code==='ENOENT');
 t.diagnostic(JSON.stringify({case:'frozen-owner-supervisor-renderer',ownerStillStoppedAtActorExit:true,rootAbsentAfterOwnerResume:true}));
});
test('MX memory kernel control kills the whole authored allocation group at a lower diagnostic cap',{skip,timeout:15000},async t=>{
 const f=await fixture(t,{timeoutMs:5000,actor:'memory',memory:64*1024**2}),child=f.start(),info=await f.ready(),actor=await processIdentity(info.pid);assert.equal(info.limits['memory.max'],String(64*1024**2));await writeFile(join(f.scratch.directory,'allocate'),'GO',{mode:0o600});
 const end=await f.finish();assert.notEqual(end.child.exitCode,0);await until(async()=>!await stillOwned(actor),'OOM actor terminated');const {stdout}=await run('/usr/bin/systemctl',['--user','show',f.scope.unit,'--property=Result','--property=MemoryPeak'],{env:{...process.env,...f.scope.env}});const report=Object.fromEntries(stdout.trim().split('\n').map(line=>line.split('=')));assert.equal(report.Result,'oom-kill');assert(Number(report.MemoryPeak)>0);assert.equal(end.frames.filter(f=>f.type==='result').length,0);t.diagnostic(JSON.stringify({case:'lower-cap-kernel-oom',memoryMaxBytes:64*1024**2,managerResult:report.Result,memoryPeakBytes:Number(report.MemoryPeak)}));
});
test('actual managed Wasm disposal joins active and queued work, then a fresh converter recovers',{skip,timeout:30000},async t=>{
 const converter=await createLinuxManagedOfficeConverter();t.after(()=>converter.dispose());
 const a=await converter.createScratch(),b=await converter.createScratch();for(const [root,marker] of [[a,'MANAGED_ACTIVE'],[b,'MANAGED_QUEUED']])await writeFile(join(root.directory,'source.docx'),previewDocx(marker,'Liberation Sans'),{mode:0o600});
 const render=root=>converter.render({inputPath:join(root.directory,'source.docx'),outputPath:join(root.directory,'converted.pdf')}).then(value=>({value}),error=>({error}));
 const first=render(a),second=render(b);await until(async()=>{const dirs=await readdir(join(a.directory,'entry-temp')).catch(()=>[]);return dirs.some(n=>n.startsWith('publication-'));},'actual managed entry started');
 await converter.dispose();assert((await first).error);assert((await second).error);for(const root of [a,b]){await root.dispose();await assert.rejects(stat(root.directory),e=>e.code==='ENOENT');}
 const recovery=await createLinuxManagedOfficeConverter();t.after(()=>recovery.dispose());const root=await recovery.createScratch();await writeFile(join(root.directory,'source.docx'),previewDocx('MANAGED_RECOVERY','Liberation Sans'),{mode:0o600});const result=await recovery.render({inputPath:join(root.directory,'source.docx'),outputPath:join(root.directory,'converted.pdf')});assert.deepEqual(result.missingFonts,[]);assert.equal((await readFile(join(root.directory,'converted.pdf'))).subarray(0,5).toString(),'%PDF-');await root.dispose();
});
