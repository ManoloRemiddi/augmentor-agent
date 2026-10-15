// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Compare independent authored fixtures through the original provider; no model or app owner.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import sharp from 'sharp';

const [thinArgument,baselineArgument,outputArgument,...extra]=process.argv.slice(2);
if(!thinArgument||!baselineArgument||!outputArgument||extra.length)
  throw Error('Usage: compare-thin-candidate.mjs THIN_APP BASELINE_APP NEW_OUTPUT');
assert.equal(process.platform,'linux');assert.equal(process.arch,'x64');assert.equal(process.version,'v24.19.0');
const root=fileURLToPath(new URL('../..',import.meta.url)),thin=await fs.realpath(thinArgument),baseline=await fs.realpath(baselineArgument),output=path.resolve(outputArgument);
const outputs=await fs.realpath(path.join(root,'outputs'));
assert.equal(path.dirname(output),outputs);assert.equal(await fs.realpath(path.dirname(output)),outputs);
async function absent(p){try{await fs.lstat(p);throw Error('Refusing existing output or sealed release: '+p);}catch(e){if(e.code!=='ENOENT')throw e;}}
await absent(output);for(const app of [thin,baseline]){
  assert(!path.relative(outputs,app).startsWith('..')&&app!==outputs,'Use private ordinary outputs/ apps');
  assert(!app.startsWith(output+path.sep));await absent(path.join(app,'desktop-release.json'));
}
const sha=bytes=>createHash('sha256').update(bytes).digest('hex'),exec=promisify(execFile);
const environment=Object.fromEntries(Object.entries(process.env).filter(([key])=>!['AUGMENTOR_','DSH_','PI_'].some(prefix=>key.startsWith(prefix))));
const run=async (program,args,timeout=60000)=>exec(program,args,{cwd:root,env:environment,timeout,maxBuffer:8*1024*1024});
await fs.mkdir(output,{mode:0o700});
async function probe(app,name,options){
  const destination=path.join(output,name);
  try{const result=await run(process.execPath,[path.join(root,'release/office-rebuild/source-entry-probe.mjs'),app,destination,...options],120000);
    await fs.writeFile(path.join(output,name+'.log'),result.stdout+'\n'+result.stderr,{flag:'wx',mode:0o600});
  }catch(error){await fs.writeFile(path.join(output,name+'-failure.log'),String(error)+'\n'+(error.stdout??'')+'\n'+(error.stderr??''),{flag:'wx',mode:0o600});throw error;}
  return JSON.parse(await fs.readFile(path.join(destination,'result.json'),'utf8'));
}
const left=await probe(thin,'thin',['--thin']);
const right=await probe(baseline,'baseline',['--fixtures',path.join(output,'thin/fixtures')]);
const formats=[],rasters=[];assert.equal(left.formats.length,6);assert.equal(right.formats.length,6);
for(let i=0;i<6;i++){
  const a=left.formats[i],b=right.formats[i],extension=a.extension;
  assert.equal(extension,b.extension);assert.equal(a.inputSha256,b.inputSha256);assert.deepEqual(a.missingFonts,b.missingFonts);
  assert.deepEqual(a.missingFonts,extension==='docx'?['Augmentor Authored Missing Font']:[]);
  for(const item of [a,b]){assert.equal(item.actualTextMarker,true);assert.equal(item.sourceBytesPreserved,true);assert.equal(item.cachedResultOwned,true);}
  const texts=[],pageCounts=[];
  for(const name of ['thin','baseline']){
    const pdf=path.join(output,name,extension+'.pdf'),raster=path.join(output,name,'raster');await fs.mkdir(raster,{recursive:true,mode:0o700});
    texts.push((await run('pdftotext',['-layout',pdf,'-'])).stdout);
    const info=(await run('pdfinfo',[pdf])).stdout,match=info.match(/^Pages:\s+(\d+)$/m);assert(match,'Missing PDF page count');pageCounts.push(Number(match[1]));
    await run('pdftoppm',['-r','96','-png',pdf,path.join(raster,extension)]);
  }
  assert.equal(texts[0],texts[1]);assert.equal(pageCounts[0],pageCounts[1]);
  const pageFiles=[];for(const name of ['thin','baseline'])pageFiles.push((await fs.readdir(path.join(output,name,'raster'))).filter(n=>new RegExp('^'+extension+'-\\d+\\.png$').test(n)).sort());
  assert.deepEqual(pageFiles[0],pageFiles[1]);assert.equal(pageFiles[0].length,pageCounts[0]);
  for(const name of pageFiles[0]){
    const a=await sharp(path.join(output,'thin/raster',name)).raw().toBuffer({resolveWithObject:true});
    const b=await sharp(path.join(output,'baseline/raster',name)).raw().toBuffer({resolveWithObject:true});
    assert.deepEqual(a.info,b.info);assert(a.data.equals(b.data),'Rendered pixel difference: '+name);
    rasters.push({name,width:a.info.width,height:a.info.height,channels:a.info.channels,rawPixelSha256:sha(a.data),identical:true});
  }
  formats.push({extension,inputSha256:a.inputSha256,pages:pageCounts[0],identicalText:true,identicalMissingFonts:true,sourceBytesPreserved:true,cachedResultOwned:true,
    thinPdfSha256:a.pdfSha256,baselinePdfSha256:b.pdfSha256});
}
const result={schema:'augmentor-thin-office-authored-parity/1',thinEntry:left.entryVersion,thinEngine:left.explicitCompatibleWasmPackage,baselineEntry:right.entryVersion,
  baselineEngine:right.explicitCompatibleWasmPackage,coreCommit:left.engineCoreCommit,originalProvider:true,formats,rasterDpi:96,rasters,
  scope:'Six independently authored basic fixtures; equal pixels are not representative document, font, performance, security, platform or distribution acceptance.',
  productionOrInstalledArtifactsChanged:false,publicRedistributionQualified:false};
await fs.writeFile(path.join(output,'comparison.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx',mode:0o600});
console.log(JSON.stringify({formats:formats.length,pages:rasters.length,rasterDpi:96,identicalPixels:true,publicRedistributionQualified:false}));
