// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Paired authored-rich-fixture diagnostic through the actual original Office provider.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import sharp from 'sharp';

const [thinArg,baselineArg,fixtureArg,outputArg,...extra]=process.argv.slice(2);
if(!thinArg||!baselineArg||!fixtureArg||!outputArg||extra.length)
  throw Error('Usage: compare-rich-candidate.mjs THIN_APP BASELINE_APP AUTHORED_FIXTURES NEW_OUTPUT');
assert.equal(process.platform,'linux');assert.equal(process.arch,'x64');assert.equal(process.version,'v24.19.0');
const root=fileURLToPath(new URL('../..',import.meta.url)),outputs=await fs.realpath(path.join(root,'outputs'));
const thin=await fs.realpath(thinArg),baseline=await fs.realpath(baselineArg),fixtures=await fs.realpath(fixtureArg),output=path.resolve(outputArg);
assert.equal(path.dirname(output),outputs);assert.equal(await fs.realpath(path.dirname(output)),outputs);
async function absent(p){try{await fs.lstat(p);throw Error('Output exists or app is sealed; refuse: '+p);}catch(error){if(error.code!=='ENOENT')throw error;}}
await absent(output);
for(const app of [thin,baseline]){
  assert(app.startsWith(outputs+path.sep)&&app!==output&&!app.startsWith(output+path.sep));
  await absent(path.join(app,'desktop-release.json'));
}
assert(fixtures.startsWith(outputs+path.sep)&&fixtures!==output&&!fixtures.startsWith(output+path.sep));
const manifest=JSON.parse(await fs.readFile(path.join(fixtures,'fixtures.json'),'utf8'));
assert.equal(manifest.schema,'augmentor-rich-office-fixtures/1');
assert.deepEqual(manifest.fixtures.map(row=>row.extension),['doc','docx','xls','xlsx','ppt','pptx']);
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
for(const row of manifest.fixtures){
  assert.equal(row.file,'authored.'+row.extension);
  const file=path.join(fixtures,row.file),stat=await fs.lstat(file);
  assert(stat.isFile()&&!stat.isSymbolicLink());assert(stat.size>0&&stat.size<=20*1024*1024);
  assert.equal(stat.size,row.bytes);assert.equal(sha(await fs.readFile(file)),row.sha256);
}
const exec=promisify(execFile),environment=Object.fromEntries(Object.entries(process.env).filter(([key])=>
  !['AUGMENTOR_','DSH_','PI_'].some(prefix=>key.startsWith(prefix))));
const run=(program,args,timeout=60000)=>exec(program,args,{cwd:root,env:environment,timeout,maxBuffer:8*1024*1024});
await fs.mkdir(output,{mode:0o700});
async function probe(app,name,options){
  const start=performance.now();
  try{
    const result=await run(process.execPath,['--max-old-space-size=2048',path.join(root,'release/office-rebuild/source-entry-probe.mjs'),
      app,path.join(output,name),'--fixtures',fixtures,...options],180000);
    await fs.writeFile(path.join(output,name+'.log'),result.stdout+'\n'+result.stderr,{flag:'wx',mode:0o600});
  }catch(error){
    await fs.writeFile(path.join(output,name+'-failure.log'),String(error)+'\n'+(error.stdout??'')+'\n'+(error.stderr??''),{flag:'wx',mode:0o600});
    throw error;
  }
  return {result:JSON.parse(await fs.readFile(path.join(output,name,'result.json'),'utf8')),elapsedMs:performance.now()-start};
}
const left=await probe(thin,'thin',['--thin']),right=await probe(baseline,'baseline',[]),cases=[],rasters=[];
assert.equal(left.result.formats.length,6);assert.equal(right.result.formats.length,6);
for(let index=0;index<6;index++){
  const specification=manifest.fixtures[index],extension=specification.extension;
  const a=left.result.formats[index],b=right.result.formats[index];
  for(const item of [a,b]){
    assert.equal(item.extension,extension);assert.equal(item.inputSha256,specification.sha256);
    assert.equal(item.sourceBytesPreserved,true);assert.equal(item.cachedResultOwned,true);
  }
  assert.deepEqual(a.missingFonts,b.missingFonts,'Different missing-font report: '+extension);
  const summaries=[];
  for(const name of ['thin','baseline']){
    const pdf=path.join(output,name,extension+'.pdf'),raster=path.join(output,name,'raster');
    await fs.mkdir(raster,{recursive:true,mode:0o700});
    const text=(await run('pdftotext',['-layout',pdf,'-'])).stdout;
    const normalized=text.replace(/\s+/g,' ');
    for(const marker of specification.requiredText)assert(normalized.includes(marker),name+'/'+extension+' loses '+marker);
    for(const marker of specification.absentText)assert(!normalized.includes(marker),name+'/'+extension+' exposes '+marker);
    const pageCount=Number((await run('pdfinfo',[pdf])).stdout.match(/^Pages:\s+(\d+)$/m)?.[1]);
    assert(Number.isSafeInteger(pageCount)&&pageCount>=specification.minimumPages&&pageCount<=12,'Unexpected page count: '+extension);
    const imageList=(await run('pdfimages',['-list',pdf])).stdout;
    const imageCount=imageList.split('\n').filter(line=>/^\s*\d+\s+\d+\s+image\s/.test(line)).length;
    assert(imageCount>=specification.minimumImages,'Embedded authored images lost: '+name+'/'+extension);
    await run('pdftoppm',['-r','96','-png',pdf,path.join(raster,extension)]);
    const pages=(await fs.readdir(raster)).filter(n=>new RegExp('^'+extension+'-\\d+\\.png$').test(n)).sort();
    assert.equal(pages.length,pageCount);
    await fs.writeFile(path.join(output,name,extension+'-text.txt'),text,{flag:'wx',mode:0o600});
    summaries.push({text,pageCount,imageCount,pages});
  }
  assert.equal(summaries[0].text,summaries[1].text,'PDF text differs: '+extension);
  assert.equal(summaries[0].pageCount,summaries[1].pageCount,'Page count differs: '+extension);
  assert.equal(summaries[0].imageCount,summaries[1].imageCount,'Image count differs: '+extension);
  assert.deepEqual(summaries[0].pages,summaries[1].pages);
  for(const page of summaries[0].pages){
    const a=await sharp(path.join(output,'thin/raster',page)).raw().toBuffer({resolveWithObject:true});
    const b=await sharp(path.join(output,'baseline/raster',page)).raw().toBuffer({resolveWithObject:true});
    assert.deepEqual(a.info,b.info);assert(a.data.equals(b.data),'Rendered pixel difference: '+page);
    rasters.push({name:page,...a.info,rawPixelSha256:sha(a.data),identical:true});
  }
  assert.equal(sha(await fs.readFile(path.join(fixtures,specification.file))),specification.sha256);
  cases.push({extension,kind:specification.kind,inputSha256:specification.sha256,pages:summaries[0].pageCount,
    images:summaries[0].imageCount,requiredTextVerified:specification.requiredText,absentTextVerified:specification.absentText,
    identicalText:true,identicalMissingFonts:true,missingFonts:a.missingFonts,sourceUnchanged:true,ownedCacheBytes:true,
    thinPdfSha256:a.pdfSha256,baselinePdfSha256:b.pdfSha256});
}
const result={schema:'augmentor-rich-office-parity/1',thinEntry:left.result.entryVersion,thinEngine:left.result.explicitCompatibleWasmPackage,
  baselineEntry:right.result.entryVersion,baselineEngine:right.result.explicitCompatibleWasmPackage,originalProvider:true,cases,rasters,rasterDpi:96,
  thinProbeElapsedMs:left.elapsedMs,baselineProbeElapsedMs:right.elapsedMs,
  scope:'Six authored rich Office files through actual provider; semantic/text/page/image/font/cache/byte/pixel checks. Timings are one observed sequential pair, not performance acceptance.',
  originalGuiExercised:false,ownerProfilesOrDocumentsUsed:false,modelRequests:0,engineBuildsStarted:0,installedChanges:0,publicRedistributionQualified:false};
await fs.writeFile(path.join(output,'comparison.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx',mode:0o600});
console.log(JSON.stringify({formats:cases.length,pages:rasters.length,identicalPixels:true,semanticChecks:true,originalProvider:true,publicRedistributionQualified:false}));
