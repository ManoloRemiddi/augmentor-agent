// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {planFixture} from './plans.mjs';
import {privateDir,atomicJson} from '../../dist/runtime/src/storage.js';import {dictationPeer} from './dictation.mjs';
export async function dictationHost(t,options={}){
 const peer=dictationPeer(options),home=privateDir(join(tmpdir(),'augmentor-dictation-peer-'+crypto.randomUUID()));await peer.listen();
 atomicJson(join(home,'config.json'),{port:Number(new URL(peer.connection.base).port)});if(process.platform==='win32')atomicJson(join(home,'token'),null);await writeFile(join(home,'token'),peer.connection.token,{mode:0o600});
 const f=await planFixture(t,{voiceMode:{home},jobMode:{}}),link=await f.link(),url=new URL(link.url),token=new URLSearchParams(url.hash.slice(1)).get('token');
 t.after(async()=>{await f.stop();await peer.close();await rm(home,{recursive:true,force:true});});
 const post=async(action,value={},bearer=token)=>{const binary=action==='transcribe',p='/api/dictation/'+action+(binary?'?'+new URLSearchParams({clientId:value.clientId,captureId:value.captureId}):'');return fetch(url.origin+p,{method:'POST',headers:{Authorization:'Bearer '+bearer,'content-type':binary?'audio/wav':'application/json'},body:binary?value.bytes:JSON.stringify(value)});};
 const ok=async(action,value)=>{const response=await post(action,value),body=await response.json();assert.equal(response.status,200,JSON.stringify(body));return body;};
 return {...f,peer,link,token,post,ok};
}
