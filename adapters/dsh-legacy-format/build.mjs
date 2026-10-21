// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {build} from 'esbuild';import {readFile,lstat} from 'node:fs/promises';import {resolve,dirname,join,relative,isAbsolute} from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';import assert from 'node:assert/strict';
const repo=fileURLToPath(new URL('../../',import.meta.url)),sha=b=>createHash('sha256').update(b).digest('hex');
/** Build parser-only code from pinned public inputs. No source input is executed
 * until the complete graph and all external imports have passed validation. */
export async function buildFormatParsers(source,stage){
 source=resolve(source);stage=resolve(stage);
 const manifest=JSON.parse(await readFile(join(repo,'release/dsh-legacy-format/SOURCES.json'))),owned=[join(repo,'adapters/dsh-legacy-format/restore.ts'),join(repo,'adapters/dsh-legacy-format/descriptor-v2.mjs')],expected=new Map(manifest.files.map(r=>[resolve(source,r.path),r.sha256])),alias={};
 if(manifest.repository!=='https://github.com/deepseek-ai/deepseek-harness'||manifest.revision!=='d743267388641bc76f17c45ce8b4c231aed1d32c'||manifest.license!=='MIT'||manifest.files.length!==52||expected.size!==52||manifest.files.some(r=>isAbsolute(r.path)||r.path.split('/').some(p=>!p||p==='.'||p==='..')||!(/^[a-f0-9]{64}$/).test(r.sha256)))throw Error('Invalid public parser source manifest.');
 const verifyInputs=async()=>{for(const [path,digest] of expected){const info=await lstat(path);if(!info.isFile()||info.isSymbolicLink())throw Error('Pinned public input is not a regular file');assert.equal(sha(await readFile(path)),digest,'Pinned public format input differs');}};
 await verifyInputs();
 for(const name of ['session-format','session-format-v0-to-v1','session-format-v1-to-v2','session-format-v2-to-v3','session-format-v3-to-v4'])alias['@deepseek-ai/dsh-'+name]=join(source,'packages/session',name,'src/index.ts');
 for(const [name,path] of Object.entries({'@deepseek-ai/dsh-util-values':'packages/util/values/src/index.ts','@deepseek-ai/dsh-brand':'packages/util/brand/src/index.ts','@deepseek-ai/dsh-util-crypto':'packages/util/crypto/src/index.ts','@deepseek-ai/dsh-llm':'packages/llm/llm/src/assistant-stream.ts','@augmentor/dsh-known-event-types':'packages/core/session/src/known-event-types.ts'}))alias[name]=join(source,path);
 const modules={},builds=[];
 for(const mode of ['baseline','compat']){
  const overlays=[],file=join(stage,mode+'.mjs');
  const built=await build({absWorkingDir:repo,entryPoints:[owned[0]],outfile:file,alias,bundle:true,platform:'node',format:'esm',target:'node24',minifyWhitespace:true,metafile:true,legalComments:'eof',plugins:[{name:'checksum-pinned-parser-only-inputs',setup(api){api.onLoad({filter:/\.(ts|mjs)$/},async args=>{
   const path=resolve(args.path);if(!expected.has(path)&&!owned.includes(path))throw Error('Unreviewed source in parser graph.');let body=await readFile(path,'utf8');if(expected.has(path)&&sha(body)!==expected.get(path))throw Error('Parser input changed during build.');
   if(mode==='compat'&&path.endsWith('/session-format-v0-to-v1/src/validation.ts')){const old="event.type === 'subagent/descriptor' && data['version'] !== 3";if(body.split(old).length!==2)throw Error('Public descriptor gate changed.');body=body.replace(old,old+" && data['version'] !== 2");overlays.push(relative(source,path));}
   if(mode==='compat'&&path.endsWith('/session-format-v0-to-v1/src/payload-validation.ts')){const old='function subagentDescriptorValue(data: JsonRecord, label: string): void {';if(body.split(old).length!==2)throw Error('Public descriptor semantics changed.');body='import {validateDescriptorV2} from '+JSON.stringify(owned[1])+';\n'+body.replace(old,old+"\n  if(data['version']===2){validateDescriptorV2(data);return;}\n");overlays.push(relative(source,path));}
   return {contents:body,loader:path.endsWith('.ts')?'ts':'js',resolveDir:dirname(path)};
  });}}]});
  const paths=Object.keys(built.metafile.inputs).map(p=>resolve(repo,p));assert(paths.every(p=>expected.has(p)||owned.includes(p)));assert.equal(paths.filter(p=>expected.has(p)).length,51);assert.equal(overlays.length,mode==='compat'?2:0);assert(Object.values(built.metafile.outputs).every(o=>o.imports.every(i=>i.external&&['node:path','node:crypto','node:util'].includes(i.path))));
  modules[mode]=await import(pathToFileURL(file));builds.push({mode,publicModules:51,ownedModules:paths.filter(p=>owned.includes(p)).map(p=>relative(repo,p)),overlays,externalImports:[...new Set(Object.values(built.metafile.outputs).flatMap(o=>o.imports.map(i=>i.path)))],outputSha256:sha(await readFile(file))});
 }
 return {manifest,modules,builds,verifyInputs};
}
