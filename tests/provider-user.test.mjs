// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {providerUserTextPresence as presence} from '../dist/observation/src/provider-user.js';
const text='AUTHORED_SKILL_TEXT';
test('recognized provider user text fields retain precise pointers',()=>{for(const [api,body,pointer] of [
 ['openai-completions',{messages:[{role:'user',content:'prefix '+text}]},'/messages/0/content'],
 ['anthropic-messages',{messages:[{role:'user',content:[{type:'text',text}]}]},'/messages/0/content/0/text'],
 ['openai-responses',{input:[{type:'message',role:'user',content:[{type:'input_text',text}]}]},'/input/0/content/0/text'],
 ['azure-openai-responses',{input:text},'/input'],
 ['openai-codex-responses',{input:[{role:'user',content:text}]},'/input/0/content'],
 ['google-generative-ai',{contents:[{role:'user',parts:[{text}]}]},'/contents/0/parts/0/text'],
 ['google-vertex',{contents:[{role:'user',parts:[{text}]}]},'/contents/0/parts/0/text'],
 ]){const r=presence(body,text,api);assert.equal(r.state,'exact-text-present-in-user-field');assert.deepEqual(r.pointers,[pointer]);}});
test('assistant, system, metadata and tool-result quotations never become human text evidence',()=>{for(const [api,body] of [
 ['openai-completions',{messages:[{role:'system',content:text},{role:'assistant',content:text},{role:'tool',content:text}],metadata:text}],
 ['anthropic-messages',{system:text,messages:[{role:'assistant',content:text},{role:'user',content:[{type:'tool_result',content:[{type:'text',text}]}]}]}],
 ['openai-responses',{instructions:text,input:[{role:'assistant',content:text},{type:'function_call_output',output:text}]}],
 ['google-generative-ai',{config:{systemInstruction:text},contents:[{role:'model',parts:[{text}]},{role:'user',parts:[{functionResponse:{response:{text}}},{thought:true,text}]}]}],
 ]){const r=presence(body,text,api);assert.equal(r.state,'not-present-in-recognized-user-fields');assert.deepEqual(r.pointers,[]);}});
test('unknown APIs, malformed envelopes and excessive row counts remain unavailable',()=>{for(const [body,api] of [[{messages:[]},'unknown'],[{messages:'invalid'},'openai-completions'],[{messages:Array(10001).fill({role:'user',content:text})},'openai-completions']])assert.equal(presence(body,text,api).state,'unavailable');assert.equal(presence({messages:[]},'', 'openai-completions').state,'empty');});
test('identical literal text fields remain multiple candidates and output pointers are bounded',()=>{const r=presence({messages:Array(300).fill({role:'user',content:text})},text,'openai-completions');assert.equal(r.state,'exact-text-present-in-user-field');assert.equal(r.pointers.length,256);assert.equal(r.omittedPointers,44);});
