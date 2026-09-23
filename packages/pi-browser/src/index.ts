// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {randomUUID} from 'node:crypto';
import {Type} from 'typebox';
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';
export const browserDefinitions=[
      {name:'browser_screenshot',action:'screenshot',description:'Capture the visible work tab as an image when DOM reads are incomplete. Requires an image-capable model and browser capture permission. Supply a tabId from browser_tabs_list to select the exact target.',parameters:Type.Object({tabId:Type.Optional(Type.Number())})},
      {name:'browser_tabs_list',action:'tabs_list',description:'List tabs in the connected visible browser.',parameters:Type.Object({})},
      {name:'browser_snapshot',action:'snapshot',description:'Read the current work tab with bounded DOM recovery. Supply tabId from browser_tabs_list to select the exact target. Inconclusive reads require a screenshot or a precise limitation report.',parameters:Type.Object({tabId:Type.Optional(Type.Number())})},
      {name:'browser_navigate',action:'navigate',description:'Navigate the visible work tab to an HTTP(S) URL and verify its resulting title and URL.',parameters:Type.Object({url:Type.String()})},
      {name:'browser_click',action:'click',description:'Click a CSS selector in the current work tab. Use the latest snapshot; never repeat an action with unknown outcome.',parameters:Type.Object({selector:Type.String()})},
      {name:'browser_type',action:'type',description:'Replace the contents of an input in the current work tab using its CSS selector.',parameters:Type.Object({selector:Type.String(),text:Type.String()})},
    ];

export class BrowserBroker {
  owners=new Map<string,{owner:object;send:(message:unknown)=>void}>();
  pending=new Map<string,{sid:string;owner:object;finish:(error:Error|null,value?:unknown)=>void}>();
  attach(sid:string,owner:object,send:(message:unknown)=>void){
    const existing=this.owners.get(sid);if(existing&&existing.owner!==owner)throw new Error('This browser chat already has an attached executor.');
    this.owners.set(sid,{owner,send});
  }
  detach(owner:object){
    for(const [sid,row] of this.owners)if(row.owner===owner)this.owners.delete(sid);
    for(const row of this.pending.values())if(row.owner===owner)row.finish(new Error('Browser disconnected. Action outcome may be unknown; it was not retried.'));
  }
  respond(owner:object,id:string,value:unknown,error?:string){
    const row=this.pending.get(id);if(!row||row.owner!==owner)throw new Error('Stale or unowned browser response');
    row.finish(error?new Error(error):null,value);
  }
  execute(sid:string,params:unknown,signal?:AbortSignal):Promise<unknown>{
    const client=this.owners.get(sid);if(!client)return Promise.reject(new Error('Open this chat in the Augmentor browser extension first.'));
    if(signal?.aborted)return Promise.reject(new Error('Cancelled'));
    return new Promise((resolve,reject)=>{
      const id='browser-'+randomUUID();let settled=false;
      const finish=(error:Error|null,value?:unknown)=>{if(settled)return;settled=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);this.pending.delete(id);error?reject(error):resolve(value);};
      const abort=()=>finish(new Error('Browser action cancelled; verify its outcome before retrying.'));
      const timer=setTimeout(()=>finish(new Error('Browser action timed out; outcome may be unknown.')),20000);
      this.pending.set(id,{sid,owner:client.owner,finish});signal?.addEventListener('abort',abort,{once:true});
      try{client.send({id,method:'browser/execute',params});}catch(error){finish(error as Error);}
    });
  }
  package(sid:string){return (pi:ExtensionAPI)=>{
    let unreadable=false;
    for(const d of browserDefinitions)pi.registerTool({name:d.name,label:d.name,description:d.description,parameters:d.parameters,
      execute:async(_id,args,signal,_update,ctx)=>{
        if(unreadable&&['click','type'].includes(d.action))throw Error('A fresh readable snapshot or screenshot is required before acting on an unobserved page.');
        if(d.action==='screenshot'&&!ctx.model?.input.includes('image'))throw Error('Select a model configured for image input before capturing the browser.');
        const value=await this.execute(sid,{action:d.action,...args},signal) as {ok?:boolean;error?:string;observation?:string;url?:string;image?:{data:string;mimeType:string}};
        if(d.action==='snapshot')unreadable=!value?.url||value?.ok===false||value?.observation==='empty';
        if(value?.ok===false)throw Error(value.error??'Browser observation or action failed; inspect before retrying.');
        if(!value||(['click','type'].includes(d.action)&&value.ok!==true))throw Error('No action acknowledgement returned. Outcome unknown; observe before retrying.');
        const {image,...metadata}=value;
        if(d.action==='screenshot'){
          if(!image||image.mimeType!=='image/jpeg'||typeof image.data!=='string'||image.data.length>700000)throw Error('No valid browser screenshot returned.');
          unreadable=false;
        }
        return {content:[{type:'text' as const,text:JSON.stringify(metadata)},...(image?[{type:'image' as const,data:image.data,mimeType:image.mimeType}]:[])],details:{}};
      }});
  };}
}
