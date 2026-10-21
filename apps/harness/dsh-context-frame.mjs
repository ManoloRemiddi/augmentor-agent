// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Presentation of the retained SDK onPayload value, not a reconstruction of
// transport/provider transformations or a second session's canonical history.
const own=(value,key)=>Object.prototype.hasOwnProperty.call(value??{},key);
const json=value=>value===undefined?undefined:JSON.stringify(value);
const marked=(value,source,position=0)=>({...value,wireKey:JSON.stringify([position,source])});
const IMAGE_NOTE='[Image input — binary content remains in the authenticated attachment viewer]';
const OPAQUE_NOTE='[Opaque provider reasoning/signature — inspect the raw recorded body]';
const fail=()=>{throw Error('Unsupported recorded context format');};
function parts(value,gaps){
  if(typeof value==='string')return value;
  if(!Array.isArray(value))fail();
  return value.map(p=>{
    if(!p||typeof p!=='object')fail();
    if(['text','input_text','output_text','summary_text','reasoning_text'].includes(p.type)&&typeof p.text==='string')return {type:'text',text:p.text};
    if(['thinking','reasoning'].includes(p.type)&&typeof (p.thinking??p.text)==='string'){
      if(p.signature)gaps.add('Opaque reasoning/signatures');return {type:'thinking',thinking:p.thinking??p.text};
    }
    if(p.type==='refusal'&&typeof p.refusal==='string')return {type:'text',text:p.refusal};
    if(['image','image_url','input_image'].includes(p.type)){gaps.add('Image bytes/token sizes');return {type:'image',text:IMAGE_NOTE};}
    if(p.type==='redacted_thinking'){gaps.add('Opaque reasoning/signatures');return {type:'text',text:OPAQUE_NOTE};}
    fail();
  });
}
const text=value=>typeof value==='string'?value:value.map(p=>p.text??p.thinking??'').join('\n');
function toolsOf(tools){
  if(tools===undefined)return [];
  if(!Array.isArray(tools))fail();
  return tools.map(item=>{
    const tool=item.function??item;if(typeof tool?.name!=='string')fail();
    if(item.type!==undefined&&!['function','custom'].includes(item.type))fail();
    return {name:tool.name,description:tool.description,schema:tool.parameters??tool.input_schema??tool.parametersJsonSchema??(tool.format?{format:tool.format}:undefined)};
  });
}
function messagesFrame(payload,gaps){
  if(!Array.isArray(payload.messages))fail();
  if(payload.messages.some(m=>!m||!['system','developer','user','assistant','tool'].includes(m.role)))fail();
  // Legacy/OpenAI messages retain their exact argument strings and content.
  const system=[payload.system===undefined?'':text(parts(payload.system,gaps)),...payload.messages.filter(m=>['system','developer'].includes(m.role)).map(m=>text(parts(m.content,gaps)))].filter(Boolean).join('\n\n');
  return {system,tools:toolsOf(payload.tools),messages:payload.messages.filter(m=>['user','assistant','tool'].includes(m.role))};
}
function anthropicFrame(payload,gaps){
  if(!Array.isArray(payload.messages))fail();const messages=[];
  for(const message of payload.messages){
    if(!['user','assistant'].includes(message?.role))fail();
    if(typeof message.content==='string'){messages.push(marked({role:message.role,content:message.content},message));continue;}
    if(!Array.isArray(message.content))fail();
    let group=[],start=0;
    const flush=()=>{if(group.length){messages.push(marked({role:message.role,content:group},message,start));group=[];}};
    for(const [index,p] of message.content.entries()){
      if(p?.type==='tool_use'&&message.role==='assistant'){
        flush();messages.push(marked({role:'assistant',content:[],tool_calls:[{id:p.id,function:{name:p.name,arguments:json(p.input)}}]},message,index));
      }else if(p?.type==='tool_result'&&message.role==='user'){
        flush();messages.push(marked({role:'tool',tool_call_id:p.tool_use_id,content:parts(p.content,gaps),...(typeof p.is_error==='boolean'?{isError:p.is_error}:{})},message,index));
      }else{if(!group.length)start=index;group.push(...parts([p],gaps));}
    }
    flush();
  }
  return {system:payload.system===undefined?'':text(parts(payload.system,gaps)),tools:toolsOf(payload.tools),messages};
}
function responsesFrame(payload,gaps){
  const input=typeof payload.input==='string'?[{role:'user',content:payload.input}]:payload.input;
  if(!Array.isArray(input))fail();const messages=[],system=payload.instructions===undefined?[]:[text(parts(payload.instructions,gaps))];
  for(const [index,item] of input.entries()){
    if(['system','developer','user','assistant'].includes(item?.role)&&[undefined,'message'].includes(item.type)){
      const content=parts(item.content,gaps);if(['system','developer'].includes(item.role))system.push(text(content));else messages.push(marked({role:item.role,content},item,index));
    }else if(['function_call','custom_tool_call'].includes(item?.type)){
      messages.push(marked({role:'assistant',content:[],tool_calls:[{id:item.call_id,function:{name:item.name,arguments:item.type==='function_call'?item.arguments:item.input}}]},item,index));
    }else if(['function_call_output','custom_tool_call_output'].includes(item?.type)){
      messages.push(marked({role:'tool',tool_call_id:item.call_id,content:parts(item.output,gaps)},item,index));
    }else if(item?.type==='reasoning'){
      const content=[...(item.summary??[]),...(item.content??[])].map(p=>({type:'thinking',thinking:text(parts([p],gaps))}));
      if(item.encrypted_content){gaps.add('Opaque reasoning/signatures');content.push({type:'text',text:OPAQUE_NOTE});}
      messages.push(marked({role:'assistant',content},item,index));
    }else fail(); // Native tool-search/additions and unknown items stay raw.
  }
  return {system:system.filter(Boolean).join('\n\n'),tools:toolsOf(payload.tools),messages};
}
function googleParts(value,gaps){
  if(!Array.isArray(value))fail();return value.map(p=>{
    if(typeof p?.text==='string'){if(p.thoughtSignature)gaps.add('Opaque reasoning/signatures');return p.thought?{type:'thinking',thinking:p.text}:{type:'text',text:p.text};}
    if(p?.inlineData||p?.fileData){const media=p.inlineData??p.fileData;if(media.mimeType?.startsWith('image/')){gaps.add('Image bytes/token sizes');return {type:'image',text:IMAGE_NOTE};}gaps.add('Opaque media bytes/token sizes');return {type:'text',text:'[Opaque provider media — inspect the raw recorded body]'};}
    fail();
  });
}
function googleFrame(payload,gaps){
  if(!Array.isArray(payload.contents))fail();const config=payload.config??{},messages=[];
  for(const message of payload.contents){
    if(!['user','model'].includes(message?.role)||!Array.isArray(message.parts))fail();let group=[],start=0;
    const flush=()=>{if(group.length){messages.push(marked({role:message.role==='model'?'assistant':'user',content:group},message,start));group=[];}};
    for(const [index,p] of message.parts.entries()){
      if(p?.functionCall&&message.role==='model'){
        flush();const call=p.functionCall;messages.push(marked({role:'assistant',content:[],tool_calls:[{id:call.id,function:{name:call.name,arguments:json(call.args)}}]},message,index));if(p.thoughtSignature)gaps.add('Opaque reasoning/signatures');
      }else if(p?.functionResponse&&message.role==='user'){
        flush();const result=p.functionResponse;messages.push(marked({role:'tool',tool_call_id:result.id,name:result.name,content:[{type:'text',text:json(result.response)??'[Result content unavailable]'},...googleParts(result.parts??[],gaps)],...(own(result.response,'error')?{isError:true}:{})},message,index));
      }else{if(!group.length)start=index;group.push(...googleParts([p],gaps));}
    }
    flush();
  }
  const system=config.systemInstruction===undefined?'':typeof config.systemInstruction==='string'?config.systemInstruction:text(googleParts(config.systemInstruction.parts,gaps));
  if(config.tools!==undefined&&!Array.isArray(config.tools))fail();
  const tools=toolsOf((config.tools??[]).flatMap(tool=>{if(!Array.isArray(tool.functionDeclarations))fail();return tool.functionDeclarations;}));
  return {system,tools,messages};
}
/** API is authoritative. Only old records without an API get messages fallback. */
export function contextFrame(payload,api){
  if(!payload||typeof payload!=='object')return null;const gaps=new Set();
  try{
    const parser=api===undefined||api==='openai-completions'?messagesFrame:api==='anthropic-messages'?anthropicFrame:['openai-responses','azure-openai-responses','openai-codex-responses'].includes(api)?responsesFrame:['google-generative-ai','google-vertex'].includes(api)?googleFrame:null;
    if(!parser)return null;return {...parser(payload,gaps),gaps:[...gaps]};
  }catch{return null;}
}
