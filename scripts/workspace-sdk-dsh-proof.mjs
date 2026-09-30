// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Real DSH ToolRuntime and scoped Cordis context; synthetic tools, no model or user data.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import {apply} from '../adapters/dsh-workspace/policy.mjs';
const require=createRequire(join(resolve(process.argv[2]),'package.json'));
const load=name=>import(pathToFileURL(require.resolve(name)).href);
const {Context}=await load('@deepseek-ai/cordis'),{default:SystemPrompt}=await load('@deepseek-ai/dsh-system-prompt'),{default:ToolRuntime,defineTool}=await load('@deepseek-ai/dsh-tools'),{createScope}=await load('@deepseek-ai/dsh-scope');
const dir=mkdtempSync(join(tmpdir(),'sdk-real-dsh-'));process.env.AUGMENTOR_WORKSPACE_PROFILES=dir;
const profile={schemaVersion:1,sdkProtocol:'augmentor-app/1',id:'fixture',name:'Fixture',preset:'augmentor-fixture',cwd:dir,memory:{person:'fixture',project:dir},parentOrigin:'http://127.0.0.1:8765',publicPath:'/augmentor/',policy:{tools:['fixture_read'],voice:false,sharedSettings:false}};
writeFileSync(join(dir,'fixture.json'),JSON.stringify(profile));
const ctx=new Context();let reads=0,writes=0;
try{
 await ctx.plugin(SystemPrompt).await();await ctx.plugin(ToolRuntime).await();
 for(const name of ['fixture_read','fixture_write'])ctx.tools.register(defineTool({name,description:name,parameters:{},output:{schema:{type:'string'},render:(_a,v)=>[{type:'text',text:v}]},execute:async()=>{name==='fixture_read'?reads++:writes++;return 'fixture';}}));
 const agent={id:'fixture-session',session:{header:{agentPreset:profile.preset,cwd:dir}}};
 const scoped=createScope(ctx,agent);agent.ctx=scoped.ctx;await scoped.ctx.plugin({name:'sdk-proof-policy',inject:['tools'],apply},{profileId:'fixture'}).await();
 // A cooperative plugin returning allow cannot undo the monotonic denial.
 ctx.on('tools/pre-execute',async()=>({kind:'allow'}));
 const run=name=>ctx.tools.execute({name,arguments:{},agent,callId:'call-'+name,signal:new AbortController().signal});
 assert.equal((await run('fixture_read')).isError,false);assert.equal((await run('fixture_write')).isError,true);assert.equal(reads,1);assert.equal(writes,0);
 const personal={id:'other',session:{header:{agentPreset:'augmentor-linux-product',cwd:dir}}};
 assert.equal((await ctx.tools.execute({name:'fixture_write',arguments:{},agent:personal,callId:'personal-call',signal:new AbortController().signal})).isError,false);assert.equal(writes,1);
 console.log(JSON.stringify({realDsh:true,allowedTool:true,deniedToolNeverExecuted:true,unrelatedAgentPreserved:true}));
}finally{await ctx.fiber.dispose();rmSync(dir,{recursive:true,force:true});}
