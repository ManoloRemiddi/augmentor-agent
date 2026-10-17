// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored loopback responses for actual pinned SDK conversions.
import {appendFileSync} from 'node:fs';
export async function serveContextProvider(api,req,res,{path,requestLog}){
  const route=api==='anthropic-messages'?req.url.startsWith('/v1/messages'):api==='openai-responses'?req.url==='/v1/responses':api==='google-generative-ai'?req.url.includes(':streamGenerateContent'):false;
  if(req.method!=='POST'||!route){res.writeHead(404).end();return;}
  let raw='';for await(const data of req)raw+=data;const body=JSON.parse(raw);
  if(requestLog)appendFileSync(requestLog,JSON.stringify(body)+'\n',{mode:0o600});
  const after=api==='anthropic-messages'?body.messages.some(m=>Array.isArray(m.content)&&m.content.some(p=>p.type==='tool_result')):api==='openai-responses'?body.input.some(p=>p.type==='function_call_output'):body.contents.some(m=>m.parts.some(p=>p.functionResponse));
  const answer='The note says: Harness fixture ready. The real Pi session executed one read tool; this provider is a deterministic test fixture.';
  res.writeHead(200,{'content-type':'text/event-stream'});const send=(type,data)=>res.write((type?'event: '+type+'\n':'')+'data: '+JSON.stringify(data)+'\n\n');
  if(api==='anthropic-messages'){
    const emit=(type,data)=>send(type,{type,...data});
    emit('message_start',{message:{id:'authored-anthropic',type:'message',role:'assistant',model:'harness-fixture',content:[],stop_reason:null,usage:{input_tokens:640,output_tokens:0}}});
    emit('content_block_start',{index:0,content_block:after?{type:'text',text:''}:{type:'tool_use',id:'authored_read',name:'read',input:{}}});
    emit('content_block_delta',{index:0,delta:after?{type:'text_delta',text:answer}:{type:'input_json_delta',partial_json:JSON.stringify({path})}});
    emit('content_block_stop',{index:0});emit('message_delta',{delta:{stop_reason:after?'end_turn':'tool_use',stop_sequence:null},usage:{output_tokens:45}});emit('message_stop',{});
  }else if(api==='openai-responses'){
    const emit=(type,data)=>send(type,{type,...data}),item=after?{type:'message',id:'msg_authored',role:'assistant',status:'completed',content:[{type:'output_text',text:answer,annotations:[]}]}:{type:'function_call',id:'fc_authored',call_id:'authored_read',name:'read',arguments:JSON.stringify({path})};
    emit('response.created',{response:{id:'resp_authored'}});emit('response.output_item.added',{output_index:0,item:after?{...item,content:[]}:{...item,arguments:''}});
    if(after)emit('response.output_text.delta',{output_index:0,content_index:0,item_id:item.id,delta:answer});else emit('response.function_call_arguments.delta',{output_index:0,item_id:item.id,delta:item.arguments});
    emit('response.output_item.done',{output_index:0,item});emit('response.completed',{response:{id:'resp_authored',status:'completed',output:[item],usage:{input_tokens:640,output_tokens:45,total_tokens:685}}});
  }else{
    send(null,{responseId:'authored-google',candidates:[{index:0,content:{role:'model',parts:after?[{text:answer}]:[{functionCall:{name:'read',args:{path}}}]},finishReason:'STOP'}],usageMetadata:{promptTokenCount:640,candidatesTokenCount:45,totalTokenCount:685}});
  }
  res.end();
}
