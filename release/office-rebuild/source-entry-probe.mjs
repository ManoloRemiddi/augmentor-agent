// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Exercise the original MIT provider over an isolated public-source entry build.
import assert from 'node:assert/strict';
import {mkdir,readFile,writeFile,lstat,copyFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {createHash} from 'node:crypto';
const [appArgument,outputArgument,...options]=process.argv.slice(2);
let thin=false,fixtureArgument;
for(let i=0;i<options.length;i++){
 if(options[i]==='--thin'&&!thin)thin=true;
 else if(options[i]==='--fixtures'&&fixtureArgument===undefined&&options[i+1])fixtureArgument=options[++i];
 else throw Error('Unknown or repeated source-entry probe option.');
}
if(!appArgument||!outputArgument)throw Error('Usage: source-entry-probe.mjs UNSELECTED_APP NEW_OUTPUT [--thin] [--fixtures AUTHORED_FIXTURE_DIRECTORY]');
const app=resolve(appArgument),output=resolve(outputArgument),project=fileURLToPath(new URL('../..',import.meta.url));
const absent=async path=>{try{await lstat(path);throw Error('Refusing an existing output or selected release.');}catch(error){if(error.code!=='ENOENT')throw error;}};
await absent(output);await absent(join(app,'desktop-release.json'));
const entry=join(app,'dist/runtime/vendor/office-entry'),pkg=JSON.parse(await readFile(join(entry,'package.json'),'utf8'));
assert.equal(pkg.name,'@augmentor/office-entry');assert.equal(pkg.version,thin?'0.1.3-augmentor.thin.1':'0.1.3-augmentor.1');assert.equal(pkg.license,'MPL-2.0');
const {discoverRuntime}=await import(pathToFileURL(join(entry,'index.js'))),runtime=await discoverRuntime();assert.equal(runtime.backend,'wasm');
const enginePackage=thin?'@augmentor/office-engine-wasm':'@deepseek-ai/libreoffice-kit-wasm';
const engine=JSON.parse(await readFile(join(app,'node_modules',enginePackage,'package.json'),'utf8'));
assert.equal(engine.name,enginePackage);assert.equal(engine.version,thin?'0.1.5-augmentor.thin.1':'0.1.5');
const engineSource=JSON.parse(await readFile(join(app,'node_modules',enginePackage,'assets/manifest.json'),'utf8'));
const {PiOfficePreview}=await import(pathToFileURL(join(app,'dist/runtime/src/office-preview.js'))),{PiFilePreview}=await import(pathToFileURL(join(app,'dist/runtime/src/file-preview.js')));
await mkdir(output,{mode:0o700});const fixtures=join(output,'fixtures');await mkdir(fixtures,{mode:0o700});
const exec=promisify(execFile);
if(fixtureArgument){
 for(const extension of ['doc','docx','xls','xlsx','ppt','pptx']){
  const source=join(resolve(fixtureArgument),'authored.'+extension);assert((await lstat(source)).isFile());
  await copyFile(source,join(fixtures,'authored.'+extension));
 }
}else await exec('/usr/bin/python3',['-B',join(project,'tests/fixtures/native-office-documents.py'),fixtures],{timeout:60000});
const reader=new PiFilePreview(),provider=new PiOfficePreview((scope,kind,p,signal)=>reader.read(scope.workspaceRoot,kind,p,signal));
const scope={sessionId:'authored-source-entry',workspaceRoot:fixtures},formats=[],sha=bytes=>createHash('sha256').update(bytes).digest('hex');
try{
 for(const extension of ['doc','docx','xls','xlsx','ppt','pptx']){
  const path=join(fixtures,'authored.'+extension),before=await readFile(path),result=await provider.render(scope,{path},new AbortController().signal);
  assert(Buffer.from(result.data).subarray(0,5).equals(Buffer.from('%PDF-')));assert.deepEqual(await readFile(path),before);
  const pdf=join(output,extension+'.pdf');await writeFile(pdf,result.data,{flag:'wx',mode:0o600});const {stdout}=await exec('/usr/bin/pdftotext',[pdf,'-'],{timeout:10000});assert(stdout.includes('AUGMENTOR_AUTHORED_NATIVE'),extension+' loses the authored content');
  const cached=await provider.render(scope,{path},new AbortController().signal);assert.deepEqual(cached.data,result.data);assert.notStrictEqual(cached.data,result.data);assert.deepEqual(await readFile(path),before);
  formats.push({extension,inputSha256:sha(before),pdfSha256:sha(result.data),pdfBytes:result.data.byteLength,missingFonts:result.missingFonts,actualTextMarker:true,sourceBytesPreserved:true,cachedResultOwned:true});
  console.log(JSON.stringify(formats.at(-1)));
 }
}finally{await provider.close();}
assert.equal(provider.busy,false);
const record={schema:'augmentor-public-source-entry-preview-probe/2',entryVersion:pkg.version,backend:runtime.backend,platform:process.platform,arch:process.arch,node:process.version,sourceCommit:'b19bb73c74ed893b8a5d1716d32df32a113ed31b',engineCoreCommit:engineSource.sourceCommit,explicitCompatibleWasmPackage:engine.name+'@'+engine.version,originalProvider:true,formats,ownerConfigurationOrHistoryUsed:false,installationContractQualified:false,engineRebuildQualified:false,publicRedistributionQualified:false};
await writeFile(join(output,'result.json'),JSON.stringify(record,null,2)+'\n',{flag:'wx',mode:0o600});
