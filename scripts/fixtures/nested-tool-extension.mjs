// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Independently authored SDK fixture, admitted only by harness-ui-proof's explicit flag.
import {existsSync,writeFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
export default function(pi){
 // The fixture owner releases this final-request barrier before shutdown.
 const finalRelease=process.env.AUGMENTOR_HARNESS_PROOF_NESTED_FINAL_RELEASE;let requests=0;
 if(finalRelease)pi.on('before_provider_request',async()=>{if(++requests!==3)return;writeFileSync(join(dirname(finalRelease),'nested-final-started'),'held',{mode:0o600});while(!existsSync(finalRelease))await delay(25);});
 const parameters={type:'object',properties:{path:{type:'string'},label:{type:'string'}},required:['path','label']};
 pi.registerTool({name:'fixture_outer',label:'Authored outer tool',description:'Run an isolated nested read, held child and explicit failed child.',parameters,async execute(_id,args,_signal,_update,ctx){
  const inner=await ctx.executeTool('fixture_inner',args);if(inner.isError)throw Error('Authored inner tool failed.');
  const failed=await ctx.executeTool('fixture_fail',{label:args.label});
  return {content:[{type:'text',text:'Authored nested chain completed: '+args.label+'. Failed child observed: '+failed.isError}],details:{}};
 }});
 pi.registerTool({name:'fixture_inner',label:'Authored inner tool',description:'Call the real SDK read and an authored held child.',parameters,async execute(_id,args,_signal,_update,ctx){
  const read=await ctx.executeTool('read',{path:args.path});if(read.isError)throw Error('Authored nested read failed.');
  const wait=await ctx.executeTool('fixture_wait',{label:args.label});if(wait.isError)throw Error('Authored held child failed.');
  return {content:read.result.content,details:{}};
 }});
 pi.registerTool({name:'fixture_wait',label:'Authored held child',description:'Wait for an isolated fixture release or SDK cancellation.',parameters:{type:'object',properties:{label:{type:'string'}},required:['label']},async execute(_id,args,signal){
  const release=process.env.AUGMENTOR_HARNESS_PROOF_NESTED_RELEASE;if(!release)throw Error('Authored release path unavailable.');
  writeFileSync(join(dirname(release),'nested-wait-started'),args.label,{mode:0o600});
  while(!existsSync(release))await delay(25,undefined,{signal});
  return {content:[{type:'text',text:'Held child released: '+args.label}],details:{}};
 }});
 pi.registerTool({name:'fixture_fail',label:'Authored failed child',description:'Return one deliberate tool error in the isolated fixture.',parameters:{type:'object',properties:{label:{type:'string'}},required:['label']},async execute(){throw Error('Authored nested failure.');}});
}
