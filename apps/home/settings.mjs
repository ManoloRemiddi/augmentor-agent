// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync,existsSync,writeFileSync,renameSync,mkdirSync} from 'node:fs';
import {join} from 'node:path';
const filename=config=>join(config.stateDir,'model.json');
export function modelSettings(input,previous={}){
 if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(k=>!['model','modelUrl','contextWindow','key','allowLanHttp'].includes(k)))throw Error('Invalid model configuration');
 if(typeof input.model!=='string'||!input.model.trim()||input.model.length>160)throw Error('Enter the provider model ID');
 const url=new URL(input.modelUrl);
 if(!['https:','http:'].includes(url.protocol)||url.username||url.password||url.search||url.hash)throw Error('Enter an HTTP(S) API base URL without credentials');
 if(url.protocol==='http:'&&!['127.0.0.1','localhost','[::1]'].includes(url.hostname)&&input.allowLanHttp!==true)throw Error('Confirm use of your private LAN HTTP endpoint');
 if(!Number.isInteger(input.contextWindow)||input.contextWindow<8192||input.contextWindow>262144)throw Error('Context window must be between 8192 and 262144');
 const key=input.key===undefined?previous.key:input.key;
 if(typeof key!=='string'||key.length>4096||/[\r\n]/.test(key))throw Error('Provide a valid API credential, or an empty value for an endpoint without authentication');
 // Never silently send the previous provider's credential to a new endpoint.
 if(input.key===undefined&&previous.modelUrl!==input.modelUrl)throw Error('Changing API endpoint requires an explicit credential selection');
 return {model:input.model.trim(),modelUrl:url.href.replace(/\/$/,''),contextWindow:input.contextWindow,key,allowLanHttp:input.allowLanHttp===true};
}
export function loadModelSettings(config){if(!existsSync(filename(config)))return null;return modelSettings(JSON.parse(readFileSync(filename(config),'utf8')));}
export function saveModelSettings(config,value){mkdirSync(config.stateDir,{recursive:true,mode:0o700});const path=filename(config);writeFileSync(path+'.tmp',JSON.stringify(value)+'\n',{mode:0o600});renameSync(path+'.tmp',path);}
export function publicModelSettings(config){return {model:config.model,modelUrl:config.modelUrl,contextWindow:config.contextWindow??131072,configured:true,fallback:'disabled',credentials:'stored privately on NAS; never returned',cloudData:'Home requests and enabled device state are sent to the selected model endpoint.'};}
export async function discoverModels(settings){
 const response=await fetch(settings.modelUrl.replace(/\/$/,'')+'/models',{headers:settings.key?{Authorization:'Bearer '+settings.key}:{},redirect:'error',signal:AbortSignal.timeout(10000)});
 if(!response.ok){await response.body?.cancel();throw Error('Provider discovery failed ('+response.status+'); verify endpoint and access');}
 const reader=response.body.getReader(),chunks=[];let size=0;try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>1048576){await reader.cancel();throw Error('Provider inventory too large');}chunks.push(value);}}finally{reader.releaseLock();}
 const result=JSON.parse(Buffer.concat(chunks).toString());if(!Array.isArray(result.data))throw Error('Endpoint does not support OpenAI-compatible model discovery');
 return {models:result.data.slice(0,500).map(m=>m.id).filter(id=>typeof id==='string'&&id.length<=160),qualification:'Inventory only; text and tool execution must be tested separately.'};
}
