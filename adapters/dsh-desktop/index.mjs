// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Mount only in Augmentor's Linux preset. Use the same executor as Pi.
import {definitions,control} from '../../dist/desktop/src/index.js'
import {applyBrowserPolicy} from './browser-policy.mjs'
import {applyResponsiveSteering} from './steering.mjs'
import {applyLinuxSupport} from './linux-support.mjs'
export const name='augmentor-desktop'
export const inject=['tools','llm','attachments']
export function apply(ctx){
  applyBrowserPolicy(ctx)
  applyResponsiveSteering(ctx)
  applyLinuxSupport(ctx)
  const owners=new Set()
  for(const d of definitions)ctx.tools.register({name:d.name,description:d.description,parameters:d.parameters,
    output:{schema:{type:'object'},render:(_args,value)=>value.content},
    execute:async(args,exec)=>{
      const id=exec.agent?.id;if(!id)throw Error('Desktop control requires an active Augmentor desktop conversation.')
      const owner='dsh:'+id;owners.add(owner)
      if(d.method==='capture'){
        const routed=exec.agent.session.requestHeader()?.config
        const provider=routed?.provider??exec.agent.options.provider,model=routed?.model??exec.agent.options.model
        const info=await ctx.llm.resolveModelInfo(provider,model,exec.signal)
        if(!info.inputModalities?.includes('image'))throw Error('Select a DSH model that declares image input before capturing the desktop.')
      }
      const {image,...metadata}=await control(d.method,owner,args,exec.signal)
      const content=[{type:'text',text:JSON.stringify(metadata)}]
      if(image){
        exec.signal.throwIfAborted()
        const attachment=await ctx.attachments.saveImage({data:Buffer.from(image.data,'base64'),mediaType:image.mimeType,name:'Augmentor desktop observation'})
        exec.signal.throwIfAborted();content.push({type:'image',attachment})
      }
      return {content}
    }})
  ctx.on('agent/turn-stopping',async({agent})=>{const owner='dsh:'+agent.id;if(owners.has(owner)){await control('stop',owner).catch(()=>{});owners.delete(owner)}})
  ctx.on('agent/status',({agent,status})=>{if(status==='idle'){const owner='dsh:'+agent.id;if(owners.has(owner)){void control('stop',owner).catch(()=>{});owners.delete(owner)}}})
  ctx.on('dispose',async()=>{await Promise.all([...owners].map(owner=>control('stop',owner).catch(()=>{})))})
}
