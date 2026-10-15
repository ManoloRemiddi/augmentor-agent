// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Literal presence in recognized human text fields at the public onPayload
 * boundary. Tool results, assistant quotations and arbitrary metadata are not
 * evidence of a user input. This does not establish causal consumption. */
export function providerUserTextPresence(payload:unknown,text:string,api?:string){
 if(!text)return {state:'empty',pointers:[] as string[]};
 if(!payload||typeof payload!=='object')return {state:'unavailable',pointers:[] as string[]};
 const body=payload as any,fields:{pointer:string;value:string}[]=[];let invalid=false,recognized=false,remaining=10000;
 const content=(value:any,pointer:string,google=false)=>{
  if(typeof value==='string'){fields.push({pointer,value});return;}
  if(!Array.isArray(value)||value.length>10000){invalid=true;return;}
  value.forEach((part,index)=>{
   if(--remaining<0){invalid=true;return;}
   if(google?typeof part?.text==='string'&&!part.thought:['text','input_text'].includes(part?.type)&&typeof part.text==='string')fields.push({pointer:pointer+'/'+index+'/text',value:part.text});
   // No descent into tool_result/functionResponse, image or opaque fields.
  });
 };
 const messages=(value:any,pointer:string,google=false)=>{
  if(!Array.isArray(value)||value.length>10000){invalid=true;return;}
  recognized=true;value.forEach((row,index)=>{if(--remaining<0){invalid=true;return;}if(row?.role==='user'&&(!row.type||row.type==='message'))content(google?row.parts:row.content,pointer+'/'+index+(google?'/parts':'/content'),google);});
 };
 switch(api){
  case 'openai-completions':case 'anthropic-messages':messages(body.messages,'/messages');break;
  case 'openai-responses':case 'azure-openai-responses':case 'openai-codex-responses':
   if(typeof body.input==='string'){recognized=true;content(body.input,'/input');}else messages(body.input,'/input');break;
  case 'google-generative-ai':case 'google-vertex':messages(body.contents,'/contents',true);break;
  default:return {state:'unavailable',pointers:[] as string[]};
 }
 const pointers=fields.filter(field=>field.value.includes(text)).map(field=>field.pointer);
 return {state:pointers.length?'exact-text-present-in-user-field':invalid||!recognized?'unavailable':'not-present-in-recognized-user-fields',pointers:pointers.slice(0,256),omittedPointers:Math.max(0,pointers.length-256)};
}
