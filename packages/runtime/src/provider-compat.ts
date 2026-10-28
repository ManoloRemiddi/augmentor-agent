// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import type {ExtensionAPI} from '@earendil-works/pi-coding-agent';

/** Older llama.cpp tool grammars reject some bounded string repetitions.
 * Only the declared provider payload changes; SDK tool schemas keep their limits.
 */
export function llamaCppToolPayload(payload:unknown):unknown|undefined{
 if(!payload||typeof payload!=='object'||Array.isArray(payload))return;
 const body=payload as Record<string,unknown>;
 if(!Array.isArray(body.tools))return;
 let changed=false;
 const schema=(value:unknown)=>{
  if(!value||typeof value!=='object'||Array.isArray(value))return;
  const node=value as Record<string,unknown>;
  for(const key of ['minLength','maxLength'])if(typeof node[key]==='number'){delete node[key];changed=true;}
  for(const key of ['properties','patternProperties','$defs','definitions','dependentSchemas']){
   const map=node[key];if(map&&typeof map==='object'&&!Array.isArray(map))Object.values(map).forEach(schema);
  }
  for(const key of ['items','additionalProperties','additionalItems','contains','not','if','then','else','propertyNames','unevaluatedProperties','unevaluatedItems']){
   const child=node[key];if(Array.isArray(child))child.forEach(schema);else schema(child);
  }
  for(const key of ['anyOf','oneOf','allOf','prefixItems'])if(Array.isArray(node[key]))(node[key] as unknown[]).forEach(schema);
 };
 const tools=body.tools.map(tool=>{
  if(!tool||typeof tool!=='object'||tool.type!=='function'||!tool.function?.parameters)return tool;
  const parameters=structuredClone(tool.function.parameters);schema(parameters);
  return {...tool,function:{...tool.function,parameters}};
 });
 return changed?{...body,tools}:undefined;
}

export function piLlamaCppSchemas(pi:ExtensionAPI){
 const providers=new Set((process.env.AUGMENTOR_PI_LLAMA_CPP_PROVIDERS??'').split(',').map(value=>value.trim()).filter(Boolean));
 if(!providers.size)return;
 pi.on('before_provider_request',(event,ctx)=>{
  if(ctx.model?.api==='openai-completions'&&providers.has(ctx.model.provider))return llamaCppToolPayload(event.payload);
 });
}
