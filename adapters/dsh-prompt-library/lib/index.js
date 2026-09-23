// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Public DSH webServer route; prompt persistence belongs to Augmentor.
import {promptCall} from '../../../dist/prompt-library/src/client.js';
import {improvePrompt} from '../../dsh-product/improve-prompt.mjs';
export const name='dsh-prompt-library';
export const inject=['webServer','llm'];
export function apply(ctx){
  ctx.effect(()=>ctx.webServer.register({kind:'exact',path:'/api/augmentor-prompts',handler:async(req,res)=>{
    const reply=(code,value)=>{res.writeHead(code,{'content-type':'application/json','cache-control':'no-store'});res.end(JSON.stringify(value));};
    const origin=req.headers.origin;
    if(origin&&origin!==`http://${req.headers.host}`&&origin!==`https://${req.headers.host}`){reply(403,{ok:false,error:'Origin not allowed'});return;}
    if(req.method!=='POST'||!req.headers['content-type']?.startsWith('application/json')){reply(405,{ok:false,error:'Use JSON POST'});return;}
    try{
      let raw='';for await(const chunk of req){raw+=chunk;if(Buffer.byteLength(raw)>1024*1024)throw new Error('Request too large');}
      const {action='list',...params}=JSON.parse(raw);
      if(action==='improve'){
        const controller=new AbortController();res.once('close',()=>{if(!res.writableEnded)controller.abort()});
        const library=await promptCall('prompts.list');
        const result=await improvePrompt(ctx.llm,{...params,instructions:library.improvement.content},AbortSignal.any([controller.signal,AbortSignal.timeout(60000)]));
        reply(200,{ok:true,...result});return;
      }
      if(!['list','save','delete','improvement.save'].includes(action))throw new Error('Unsupported prompt action');
      reply(200,{ok:true,library:await promptCall('prompts.'+action,params)});
    }catch(error){reply(400,{ok:false,error:error.message});}
  }}));
}
