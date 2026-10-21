// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Build the public-source MPL entry; never substitute opaque npm entry bytes.
import {build} from 'esbuild';
import {readFile,writeFile,mkdir,mkdtemp,rm,cp,readdir,lstat} from 'node:fs/promises';
import {join,relative,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const root=fileURLToPath(new URL('..',import.meta.url)),source=join(root,'packages/runtime/vendor/office-entry'),output=join(root,'dist/runtime/vendor/office-entry');
const action=process.argv[2]??'build';if(!['build','--check','--write-types'].includes(action)||process.argv.length>3)throw Error('Unknown source entry build action.');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex'),upstream=JSON.parse(await readFile(join(source,'UPSTREAM.json'),'utf8'));
for(const row of upstream.files){
 if(!/^preferred-source\/[a-z0-9-]+(?:\.d)?\.ts$/.test(row.path)||!/^[a-f0-9]{64}$/.test(row.sha256))throw Error('Unsafe Office source receipt.');
 const path=join(source,row.path);if(!(await lstat(path)).isFile()||sha(await readFile(path))!==row.sha256)throw Error('Preferred Office entry source changed without its receipt: '+row.path);
}
const temporary=await mkdtemp(join(tmpdir(),'augmentor-office-entry-types-'));
async function files(directory){const rows=[];for(const entry of (await readdir(directory,{withFileTypes:true})).sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:0)){const path=join(directory,entry.name);if(entry.isSymbolicLink())throw Error('Linked Office source/build content.');if(entry.isDirectory())rows.push(...await files(path));else if(entry.isFile())rows.push(path);}return rows;}
const preferred=(await files(join(source,'preferred-source'))).map(path=>relative(source,path).replaceAll('\\','/'));
if(preferred.length!==32||new Set(upstream.files.map(row=>row.path)).size!==32||preferred.some(path=>!upstream.files.some(row=>row.path===path)))throw Error('Office preferred source inventory changed.');
try{
 execFileSync(process.execPath,[join(root,'node_modules/typescript/bin/tsc'),'-p',join(source,'tsconfig.entry.json'),'--outDir',temporary],{cwd:root,stdio:'inherit'});
 const generated=(await files(temporary)).filter(name=>name.endsWith('.d.ts'));if(generated.length!==31)throw Error('Incomplete Office entry declarations.');
 for(const path of generated){const name=relative(temporary,path),target=join(source,name),bytes=await readFile(path);if(action==='--write-types'){await mkdir(dirname(target),{recursive:true});await writeFile(target,bytes);}else if(!bytes.equals(await readFile(target)))throw Error('Office entry declaration differs from preferred source: '+name);}
 if(action==='--check')process.exitCode=0;
 else{
  await rm(output,{recursive:true,force:true});await mkdir(output,{recursive:true});await build({absWorkingDir:root,entryPoints:['index','worker','font-snapshot-worker','cli'].map(name=>join(source,'preferred-source',name+'.ts')),outdir:output,bundle:true,packages:'external',platform:'node',format:'esm',target:'node22.19',sourcemap:true,legalComments:'linked'});
  for(const name of ['LICENSE','NOTICE','UPSTREAM.json','BUILDING.md','tsconfig.entry.json'])await cp(join(source,name),join(output,name));await cp(join(source,'preferred-source'),join(output,'preferred-source'),{recursive:true});
  for(const path of generated){const name=relative(temporary,path);await mkdir(dirname(join(output,name)),{recursive:true});await cp(path,join(output,name));}
  await writeFile(join(output,'package.json'),JSON.stringify({name:upstream.componentName,version:upstream.version,type:'module',private:true,license:upstream.license},null,2)+'\n');
  await mkdir(join(output,'build-support'));for(const name of ['package.json','package-lock.json','scripts/build-office-entry.mjs'])await cp(join(root,name),join(output,'build-support',name.split('/').at(-1)));
  await cp(join(root,'apps/harness/package.json'),join(output,'build-support/harness-package.json'));
  const toolchain={node:process.version,typescript:JSON.parse(await readFile(join(root,'node_modules/typescript/package.json'),'utf8')).version,esbuild:JSON.parse(await readFile(join(root,'node_modules/esbuild/package.json'),'utf8')).version};
  const content={};for(const path of await files(output)){const name=relative(output,path).replaceAll('\\','/');if(name!=='SOURCE.json')content[name]=sha(await readFile(path));}
  await writeFile(join(output,'SOURCE.json'),JSON.stringify({schema:'augmentor-built-office-entry/1',name:upstream.componentName,version:upstream.version,sourceCommit:upstream.commit,sourceArchiveSha256:upstream.archiveSha256,toolchain,files:content,scope:'Source-built adapter; exact engine rebuild and native/platform distribution remain separate.'},null,2)+'\n');
 }
}finally{await rm(temporary,{recursive:true,force:true});}
