// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import assert from 'node:assert/strict';import net from 'node:net';import {mkdtemp,rm,mkdir} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join,resolve} from 'node:path';import {pathToFileURL} from 'node:url';import {spawn,execFile} from 'node:child_process';import {promisify} from 'node:util';import {once} from 'node:events';
export const root=resolve(process.env.AUGMENTOR_PI_TEST_ROOT??'.'),modules=async name=>import(pathToFileURL(join(root,'dist/runtime/src',name+'.js'))),exec=promisify(execFile);
export const {pythonExecutable}=await import(pathToFileURL(join(root,'dist/platform/src/index.js'))),py=pythonExecutable();
const {inspectSharedProfile,importSharedProfile}=await modules('shared-profile-import');
const companions=new Set();
export async function sharedFixture(t,mode='plain'){
 const base=await mkdtemp(join(tmpdir(),'augmentor-shared-import-'));t.after(async()=>{for(const peer of companions)if(peer.profile.data.startsWith(base+'/'))await peer.stop();await rm(base,{recursive:true,force:true});});const {stdout}=await exec(py,['-I','-B',resolve('tests/fixtures/shared-profile-data.py'),root,base,mode]);const f=JSON.parse(stdout),inspection=inspectSharedProfile(f.source);return {...f,base,inspection,import:options=>importSharedProfile(f.source,f.target,inspection.sha256,options)};
}
export async function query(data,sql){const {stdout}=await exec(py,['-I','-B','-c',"import json,sqlite3,sys;db=sqlite3.connect(sys.argv[1]);db.row_factory=sqlite3.Row;print(json.dumps([dict(r) for r in db.execute(sys.argv[2])]))",data,sql]);return JSON.parse(stdout);}
export function companionCall(profile,component,method,params={},id=crypto.randomUUID()){
 return new Promise((done,reject)=>{const socket=net.createConnection(join(profile.state,component==='memory'?'dual-memory.sock':'prompts.sock'));let buffer='';socket.setTimeout(5000,()=>socket.destroy(Error('Authored companion request timed out.')));socket.once('error',reject);socket.once('connect',()=>socket.write(JSON.stringify({protocol:'augmentor-prompts/1',id,method,params})+'\n'));socket.on('data',bytes=>{buffer+=bytes;if(buffer.length>1024*1024){socket.destroy(Error('Companion response exceeded its bound.'));return;}const end=buffer.indexOf('\n');if(end<0)return;socket.end();try{const frame=JSON.parse(buffer.slice(0,end));assert.equal(frame.id,id);if(frame.error)reject(Error(frame.error.message));else done(frame.result);}catch(error){reject(error);}});socket.once('end',()=>reject(Error('Companion disconnected before its result.')));});
}
export function companion(t,profile,component){
 const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>!/^(AUGMENTOR_|DSH_|PI_)/.test(k)));Object.assign(env,{AUGMENTOR_SHARED_STATE:profile.state,AUGMENTOR_SHARED_DATA:profile.data,XDG_CONFIG_HOME:join(profile.state,'config'),AUGMENTOR_PI_CONFIG:join(profile.state,'pi-config'),PYTHONDONTWRITEBYTECODE:'1'});
 const child=spawn(py,['-I','-B',join(root,component==='memory'?'services/memory/service.py':'services/prompt-library/service.py')],{env,cwd:profile.state,stdio:['ignore','ignore','pipe']});let errors='';child.stderr.on('data',b=>errors+=b);
 const exit=once(child,'exit');const stop=async()=>{if(child.exitCode===null&&child.signalCode===null){child.kill('SIGTERM');await exit;}};t.after(stop);
 const ready=async()=>{const end=Date.now()+10000;while(Date.now()<end){assert.equal(child.exitCode,null,errors);try{return await companionCall(profile,component,component==='memory'?'memory.dual.describe':'host.describe');}catch(error){if(!['ENOENT','ECONNREFUSED'].includes(error.code))throw error;}await new Promise(r=>setTimeout(r,20));}throw Error('Authored companion startup timed out: '+errors);};
 const peer={profile,child,exit,stop,ready,errors:()=>errors};companions.add(peer);exit.finally(()=>companions.delete(peer));return peer;
}
