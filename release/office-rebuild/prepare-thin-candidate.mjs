// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Private diagnostic only: never alter a base app, selected release or default dependency.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {build} from 'esbuild';

const root=fileURLToPath(new URL('../..',import.meta.url));
const [baseArgument,cacheArgument,container,outputArgument,...extra]=process.argv.slice(2);
if(!baseArgument||!cacheArgument||!container||!outputArgument||extra.length)
  throw Error('Usage: prepare-thin-candidate.mjs UNSELECTED_APP BUILT_CACHE TERMINAL_CONTAINER NEW_OUTPUT');
assert.equal(process.platform,'linux');assert.equal(process.arch,'x64');assert.equal(process.version,'v24.19.0');
const base=await fs.realpath(baseArgument),cache=await fs.realpath(cacheArgument),output=path.resolve(outputArgument);
const outputs=await fs.realpath(path.join(root,'outputs'));
// TypeScript resolves the root's locked build tools from this private output tree.
assert.equal(await fs.realpath(path.dirname(output)),outputs,'Use a new direct child of repository outputs/');
assert.equal(path.dirname(output),outputs,'Linked output parents are refused');
assert(!path.relative(outputs,base).startsWith('..')&&base!==outputs,'Base must be a private ordinary outputs/ app');
assert(output!==base&&!base.startsWith(output+path.sep),'Output would contain the base app');
async function absent(p){try{await fs.lstat(p);throw Error('Refusing existing output or sealed release: '+p);}catch(e){if(e.code!=='ENOENT')throw e;}}
async function regular(p){assert((await fs.lstat(p)).isFile(),'Regular file required: '+p);return fs.readFile(p);}
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const json=async p=>JSON.parse((await regular(p)).toString('utf8'));
const checkedJson=async p=>{const stat=await fs.lstat(p);assert(stat.isDirectory()&&!stat.isSymbolicLink());};
async function files(directory){const names=[];for(const e of (await fs.readdir(directory,{withFileTypes:true})).sort((a,b)=>a.name.localeCompare(b.name))){
  const p=path.join(directory,e.name);assert(!e.isSymbolicLink(),'Linked source content: '+p);
  if(e.isDirectory())names.push(...await files(p));else{assert(e.isFile());names.push(p);}
}return names;}
await absent(output);await absent(path.join(base,'desktop-release.json'));
for(const part of ['dist','node_modules','node'])await checkedJson(path.join(base,part));
const env=await json(path.join(root,'release/office-rebuild/environment.json'));
const inspected=JSON.parse(execFileSync('docker',['inspect',container],{encoding:'utf8'}))[0];
assert.equal(inspected.State.Status,'exited');assert.equal(inspected.State.ExitCode,0);assert.equal(inspected.State.OOMKilled,false);
assert.equal(inspected.Image,env.builderImageId);assert(inspected.Mounts.some(m=>m.Destination==='/office'&&m.Source===cache));
for(const [key,value] of Object.entries({Memory:8589934592,MemorySwap:8589934592,NanoCpus:2000000000,PidsLimit:1024,NetworkMode:'none',ReadonlyRootfs:true}))assert.equal(inspected.HostConfig[key],value);
const status=await json(path.join(cache,'status-thin.json')),profile=await json(path.join(cache,'thin-resource-profile.json'));
assert.equal(status.phase,'complete');assert.equal(status.stage,'complete');assert.equal(status.memoryMax,'8589934592');assert.equal(status.swapMax,'0');
assert(status.memoryPeakBytes>0&&status.memoryPeakBytes<=8589934592);assert.deepEqual(status.compilerControls,profile.compilerControls);
assert.equal(profile.compilerControls.EMCC_CFLAGS,'-flto=thin');assert.equal(profile.oldCoreBuildObjectsReused,false);
assert.equal(profile.runtimeWasmMemoryThreadFlagsChanged,false);assert.equal(profile.supplierIdentityCapturesCompilerOverride,false);
for(const [name,expected] of [['run-thin-lto.sh',env.thinLtoExperiment.driverSha256],['thin-linker-resources.patch',env.thinLtoExperiment.additionalPatchSha256]]){
  assert.equal(sha(await regular(path.join(cache,name))),expected);assert.equal(sha(await regular(path.join(root,'release/office-rebuild',name))),expected);
}
assert.equal(profile.driverSha256,env.thinLtoExperiment.driverSha256);assert.equal(profile.additionalBuildOnlyPatchSha256,env.thinLtoExperiment.additionalPatchSha256);
const assets=path.join(cache,'dist-thin'),manifest=await json(path.join(assets,'manifest.json'));
assert.equal(manifest.sourceCommit,env.coreCommit);assert.equal(manifest.inputs.source.emsdk.commit,env.emsdkCommit);
assert.equal(execFileSync('git',['rev-parse','HEAD'],{cwd:path.join(cache,'core'),encoding:'utf8'}).trim(),env.coreCommit);
assert.equal(execFileSync('git',['rev-parse','HEAD'],{cwd:path.join(cache,'emsdk'),encoding:'utf8'}).trim(),env.emsdkCommit);
const assetNames=['soffice.cjs','soffice.wasm','soffice.data','soffice.data.js.metadata'];
assert.deepEqual(Object.keys(manifest.files).sort(),assetNames.toSorted());
assert.deepEqual((await fs.readdir(assets)).sort(),['manifest.json',...assetNames].sort());
for(const name of assetNames)assert.equal(sha(await regular(path.join(assets,name))),manifest.files[name]);
const actualDiff=execFileSync('git',['diff','--binary','HEAD','--'],{cwd:path.join(cache,'core'),maxBuffer:8*1024*1024});
// The supplier's run() hashes stdout.trim(), not raw git stdout. Preserve both.
const diffSha=sha(Buffer.from(actualDiff.toString('utf8').trim()));assert.equal(diffSha,manifest.inputs.sourceChanges);
assert.equal(sha(await regular(path.join(cache,'build-thin/autogen.input'))),manifest.inputs.configuration);
assert.equal(manifest.inputs.patches['0032-augmentor-linker-resources.patch'],profile.additionalBuildOnlyPatchSha256);
assert.equal(sha(await regular(path.join(cache,'recipe/engine/wasm-source/patches/0032-augmentor-linker-resources.patch'))),profile.additionalBuildOnlyPatchSha256);
// Validate the exact original entry/engine/source/notices before cloning an allowlist.
execFileSync('python3',['-B','-c',
  "import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('office',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.validate_inputs(Path(sys.argv[2]))",
  path.join(root,'scripts/office_engine.py'),base],{cwd:root,stdio:'inherit'});
const supplier=path.join(base,'node_modules/@deepseek-ai/libreoffice-kit-wasm');
const recipeFiles=await files(path.join(supplier,'sources'));assert.equal(recipeFiles.length,39);
for(const p of recipeFiles){const name=path.relative(path.join(supplier,'sources'),p);assert.equal(sha(await regular(path.join(cache,'recipe',name))),sha(await regular(p)),name);}
const originalSource=path.join(root,'packages/runtime/vendor/office-entry');
const upstream=await json(path.join(originalSource,'UPSTREAM.json'));
assert.equal(upstream.files.length,32);
const preferredFiles=await files(path.join(originalSource,'preferred-source'));assert.equal(preferredFiles.length,32);
for(const row of upstream.files){assert(/^preferred-source\/[a-z0-9-]+(?:\.d)?\.ts$/.test(row.path));assert.equal(sha(await regular(path.join(originalSource,row.path))),row.sha256);}
const engineName='@augmentor/office-engine-wasm',engineVersion='0.1.5-augmentor.thin.1',entryVersion='0.1.3-augmentor.thin.1';
const before=(await regular(path.join(originalSource,'preferred-source/engine.ts'))).toString('utf8');
let after=before;
for(const [from,to] of [["export const ENGINE_VERSION = '0.1.3-augmentor.1'",`export const ENGINE_VERSION = '${entryVersion}'`],
  ["wasm: '0.1.5',",`wasm: '${engineVersion}',`],["const ENGINE_PREFIX = '@deepseek-ai/libreoffice-kit'","const ENGINE_PREFIX = '@augmentor/office-engine'"]]){
  assert.equal(after.split(from).length,2,'Preferred source mapping changed');after=after.replace(from,to);
}
after=after.replace('explicit source-fork identity and tested Linux Wasm package version.','explicit source-fork identity and isolated source-built ThinLTO engine mapping.');
// All validation above is read-only. Everything below writes only this new tree.
await fs.mkdir(output,{mode:0o700});const app=path.join(output,'app'),preferred=path.join(output,'entry-source');await fs.mkdir(app,{mode:0o700});
for(const name of ['dist','node_modules','node','package.json','package-lock.json'])await fs.cp(path.join(base,name),path.join(app,name),{recursive:true,dereference:false});
await fs.cp(originalSource,preferred,{recursive:true});await fs.writeFile(path.join(preferred,'preferred-source/engine.ts'),after);
upstream.version=entryVersion;upstream.modifications.push(`Private Linux-only diagnostic mapping to ${engineName}@${engineVersion}; conversion/font/worker source unchanged.`);
upstream.files.find(row=>row.path==='preferred-source/engine.ts').sha256=sha(Buffer.from(after));
await fs.writeFile(path.join(preferred,'UPSTREAM.json'),JSON.stringify(upstream,null,2)+'\n');
const engine=path.join(app,'node_modules',engineName);await absent(engine);await fs.mkdir(engine,{recursive:true,mode:0o700});
await fs.cp(path.join(supplier,'licenses'),path.join(engine,'licenses'),{recursive:true});await fs.cp(assets,path.join(engine,'assets'),{recursive:true});
const sources=path.join(engine,'sources');await fs.cp(path.join(supplier,'sources'),sources,{recursive:true});
await fs.copyFile(path.join(cache,'recipe/engine/wasm-source/patches/0032-augmentor-linker-resources.patch'),path.join(sources,'engine/wasm-source/patches/0032-augmentor-linker-resources.patch'));
for(const name of ['thin-resource-profile.json','run-thin-lto.sh','thin-linker-resources.patch'])await fs.copyFile(path.join(cache,name),path.join(sources,name));
await fs.copyFile(path.join(cache,'build-thin/autogen.input'),path.join(sources,'build-autogen.input'));await fs.writeFile(path.join(sources,'source-changes.patch'),actualDiff);
await fs.writeFile(path.join(engine,'package.json'),JSON.stringify({name:engineName,version:engineVersion,type:'module',private:true,license:'MPL-2.0',exports:{'./package.json':'./package.json','./prebuilds.json':'./prebuilds.json'}},null,2)+'\n');
const engineFiles={};for(const p of await files(engine))engineFiles[path.relative(engine,p).replaceAll('\\','/')]=sha(await regular(p));
await fs.writeFile(path.join(engine,'prebuilds.json'),JSON.stringify({schemaVersion:1,version:engineVersion,platform:'wasm',status:'built',
  engine:{kind:'wasm',loader:'assets/soffice.cjs',wasm:'assets/soffice.wasm',data:'assets/soffice.data',metadata:'assets/soffice.data.js.metadata',programDirectory:manifest.programPath},files:engineFiles,
  source:{coreCommit:manifest.sourceCommit,supplierBuildId:manifest.buildId,resourceProfileSha256:engineFiles['sources/thin-resource-profile.json'],sourceDiffSha256:diffSha,rawSourceDiffSha256:sha(actualDiff)},
  scope:'Experimental source-built engine; not a public package or redistribution qualification.'},null,2)+'\n');
const entry=path.join(app,'dist/runtime/vendor/office-entry'),types=path.join(output,'types');await fs.rm(entry,{recursive:true});await fs.mkdir(entry);
execFileSync(process.execPath,[path.join(root,'node_modules/typescript/bin/tsc'),'-p',path.join(preferred,'tsconfig.entry.json'),'--outDir',types],{cwd:root,stdio:'inherit'});
assert.equal((await files(types)).filter(p=>p.endsWith('.d.ts')).length,31);
await build({absWorkingDir:root,entryPoints:['index','worker','font-snapshot-worker','cli'].map(name=>path.join(preferred,'preferred-source',name+'.ts')),outdir:entry,bundle:true,packages:'external',platform:'node',format:'esm',target:'node22.19',sourcemap:true,legalComments:'linked'});
for(const name of ['LICENSE','NOTICE','UPSTREAM.json','BUILDING.md','tsconfig.entry.json'])await fs.copyFile(path.join(preferred,name),path.join(entry,name));
await fs.cp(path.join(preferred,'preferred-source'),path.join(entry,'preferred-source'),{recursive:true});await fs.cp(types,entry,{recursive:true});
await fs.writeFile(path.join(entry,'package.json'),JSON.stringify({name:'@augmentor/office-entry',version:entryVersion,type:'module',private:true,license:'MPL-2.0'},null,2)+'\n');
await fs.mkdir(path.join(entry,'build-support'));
for(const [from,to] of [['package.json','package.json'],['package-lock.json','package-lock.json'],['release/office-rebuild/prepare-thin-candidate.mjs','prepare-thin-candidate.mjs'],['apps/harness/package.json','harness-package.json']])await fs.copyFile(path.join(root,from),path.join(entry,'build-support',to));
const toolchain={node:process.version};for(const name of ['typescript','esbuild'])toolchain[name]=(await json(path.join(root,'node_modules',name,'package.json'))).version;
const entryFiles={};for(const p of await files(entry))entryFiles[path.relative(entry,p).replaceAll('\\','/')]=sha(await regular(p));
await fs.writeFile(path.join(entry,'SOURCE.json'),JSON.stringify({schema:'augmentor-experimental-built-office-entry/1',name:upstream.componentName,version:entryVersion,sourceCommit:upstream.commit,sourceArchiveSha256:upstream.archiveSha256,toolchain,files:entryFiles,scope:'Private ThinLTO diagnostic; not the default entry or public source-distribution closure.'},null,2)+'\n');
const record={schema:'augmentor-thin-office-candidate/2',entryVersion,engineName,engineVersion,coreCommit:manifest.sourceCommit,supplierBuildId:manifest.buildId,
  ownResourceProfileSha256:engineFiles['sources/thin-resource-profile.json'],sourceDiffSha256:diffSha,rawSourceDiffSha256:sha(actualDiff),engineAssets:manifest.files,
  originalEntryEngineTsSha256:sha(Buffer.from(before)),adaptedEntryEngineTsSha256:sha(Buffer.from(after)),sourceEntryFiles:32,sourceRecipeFiles:39,additionalRecipePatches:1,toolchain,
  conversionOrFontSourceChanged:false,productionOrInstalledArtifactsChanged:false,defaultDependenciesChanged:false,publicRedistributionQualified:false};
await fs.writeFile(path.join(output,'preparation.json'),JSON.stringify(record,null,2)+'\n');console.log(JSON.stringify(record));
