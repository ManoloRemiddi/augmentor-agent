// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {homedir} from 'node:os';

const require=createRequire((process.env.DSH_INSTALL_ROOT ?? homedir()+'/.local/node/lib/node_modules/@deepseek-ai/dsh')+'/package.json');
const version=require('./package.json').version;
const load=()=>import(pathToFileURL(require.resolve('@deepseek-ai/dsh-session-format-v3-to-v4')).href);
const header={version:3,id:'synthetic',createdAt:1,isSeeded:false,delegationDepth:0};
const id='12345678-1234-1234-1234-123456789abc';
const event=(type,data,extras={})=>({type,seq:0,time:2,data,...extras});
async function migrate(events){
  const m=await load(), declaration=m.createSessionFormatV3ToV4([]), targetHeader=declaration.migrateHeader(header);
  const stage=declaration.createStage({sourceHeader:header,targetHeader,sourceInheritedEventCount:0,sourceKind:'decoded'});
  const output=[],context={emitEvent:e=>output.push(e),emitRun:()=>assert.fail('Unexpected compact run')};
  events.forEach((e,seq)=>stage.transformEvent({...e,seq},context));
  return {header:targetHeader,inheritedEventCount:stage.finish(context),events:output};
}
test('legacy Augmentor notices gain one attributed opener and retain reference coordinates', {skip:version!=='0.2.0-rc.2'},async()=>{
  const m=await load();const a=await migrate([
    event('command/done',{commandId:id,kind:'success',text:'Harness: synthetic status'}),
    event('user/message',{id:'m',role:'user',source:{kind:'user'},content:[{type:'text',text:'fixture'}]},{surfaceOp:'append'}),
    event('user/message',{id:'n',role:'user',source:{kind:'user'},content:[{type:'text',text:'edited'}]},{surfaceOp:{op:'replace',startSeq:1,endSeq:1},sourceEventSeqs:[1]}),
  ]);
  assert.equal(a.events[0].type,'command/run');assert.equal(a.events[0].data.source.kind,'plugin:augmentor-execution');
  assert.equal(a.events[1].data.text,'Harness: synthetic status');
  assert.deepEqual(a.events[3].sourceEventSeqs,[2]);assert.equal(a.events[3].surfaceOp.startSeq,2);
  m.restoreReleasedV4Artifact(a,new Set(a.events.map(e=>e.type)));
});
test('paired commands are preserved and unrelated orphan completions remain rejected', {skip:version!=='0.2.0-rc.2'},async()=>{
  const m=await load(), a=await migrate([event('command/run',{commandId:id,name:'fixture',source:{kind:'user'}}),event('command/done',{commandId:id,kind:'success',text:'Harness: fixture'})]);
  assert.equal(a.events.length,2);m.restoreReleasedV4Artifact(a,new Set(['command/run','command/done']));
  const bad=await migrate([event('command/done',{commandId:id,kind:'success',text:'unrelated completion'})]);
  assert.throws(()=>m.restoreReleasedV4Artifact(bad,new Set(['command/done'])),/command/);
});
