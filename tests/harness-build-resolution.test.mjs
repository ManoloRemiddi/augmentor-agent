// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {posix,win32,join} from 'node:path';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {relativeBuildInput,spreadsheetOverlayResolver} from '../scripts/harness-build-resolution.mjs';

test('build input boundaries distinguish actual descendants from siblings, parents and virtual entries',()=>{
 assert.equal(relativeBuildInput('/tmp/sheet','/tmp/sheet/dist/index.mjs',posix),'dist/index.mjs');
 for(const value of ['/tmp/sheet-other/dist/index.mjs','/tmp/sheet/../outside.mjs','/tmp/sheet','','raw:/tmp/sheet/file.js'])assert.equal(relativeBuildInput('/tmp/sheet',value,posix),undefined);
 assert.equal(relativeBuildInput('/tmp/context','/tmp/context/src/history.ts',posix),'src/history.ts');
 assert.equal(relativeBuildInput('/tmp/context','/tmp/context-other/src/history.ts',posix),undefined);
});

test('Windows overlay imports resolve at their original package with mixed separators, case, UNC and drive boundaries',async()=>{
 const overlay='C:\\Temp\\overlay\\node_modules\\@fortune-sheet\\react',original='D:\\project\\apps\\harness\\node_modules\\@fortune-sheet\\react',calls=[];let resolve;
 spreadsheetOverlayResolver(new Map(),new Map([[overlay,original]]),win32).setup({onResolve(_options,callback){resolve=callback;},async resolve(path,options){calls.push({path,...options});return {path:'AUTHORED RESOLVED DEPENDENCY'};}});
 const importer='c:/temp/overlay/node_modules/@fortune-sheet/react/dist/index.esm.js';
 assert.equal((await resolve({path:'immer',importer,kind:'import-statement'})).path,'AUTHORED RESOLVED DEPENDENCY');
 assert.deepEqual(calls,[{path:'immer',resolveDir:original+'\\dist',kind:'import-statement',pluginData:{spreadsheetOriginalResolution:true}}]);
 assert.equal(await resolve({path:'immer',importer,kind:'import-statement',pluginData:{spreadsheetOriginalResolution:true}}),undefined);
 assert.equal(await resolve({path:'immer',importer:importer.replace('/react/','/react-other/'),kind:'import-statement'}),undefined);
 assert.equal(relativeBuildInput(overlay,'D:/Temp/overlay/node_modules/@fortune-sheet/react/dist/index.js',win32),undefined);
 assert.equal(relativeBuildInput('\\\\server\\share\\overlay','//SERVER/share/overlay/dist/index.js',win32),'dist\\index.js');
 assert.equal(relativeBuildInput('\\\\server\\share\\overlay','//server/other/overlay/dist/index.js',win32),undefined);
});

test('real browser build preserves the nested supplier export instead of falling back to an incompatible project package',async t=>{
 const root=await mkdtemp(join(tmpdir(),'augmentor-build-resolution-'));t.after(()=>rm(root,{recursive:true,force:true}));
 const original=join(root,'node_modules','fixture-sheet'),overlay=join(root,'temporary','node_modules','fixture-sheet');
 async function file(path,body){await mkdir(join(path,'..'),{recursive:true});await writeFile(path,body);}
 const importer='import choice from "fixture-choice"; export default choice;';
 await file(join(original,'package.json'),JSON.stringify({name:'fixture-sheet',version:'1.0.0',module:'dist/index.mjs'}));await file(join(original,'dist/index.mjs'),importer);await file(join(overlay,'dist/index.mjs'),importer);
 await file(join(root,'node_modules/fixture-choice/package.json'),JSON.stringify({name:'fixture-choice',version:'11.0.0',module:'index.mjs'}));await file(join(root,'node_modules/fixture-choice/index.mjs'),'export const incompatible = "AUTHORED WRONG PROJECT EXPORT";');
 await file(join(original,'node_modules/fixture-choice/package.json'),JSON.stringify({name:'fixture-choice',version:'9.0.0',module:'index.mjs'}));await file(join(original,'node_modules/fixture-choice/index.mjs'),'export default "AUTHORED LOCKED NESTED EXPORT";');
 const entries=new Map([['fixture-sheet',join(overlay,'dist/index.mjs')]]),origins=new Map([[overlay,original]]);
 const requireUi=createRequire(new URL('../apps/harness/package.json',import.meta.url)),{build}=await import(pathToFileURL(requireUi.resolve('esbuild')).href);
 const result=await build({absWorkingDir:root,stdin:{contents:'import sheet from "fixture-sheet"; export default sheet;',resolveDir:root},bundle:true,format:'esm',platform:'browser',write:false,logLevel:'silent',plugins:[spreadsheetOverlayResolver(entries,origins)],mainFields:['browser','module','main'],nodePaths:[join(root,'node_modules')]});
 assert.equal((await import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].contents).toString('base64'))).default,'AUTHORED LOCKED NESTED EXPORT');
 assert.equal(await readFile(join(original,'dist/index.mjs'),'utf8'),importer);assert.equal(await readFile(join(overlay,'dist/index.mjs'),'utf8'),importer);
});
