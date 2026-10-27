// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {foregroundShellSeconds,piShellDeadlines} from '../dist/runtime/src/shell-deadlines.js';
test('foreground deadline defaults are configurable without changing explicit deadlines',()=>{
 assert.equal(foregroundShellSeconds({}),120);assert.equal(foregroundShellSeconds({AUGMENTOR_FOREGROUND_SHELL_SECONDS:'0'}),0);
 assert.equal(foregroundShellSeconds({AUGMENTOR_FOREGROUND_SHELL_SECONDS:'invalid'}),120);
 const hooks=new Map();piShellDeadlines(120)({on:(name,handler)=>hooks.set(name,handler)});
 for(const name of ['bash','powershell']){
  const event={toolName:name,input:{command:'synthetic command'},parentToolCallId:'codemode/1'};hooks.get('tool_call')(event);assert.equal(event.input.timeout,120);
  event.input.timeout=900;hooks.get('tool_call')(event);assert.equal(event.input.timeout,900);
 }
 const other={toolName:'read',input:{path:'fixture'}};hooks.get('tool_call')(other);assert.equal(other.input.timeout,undefined);
 const disabled=new Map();piShellDeadlines(0)({on:(name,handler)=>disabled.set(name,handler)});const event={toolName:'bash',input:{command:'fixture'}};disabled.get('tool_call')(event);assert.equal(event.input.timeout,undefined);
});
test('timeout feedback retains partial evidence and structured output without replay',()=>{
 const hooks=new Map();piShellDeadlines(120)({on:(name,handler)=>hooks.set(name,handler)});
 const content=[{type:'text',text:'partial output\nCommand timed out after 120 seconds'}],structuredContent={output:'partial output',exit_code:143};
 const result=hooks.get('tool_result')({toolName:'bash',isError:true,content,structuredContent});
 assert.equal(result.content[0],content[0]);assert.equal(result.structuredContent,structuredContent);assert.match(result.content[1].text,/not a rollback/);
 assert.equal(hooks.get('tool_result')({toolName:'bash',isError:false,content}),undefined);
});
