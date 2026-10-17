// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFile} from 'node:fs/promises';import {join} from 'node:path';import {pathToFileURL} from 'node:url';
import {application,bundleFixture} from './dsh-bundle.mjs';import {authoredFileDshProject} from './dsh-file-project.mjs';
export const load=name=>import(pathToFileURL(join(application,'dist/runtime/src',name+'.js')));
const {importDshProject}=await load('dsh-project-import'),{PiAttachments}=await load('attachments'),{PiDshHistoryMedia}=await load('dsh-history-media'),{PiNativeRelocationContext}=await load('native-relocation-context'),{inheritedDshAttachment}=await load('dsh-branch-history'),{stateInventory}=await load('profile-transaction');
const pkg=JSON.parse(await readFile(join(application,'node_modules/@earendil-works/pi-coding-agent/package.json')));export const {SessionManager}=await import(pathToFileURL(join(application,'node_modules/@earendil-works/pi-coding-agent',pkg.exports['.'].import)));
export async function nativeFile(state,id){const meta=JSON.parse(await readFile(join(state,'sessions',id+'.meta.json')));return {meta,manager:SessionManager.open(meta.file),bytes:await readFile(meta.file)};}
export async function historicalFileRelocationFixture(t,{where='user',count=1,selection}={}){
 const f=await bundleFixture(t,cwd=>{const value=authoredFileDshProject(cwd,{where}),parts=[value.filePart];for(let i=1;i<count;i++){const part=structuredClone(value.filePart);part.attachment.name='authored-alias-'+i+'.txt';const e=value.value.sessions[0].records[value.fileSeq].event;(e.type==='user/message'?e.data:e.data.message).content.push(part);parts.push(part);}return {...value,fileParts:parts};}),receipt=await importDshProject(f.source,f.state,{...f.options,...(selection?{selection}:{})}),id=receipt.sessions[0].sessionId,source=await nativeFile(f.state,id),store=new PiAttachments(f.state),former=[];
 for(const part of f.authored.fileParts)former.push(JSON.parse((await store.resolve(id,'',[part])).text.split('\n').at(-1)).path);
 const summary='AUTHORED-COMPACTED-HISTORICAL-FILES: '+former.join(' ; ');source.manager.appendCompaction(summary,source.manager.getBranch().at(-1).id,100);
 const context=source.manager.buildSessionContext().messages;if(context.some(m=>m.customType==='augmentor.dsh-media.v1'))throw Error('Authored media was not compacted out of active context.');
 return {...f,receipt,id,summary,former,sourceNative:await readFile(source.meta.file),sourceMeta:source.meta,sourceSnapshot:stateInventory(f.state)};
}
export async function historicalBoundContext(state,id,{ancestors=[id],messages}={}){
 const native=await nativeFile(state,id),store=new PiAttachments(state,(_,part)=>inheritedDshAttachment(native.manager,state,part)),session={model:{input:['text']},agent:{}},relocation=new PiNativeRelocationContext(state,id,store,()=>ancestors),media=new PiDshHistoryMedia(store,id);relocation.install(session);media.install(session);
 try{return await session.agent.transformContext(messages??native.manager.buildSessionContext().messages);}finally{media.dispose();relocation.dispose();}
}
export function hintedPaths(messages){const hint=messages.find(m=>m.customType==='augmentor.native-relocation.v1');return hint?JSON.parse(hint.content.split('\n').at(-1)):[];}
