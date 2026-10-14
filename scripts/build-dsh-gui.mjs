// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createRequire} from 'node:module';
import {copyFileSync,readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync,rmSync,mkdtempSync} from 'node:fs';
import {join, resolve, dirname,isAbsolute} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {relativeBuildInput,spreadsheetOverlayResolver} from './harness-build-resolution.mjs';
const root=resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ui=join(root,'apps/harness'),vendor=join(ui,'vendor/dsh');
const provenance=JSON.parse(readFileSync(join(vendor,'SOURCE.json'),'utf8'));
for(const entry of provenance.files){if(createHash('sha256').update(readFileSync(join(vendor,entry.path))).digest('hex')!==entry.sha256)throw Error('DSH source differs from reviewed public selection: '+entry.path);}
const brandVendor=join(ui,'vendor/augmentor-brand'),brandSource=JSON.parse(readFileSync(join(brandVendor,'SOURCE.json'),'utf8'));
for(const entry of brandSource.files){if(createHash('sha256').update(readFileSync(join(brandVendor,entry.path))).digest('hex')!==entry.sha256)throw Error('Augmentor brand differs from reviewed public selection: '+entry.path);}
const fileReferenceVendor=join(root,'packages/runtime/vendor/dsh-file-reference'),fileReferenceSource=JSON.parse(readFileSync(join(fileReferenceVendor,'SOURCE.json'),'utf8'));
for(const entry of fileReferenceSource.files){if(createHash('sha256').update(readFileSync(join(fileReferenceVendor,entry.path))).digest('hex')!==entry.sha256)throw Error('DSH file-reference source differs from reviewed public selection: '+entry.path);}
const officeVendor=join(root,'packages/runtime/vendor/dsh-office'),officeSource=JSON.parse(readFileSync(join(officeVendor,'SOURCE.json'),'utf8'));
for(const entry of officeSource.files){if(createHash('sha256').update(readFileSync(join(officeVendor,entry.path))).digest('hex')!==entry.sha256)throw Error('DSH Office source differs from reviewed public selection: '+entry.path);}
const contextVendor=join(ui,'vendor/dsh-context'),contextSource=JSON.parse(readFileSync(join(contextVendor,'SOURCE.json'),'utf8'));
for(const entry of contextSource.files){if(createHash('sha256').update(readFileSync(join(contextVendor,entry.path))).digest('hex')!==entry.sha256)throw Error('dsh-context source differs from reviewed selection: '+entry.path);}
const metafolderVendor=join(ui,'vendor/dsh-metafolder'),metafolderSource=JSON.parse(readFileSync(join(metafolderVendor,'SOURCE.json'),'utf8'));
for(const entry of metafolderSource.files){if(createHash('sha256').update(readFileSync(join(metafolderVendor,entry.path))).digest('hex')!==entry.sha256)throw Error('Metafolder source differs from the reviewed selection: '+entry.path);}
const requireUi=createRequire(join(ui,'package.json'));
const searchVendor=join(ui,'vendor/dsh-web-search-free'),searchSource=JSON.parse(readFileSync(join(searchVendor,'SOURCE.json'),'utf8'));
for(const entry of searchSource.files){if(createHash('sha256').update(readFileSync(join(searchVendor,entry.path))).digest('hex')!==entry.sha256)throw Error('Free Search card differs from the reviewed public selection: '+entry.path);}
const pdfRoot=dirname(requireUi.resolve('pdfjs-dist/package.json'));
if(JSON.parse(readFileSync(join(pdfRoot,'package.json'),'utf8')).version!=='6.3.289')throw Error('PDF.js differs from the reviewed DSH lock.');
// Port the original PDF build's local resource/notice recipe. Asset bytes stay
// in the deferred PDF chunk; no viewer CDN, font fetch or parser worker fallback.
const pdfAssets={},pdfAssetRecords=[];
for(const [kind,folder] of [['cMapUrl','cmaps'],['standardFontDataUrl','standard_fonts'],['wasmUrl','wasm']]){
 pdfAssets[kind]={};for(const name of readdirSync(join(pdfRoot,folder)).filter(name=>!name.startsWith('LICENSE')).sort()){
  const bytes=readFileSync(join(pdfRoot,folder,name));pdfAssets[kind][name]=bytes.toString('base64');pdfAssetRecords.push({kind,name,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')});
 }
}
const pdfNotices=['LICENSE',...['cmaps','standard_fonts','wasm'].flatMap(folder=>readdirSync(join(pdfRoot,folder)).filter(name=>name.startsWith('LICENSE')).sort().map(name=>folder+'/'+name))];
const {compile}=requireUi('@tailwindcss/node'),{Scanner}=requireUi('@tailwindcss/oxide');
const tailwindPath=join(contextVendor,'src/client/styles/tailwind.css');
const compiler=await compile(readFileSync(tailwindPath,'utf8'),{base:dirname(tailwindPath),onDependency:()=>{}});
const contextUtilities=compiler.build(new Scanner({sources:compiler.sources}).scan());
const {build}=createRequire(join(ui,'package.json'))('esbuild');
// The public prompt-section function has type-only Cordis/config imports. Its
// separate Node graph must contain that one source and no supplier Host runtime.
const promptSupplier=await build({absWorkingDir:root,entryPoints:[join(contextVendor,'src/host/promptInjection.ts')],outfile:join(root,'dist/runtime/vendor/dsh-context-prompt.js'),bundle:true,format:'esm',platform:'node',target:'node24',metafile:true,legalComments:'eof'});
if(Object.keys(promptSupplier.metafile.inputs).length!==1||Object.values(promptSupplier.metafile.outputs).some(output=>output.imports.length))throw Error('Unexpected runtime dependency in original prompt section registration.');
copyFileSync(join(contextVendor,'LICENSE'),join(root,'dist/runtime/vendor/dsh-context-LICENSE.txt'));
writeFileSync(join(root,'dist/runtime/vendor/dsh-context-SOURCE.json'),JSON.stringify({repository:contextSource.repository,commit:contextSource.commit,version:contextSource.version,license:contextSource.license,copyright:contextSource.copyright,files:contextSource.files.filter(row=>row.path==='src/host/promptInjection.ts'),build:promptSupplier.metafile},null,2)+'\n');
// Reproduce the public baseline's exact FortuneSheet/ExcelJS patches in private
// build-local overlays. Workspace modules and selected releases stay untouched.
const spreadsheetOverlay=mkdtempSync(join(tmpdir(),'augmentor-spreadsheet-overlay-')),spreadsheetPatches=[],spreadsheetEntries=new Map(),spreadsheetOrigins=new Map();
for(const [name,version,patchName] of [['@fortune-sheet/core','1.0.4','@fortune-sheet__core@1.0.4.patch'],['@fortune-sheet/react','1.0.4','@fortune-sheet__react@1.0.4.patch'],['exceljs','4.4.0','exceljs@4.4.0.patch']]){
 const original=dirname(requireUi.resolve(name+'/package.json')),meta=JSON.parse(readFileSync(join(original,'package.json'),'utf8')),patch=join(vendor,'patches',patchName),body=readFileSync(patch,'utf8'),overlay=join(spreadsheetOverlay,'node_modules',name);
 if(meta.version!==version)throw Error('Spreadsheet patch package differs: '+name);
 const paths=[...body.matchAll(/^diff --git a\/(\S+) b\/(\S+)$/gm)].map(match=>{if(match[1]!==match[2]||match[1].startsWith('/')||match[1].split('/').includes('..'))throw Error('Unsafe spreadsheet patch path.');return match[1];});
 for(const section of body.split(/^diff --git /m).slice(1)){const path=section.match(/^a\/(\S+) b\//)?.[1],index=section.match(/^index ([a-f0-9]+)\.\.([a-f0-9]+)/m);if(!path||!index)throw Error('Spreadsheet patch source identity is unavailable.');const bytes=readFileSync(join(original,path)),blob=createHash('sha1').update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');if(!blob.startsWith(index[1]))throw Error('Spreadsheet patch source body differs: '+name+'/'+path);}
 spreadsheetOrigins.set(overlay,original);mkdirSync(overlay,{recursive:true});for(const path of new Set(['package.json',...paths,...readdirSync(original).filter(name=>/^(license|notice)([.\-_]|$)/i.test(name))])){const target=join(overlay,path);mkdirSync(dirname(target),{recursive:true});copyFileSync(join(original,path),target);}
 execFileSync('git',['apply','--check',patch],{cwd:overlay});execFileSync('git',['apply',patch],{cwd:overlay});
 const patchedMeta=JSON.parse(readFileSync(join(overlay,'package.json'),'utf8')),entry=name==='exceljs'?patchedMeta.browser:patchedMeta.module;
 if(typeof entry!=='string')throw Error('Spreadsheet patched browser entry is unavailable.');spreadsheetEntries.set(name,join(overlay,entry));
 spreadsheetPatches.push({name,version,patch:'patches/'+patchName,patchSha256:createHash('sha256').update(body).digest('hex'),files:paths.map(path=>({path,sourceSha256:createHash('sha256').update(readFileSync(join(original,path))).digest('hex'),sha256:createHash('sha256').update(readFileSync(join(overlay,path))).digest('hex')}))});
}
const spreadsheetResolver=spreadsheetOverlayResolver(spreadsheetEntries,spreadsheetOrigins);
// Port the original isolated parser build; its graph participates in notices and
// remains outside the application's initial module closure.
const excelWorker=await build({absWorkingDir:root,entryPoints:[join(vendor,'packages/client/ui-sidebar-documentpreview/src/client/excel/worker.ts')],outfile:join(root,'dist/harness-web/dsh-excel-worker-0.2.1-alpha.2.mjs'),bundle:true,format:'esm',platform:'browser',target:'chrome120',minify:true,metafile:true,legalComments:'eof',write:false,nodePaths:[join(ui,'node_modules'),join(root,'node_modules')],plugins:[spreadsheetResolver],mainFields:['browser','module','main'],define:{'process.env.NODE_ENV':'"production"'}});
if(excelWorker.outputFiles.length!==1||Object.values(excelWorker.metafile.outputs).some(output=>output.imports.length))throw Error('Spreadsheet parser must be one self-contained local worker.');
const packages=new Map();
for(const family of readdirSync(join(vendor,'packages'))){
  for(const name of readdirSync(join(vendor,'packages',family))){
    const directory=join(vendor,'packages',family,name),file=join(directory,'package.json');
    if(existsSync(file))packages.set(JSON.parse(readFileSync(file,'utf8')).name,directory);
  }
}
const pinnedPublicResolver={name:'pinned-public-dsh',setup(b){
    b.onResolve({filter:/^@dsh-metafolder$/},()=>({path:join(metafolderVendor,'client.js'),namespace:'metafolder'}));
    b.onLoad({filter:/.*/,namespace:'metafolder'},args=>({contents:'import React from \"react\";\nexport default (function(React){\n'+readFileSync(args.path,'utf8')+'\n})(React);',loader:'js',resolveDir:ui}));
    b.onResolve({filter:/^(\.\.\/historyPage|\.\/historyPage|\.\.\/modelPrices)$/},args=>relativeBuildInput(contextVendor,args.importer)!==undefined?{path:join(ui,'dsh-context-boundary.mjs')}:undefined);
    b.onResolve({filter:/\?inline$/},args=>({path:requireUi.resolve(args.path.slice(0,-7)),namespace:'raw'}));
    b.onResolve({filter:/\?raw$/},args=>({path:args.path.startsWith('.')?resolve(dirname(args.importer),args.path.slice(0,-4)):requireUi.resolve(args.path.slice(0,-4)),namespace:'raw'}));
    b.onLoad({filter:/.*/,namespace:'raw'},args=>({contents:readFileSync(args.path,'utf8'),loader:'text'}));
    b.onLoad({filter:/ui-sidebar-documentpreview\/src\/client\/pdf\/assets\.ts$/},args=>({contents:'const __DSH_PDFJS_ASSETS__ = '+JSON.stringify(pdfAssets)+';\n'+readFileSync(args.path,'utf8'),loader:'ts'}));
    b.onLoad({filter:/vendor\/dsh-context\/src\/client\/styles\/tailwind\.css$/},()=>({contents:contextUtilities,loader:'css'}));
    b.onResolve({filter:/^@dsh-gui\//},args=>({path:join(vendor,'packages/client',args.path.slice(9))}));
    b.onResolve({filter:/^@deepseek-ai\//},args=>{
      const parts=args.path.split('/'),name=parts.slice(0,2).join('/'),sub=parts.slice(2).join('/');
      const directory=packages.get(name);
      if(!directory)throw Error('Unselected DSH package: '+args.path);
      let target=sub==='client'?'src/client/index.ts':sub?'src/'+sub+'.ts':'src/index.ts';
      if(sub.startsWith('src/'))target=sub;
      const path=join(directory,target);
      if(!existsSync(path))throw Error('Unselected DSH export: '+args.path+' → '+path);
      return {path};
    });
  }};
// Shared pure shortcut protocol runs on the Host without a Cordis/native service.
const shortcutSupplier=await build({absWorkingDir:root,entryPoints:[join(vendor,'packages/client/shortcuts/src/protocol.ts')],outfile:join(root,'dist/runtime/vendor/dsh-shortcuts.js'),bundle:true,format:'esm',platform:'node',target:'node24',metafile:true,legalComments:'eof',plugins:[pinnedPublicResolver]});
const shortcutInputs=Object.keys(shortcutSupplier.metafile.inputs);
if(shortcutInputs.some(path=>!/^apps\/harness\/vendor\/dsh\/packages\/(?:client\/shortcuts\/src\/(?:binding|configuration|persistence|native|protocol)\.ts|util\/(?:crypto|values)\/src\/index\.ts|util\/values\/src\/partial-json\.ts)$/.test(path))||Object.values(shortcutSupplier.metafile.outputs).some(output=>output.imports.length))throw Error('Unexpected shortcut runtime dependency.');
const shortcutRuntime={repository:provenance.repository,commit:provenance.commit,license:'MIT',files:provenance.files.filter(row=>shortcutInputs.includes('apps/harness/vendor/dsh/'+row.path)),bundle:{name:'dsh-shortcuts.js',sha256:createHash('sha256').update(readFileSync(join(root,'dist/runtime/vendor/dsh-shortcuts.js'))).digest('hex')},build:shortcutSupplier.metafile};
copyFileSync(join(vendor,'LICENSE'),join(root,'dist/runtime/vendor/dsh-shortcuts-LICENSE.txt'));
writeFileSync(join(root,'dist/runtime/vendor/dsh-shortcuts-SOURCE.json'),JSON.stringify(shortcutRuntime,null,2)+'\n');
const result=await build({
  absWorkingDir:root,entryPoints:[join(ui,'dsh-app.jsx')],outdir:join(root,'dist/harness-web'),
  entryNames:'dsh-gui',bundle:true,format:'esm',platform:'browser',target:'chrome120',
  jsx:'automatic',minify:false,metafile:true,legalComments:'eof',splitting:true,chunkNames:'[name]-[hash]',write:false,
  nodePaths:[join(ui,'node_modules'),join(root,'node_modules')],loader:{'.woff2':'file','.woff':'file','.ttf':'file','.png':'file','.svg':'dataurl'},
  define:{'__DSH_CTX_VERSION__':'"0.68.1"','process.env.NODE_ENV':'"production"','process.env.DSH_CLIENT_TITLE':'"Augmentor Harness"','process.env.DSH_CLIENT_VERSION':'"0.2.13"','process.env.DSH_CLIENT_COMMIT_HASH':'undefined','process.env.DSH_CLIENT_GIT_DIRTY':'"false"'},
  plugins:[spreadsheetResolver,pinnedPublicResolver],
});
const allBrowserInputs=[...new Set([...Object.keys(result.metafile.inputs),...Object.keys(excelWorker.metafile.inputs)])];
const forbidden=allBrowserInputs.filter(path=>/vendor\/dsh\/.*(?:client-runtime|product-analytics|ui-settings-account|ui-settings-session-log|packages\/host)|vendor\/dsh-context\/(?:src\/host|src\/client\/(?:modelPrices|historyPage|latestVersion|settingsJump|balance|skills))|node_modules\/(?:@deepseek-ai\/cordis|@opencode-ai\/models|posthog|@sentry)/.test(path));
if(forbidden.length)throw Error('Supplier runtime/analytics entered the browser graph: '+forbidden.join(', '));
const npmRoots=new Map();
for(const name of allBrowserInputs){
  if(!name.includes('node_modules/'))continue;
  const sourcePath=name.startsWith('raw:')?name.slice(4):name;
  let directory=dirname(isAbsolute(sourcePath)?sourcePath:join(root,sourcePath));
  while(directory!==root&&(!existsSync(join(directory,'package.json'))||!JSON.parse(readFileSync(join(directory,'package.json'),'utf8')).name))directory=dirname(directory);
  if(directory===root)throw Error('No supplier manifest for browser input: '+name);
  const manifest=JSON.parse(readFileSync(join(directory,'package.json'),'utf8'));
  npmRoots.set(directory,manifest);
}
const licenses=[readFileSync(join(vendor,'LICENSE'),'utf8'),'\nAdditional original DSH PDF selection: registration, page/text/zoom and tab-lifetime source reused at the same public MIT ref. The marked PDF runtime uses a reviewed same-origin module worker instead of Blob creation, preserving the application CSP and original worker lifecycle. PDF.js and bundled CMap/font/decoder data retain their separate notices below; Liberation data carries GPL-2.0/font-exception terms. Public binary/source/rebuild qualification remains separate.\n','\n--- dsh-context 0.68.1 · Copyright 2025 bowenliang123 · Apache-2.0 ---\n'+readFileSync(join(contextVendor,'LICENSE'),'utf8')+'\nModified by Augmentor: Pi read-only data/history bindings; automatic registry/price lookups and unbound DSH settings removed; unattested DSH threshold removed; unobserved skill/fleet figures marked unavailable; original request selector binds explicit metadata paging/body reads with unavailable-data notes; original slash modal binds the same read-only picker and recorded-data notice; original Insights uses bounded Pi metadata/newest-body reads and reported SDK usage buckets, with unavailable skills/prices/detailed timing explicit and DSH backfill disabled; tooltip identity is captured outside state updaters to prevent focus/measurement loops; original settings card keeps unsupported Pi fields disabled; original sidebar/placement registrations use Pi UI-only slots, independent dock scroll identity/root and a served-family navigation gate. Original Fleet widgets bind exact-parent Pi job identities, scoped head/detail caches and narrower read-only child links; optional reported disposition/request and composition availability fields prevent inferred success or zero occupancy. Team/mailbox and active-time data remain unavailable. The verbatim public prompt-section registration is separately transpiled for a Pi request-time registry seat; literal prefix/suffix preserve existing system/tool state and recorded revisions without Cordis or another agent owner. Original/adapted source hashes and modification notices are recorded in SOURCE.json.\n'];
licenses.push('\nModified DSH MIT TrajectoryView: optional recorded-only request numbering for Pi bindings; unmatched SDK assistant/abort receipts remain visible without inferred provider request controls. Original default behavior, layout and CSS preserved. Original/adapted hashes remain in SOURCE.json.\n');
licenses.push('\n--- Original Augmentor website brand · MIT · '+brandSource.ref+' ---\n'+readFileSync(join(brandVendor,'LICENSE'),'utf8')+'\nOriginal CSS and favicon are verbatim; local sizing/contrast bindings preserve the original motion. Public original/source hashes are recorded in SOURCE.json.\n');
licenses.push('\n--- Original DSH Metafolder 1.2.1 · MIT · '+metafolderSource.commit+' ---\n'+readFileSync(join(metafolderVendor,'LICENSE'),'utf8')+'\nModified by Augmentor: Pi profile/action/shortcut faces and current pin/archive controls; original UI layout/CSS retained. Original/adapted hashes are recorded in SOURCE.json.\n');
const browserNoticeCatalog=JSON.parse(readFileSync(join(root,'licenses/catalog.json'),'utf8'));
licenses.push('\n--- Original DSH Web Search Free 1.6.0 · MIT · '+searchSource.commit+' ---\n'+readFileSync(join(searchVendor,'LICENSE'),'utf8')+'\nModified by Augmentor: export original configuration card through a private Pi scope, suppress the DSH-only model migration prompt retain unconfirmed drafts and bind badge/thumb to DSH theme tokens. Original controls/layout and preferred source remain recorded in SOURCE.json.\n');
for(const [name,record] of Object.entries(browserNoticeCatalog.sources)){if(createHash('sha256').update(readFileSync(join(root,'licenses',record.file))).digest('hex')!==record.sha256)throw Error('Reviewed supplier notice changed: '+name);}
const npmRecords=[];
const tailwindRoot=dirname(requireUi.resolve('tailwindcss/package.json')),tailwindManifest=JSON.parse(readFileSync(join(tailwindRoot,'package.json'),'utf8'));
licenses.push('\n--- tailwindcss '+tailwindManifest.version+' (MIT; generated dashboard CSS) ---\n'+readFileSync(join(tailwindRoot,'LICENSE'),'utf8'));
npmRecords.push({name:'tailwindcss',version:tailwindManifest.version,license:tailwindManifest.license,notices:['LICENSE'],scope:'generated dashboard CSS; compiler is build-only'});
for(const [directory,manifest] of [...npmRoots].sort((a,b)=>a[1].name.localeCompare(b[1].name))){
  const fortune=manifest.name==='@fortune-sheet/react'||manifest.name==='@fortune-sheet/core';
  let notices=fortune?['selected-dsh/FortuneSheet.txt']:manifest.name==='pdfjs-dist'?pdfNotices:readdirSync(directory).filter(name=>/^(license|notice|copying|copyright)([.\-_]|$)/i.test(name));
  const override=browserNoticeCatalog.overrides[manifest.name+'@'+manifest.version];
  if(!notices.length&&override)notices=['reviewed-catalog/'+browserNoticeCatalog.sources[override].file];
  if(!notices.length)throw Error('Missing browser supplier notice: '+manifest.name);
  if(fortune&&manifest.version!=='1.0.4')throw Error('FortuneSheet differs from the reviewed DSH lock.');
  const texts=notices.map(name=>fortune?readFileSync(join(vendor,'packages/client/ui-sidebar-documentpreview/licenses/FortuneSheet.txt'),'utf8'):name.startsWith('reviewed-catalog/')?readFileSync(join(root,'licenses',name.slice('reviewed-catalog/'.length)),'utf8'):readFileSync(join(directory,name),'utf8'));
  const attribution=manifest.name==='dompurify'?readFileSync(join(directory,'dist/purify.es.mjs'),'utf8').split('\n')[0]:undefined;if(attribution&&!attribution.includes('/*! @license DOMPurify 3.4.16 | (c) Cure53 and other contributors'))throw Error('DOMPurify attribution differs from the reviewed version.');
  const choice=manifest.name==='dompurify'?browserNoticeCatalog.choices?.[manifest.name+'@'+manifest.version]:undefined;if(manifest.name==='dompurify'&&!choice)throw Error('DOMPurify browser licence choice is unreviewed.');if(choice&&manifest.license!==choice.expression)throw Error('Browser licence choice differs from its reviewed expression.');const selectedLicense=choice?.selected??manifest.license;
  licenses.push('\n--- '+manifest.name+' '+manifest.version+' ('+selectedLicense+') ---\n'+(attribution?attribution+'\n':'')+texts.join('\n'));
  npmRecords.push({name:manifest.name,version:manifest.version,license:selectedLicense,...(choice?{declaredLicense:manifest.license,licenseChoice:choice.note,...(attribution?{attribution:{path:'dist/purify.es.mjs',line:1,sha256:createHash('sha256').update(attribution).digest('hex')}}:{})}:{}),notices,...(fortune?{source:'Pinned public DSH spreadsheet licence selection; original MIT copyright retained.'}:{})});
}
for(const family of ['cosmokit','schemastery']){
  const notice=join(vendor,'packages/vendor',family,'LICENSE');if(existsSync(notice))licenses.push('\n--- DSH vendor '+family+' ---\n'+readFileSync(notice,'utf8'));
}
// Commit this workspace's generated assets only after the graph/notice checks.
// Old chunks must not accumulate in the next ordinary artifact. This directory
// is generated source-workspace output, never the selected installed release.
rmSync(join(root,'dist/harness-web'),{recursive:true,force:true});
mkdirSync(join(root,'dist/harness-web'),{recursive:true});
for(const file of result.outputFiles){mkdirSync(dirname(file.path),{recursive:true});writeFileSync(file.path,file.contents);}
writeFileSync(excelWorker.outputFiles[0].path,excelWorker.outputFiles[0].contents);
writeFileSync(join(root,'dist/harness-web/excel-worker-inputs.json'),JSON.stringify(excelWorker.metafile,null,2)+'\n');
const htmlLoader=readFileSync(join(ui,'html-frame-loader.js'),'utf8'),htmlTemplate=readFileSync(join(ui,'html-frame.html'),'utf8');if(/<\/script/i.test(htmlLoader)||!htmlTemplate.includes('<!-- AUGMENTOR_HTML_FRAME_BOOTSTRAP -->'))throw Error('Invalid fixed HTML frame bootstrap.');const htmlFrame=htmlTemplate.replace('<!-- AUGMENTOR_HTML_FRAME_BOOTSTRAP -->','<script>'+htmlLoader+'</script>');writeFileSync(join(root,'dist/harness-web/dsh-html-frame.html'),htmlFrame);
copyFileSync(join(brandVendor,'favicon.svg'),join(root,'dist/harness-web/favicon.svg'));
writeFileSync(join(root,'dist/harness-web/THIRD-PARTY-NOTICES.txt'),licenses.join('\n')+'\n');
const pdfWorker=readFileSync(requireUi.resolve('pdfjs-dist/build/pdf.worker.min.mjs'));
const hostedPdfWorker=Buffer.concat([pdfWorker,Buffer.from('\n// Modified by Augmentor: original DSH readiness handshake for the reviewed local worker.\nself.postMessage({type:"dsh-pdf-worker-ready"});\n')]);
writeFileSync(join(root,'dist/harness-web/SOURCE.json'),JSON.stringify({dsh:provenance,dshContext:contextSource,dshMetafolder:metafolderSource,dshFreeSearch:searchSource,augmentorBrand:brandSource,npm:npmRecords,shortcuts:shortcutRuntime,html:{frame:{name:'dsh-html-frame.html',sha256:createHash('sha256').update(htmlFrame).digest('hex')},loader:{path:'apps/harness/html-frame-loader.js',sha256:createHash('sha256').update(htmlLoader).digest('hex')},scope:'Original HTML bodies; fixed opaque-frame single transfer; no credentials or Host callbacks; scoped network/worker/permission restrictions'},excel:{patches:spreadsheetPatches,scope:'Original read-only spreadsheet registration/grid/conversion with isolated reviewed local module worker; no formula evaluation',worker:{name:'dsh-excel-worker-0.2.1-alpha.2.mjs',sha256:createHash('sha256').update(excelWorker.outputFiles[0].contents).digest('hex')},limits:{maxBytes:16*1024*1024,maxCells:250_000,timeoutMs:15_000},fortuneVersion:'1.0.4',sheetJsVersion:'0.20.3'},pdf:{version:'6.3.289',scope:'Deferred original PDF renderer, reviewed local module worker and local font/CMap/decoder data',notices:pdfNotices,assets:pdfAssetRecords,worker:{name:'dsh-pdf-worker-6.3.289.mjs',sourceSha256:createHash('sha256').update(pdfWorker).digest('hex'),sha256:createHash('sha256').update(hostedPdfWorker).digest('hex'),modification:'Original DSH readiness handshake appended; library body stays byte-exact.'}}},null,2)+'\n');
writeFileSync(join(root,'dist/harness-web/build-inputs.json'),JSON.stringify(result.metafile,null,2)+'\n');
writeFileSync(join(root,'dist/harness-web/dsh-pdf-worker-6.3.289.mjs'),hostedPdfWorker);
rmSync(spreadsheetOverlay,{recursive:true,force:true});
console.log('Built the pinned public DSH GUI.');

writeFileSync(join(root,'dist/harness-web/assets.json'),JSON.stringify([...Object.keys(result.metafile.outputs).map(p=>p.split('/').at(-1)),'dsh-html-frame.html','dsh-excel-worker-0.2.1-alpha.2.mjs','dsh-pdf-worker-6.3.289.mjs','THIRD-PARTY-NOTICES.txt','SOURCE.json','favicon.svg'].sort())+'\n');
