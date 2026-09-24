// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {createRequire} from 'node:module';import {readFileSync} from 'node:fs';import {pathToFileURL,fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../../',import.meta.url)).replace(/\/$/,'');const require=createRequire(root+'/apps/browser/test/proof.js');const {JSDOM}=require('jsdom');
const dom=new JSDOM(readFileSync(root+'/apps/browser/extension/sidepanel.html','utf8'),{url:'http://localhost/sidepanel.html',runScripts:'outside-only',pretendToBeVisual:true});
for(const k of ['document','window','localStorage','location','MutationObserver','navigator','HTMLElement'])Object.defineProperty(globalThis,k,{value:k==='window'?dom.window:dom.window[k],configurable:true});
globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window);globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window);globalThis.getComputedStyle=dom.window.getComputedStyle.bind(dom.window);dom.window.HTMLElement.prototype.scrollTo=function({top}){this.scrollTop=top};
for(const file of ['theme-tokens.js','vendor/marked.min.js'])dom.window.eval(readFileSync(root+'/apps/browser/extension/'+file,'utf8'));globalThis.__dshAugTheme=dom.window.__dshAugTheme;globalThis.marked=dom.window.marked;
const saved={},messages=[];const snapshot={phase:'ready',harness:'dsh',running:false,sessionId:'fixture',saved:[],log:[],model:{provider:'fixture',model:'fixture-model'},models:[{provider:'fixture',models:[{model:'fixture-model',name:'Fixture model'}]}],capabilities:{branch:true,edit:true}};
globalThis.chrome={runtime:{getURL:x=>x,onMessage:{addListener:f=>messages.push(f)},sendMessage:async m=>m.type==='log'?snapshot:m.type==='surface/state'?{ok:true,pinned:true}:m.type==='surface/appearance'?{ok:true,result:{theme:'dark',animation:false,tokens:{'--brand':'#66ffaa','--bg':'#051410'},values:{}}}:m.type==='voice/preferences'?{ok:true,result:{enabled:true,mode:'manual'}}:{ok:true,library:{revision:0,prompts:[]}}},storage:{session:{get:async k=>({[k]:saved[k]}),set:async o=>Object.assign(saved,o),remove:async k=>delete saved[k]},local:{set:async()=>{}}}};
try{
 await import(pathToFileURL(root+'/apps/browser/extension/sidepanel.js'));await new Promise(r=>setTimeout(r,200));
 const d=dom.window.document;const errors=[...d.querySelectorAll('.err')].map(x=>x.textContent);if(errors.length)throw Error(errors.join('\n'));
 if(d.querySelector('#model-label').textContent!=='Fixture model')throw Error('Model did not populate');
 if(!d.querySelector('.voice-drawing'))throw Error('Native contour did not mount');
 console.log('Complete sidebar entrypoint boots; model and native voice SVG present; no UI errors.');
 d.querySelector('#more').click();d.querySelector('#settings').click();
}finally{dom.window.dispatchEvent(new dom.window.Event('pagehide'));dom.window.close()}
