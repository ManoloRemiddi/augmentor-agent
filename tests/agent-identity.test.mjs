// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {soulText,sessionSoul} from '../dist/identity/src/index.js';
import {instructionSnapshot} from '../dist/codex-runtime/src/instructions.js';
import {AccessSettings,nativePolicy,actionNeedsApproval} from '../dist/codex-runtime/src/permissions.js';
import {CodexInteractions} from '../dist/codex-runtime/src/interactions.js';
import {apply} from '../adapters/dsh-identity/index.mjs';
test('shared Soul reaches developer instructions and DSH snapshots survive later edits and reconnects',t=>{
 const root=mkdtempSync(join(tmpdir(),'agent-identity-')),previous=process.env.AUGMENTOR_IDENTITY_DIR;process.env.AUGMENTOR_IDENTITY_DIR=root;
 t.after(()=>{previous===undefined?delete process.env.AUGMENTOR_IDENTITY_DIR:process.env.AUGMENTOR_IDENTITY_DIR=previous;rmSync(root,{recursive:true,force:true});});
 assert.match(soulText(),/Augmentor/);writeFileSync(join(root,'soul.md'),'SYNTHETIC_SOUL_A');
 assert.match(instructionSnapshot().text,/SYNTHETIC_SOUL_A/);
 const hooks={},sections=[];apply({on:(name,fn)=>hooks[name]=fn,effect:fn=>fn(),systemPrompt:{section:s=>sections.push(s),getSectionOrder:()=>0,suppressRuntimeContext:()=>{}}});
 const first={id:'synthetic-first',session:{snapshotEvents:()=>[]}};hooks['agent/created']({agent:first});
 writeFileSync(join(root,'soul.md'),'SYNTHETIC_SOUL_B');assert.equal(sessionSoul(first.id),'SYNTHETIC_SOUL_A');
 const prefix=sections.find(s=>s.complete);assert.match(prefix.text({agent:first}),/SYNTHETIC_SOUL_A/);
 const next={...first,id:'synthetic-next'};hooks['agent/created']({agent:next});assert.match(prefix.text({agent:next}),/SYNTHETIC_SOUL_B/);
 const historical={id:'synthetic-historical',session:{snapshotEvents:()=>[{type:'user/message'}]}};assert.doesNotMatch(prefix.text({agent:historical}),/SYNTHETIC_SOUL_B/);
 writeFileSync(join(root,'soul.md'),'x'.repeat(32769));assert.throws(()=>soulText(),/32 KiB/);
});
test('Codex access defaults to full, preserves persisted choices and rejects stale writes',t=>{
 const root=mkdtempSync(join(tmpdir(),'agent-access-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
 const settings=new AccessSettings(join(root,'access.json'));assert.equal(settings.read().defaultPreset,'danger-full-access');
 const input={ns:'permission',expectedRevision:0,ops:[{op:'set',path:['defaultPreset'],value:'read-only'}]};settings.mutate(input);
 assert.equal(new AccessSettings(settings.path).read().defaultPreset,'read-only');assert.throws(()=>settings.mutate(input),/changed elsewhere/);
 assert.deepEqual(nativePolicy('danger-full-access'),{approvalPolicy:'never',sandbox:'danger-full-access'});
 assert.deepEqual(nativePolicy('workspace-write'),{approvalPolicy:'on-request',sandbox:'read-only'});
 assert.deepEqual(nativePolicy('read-only'),{approvalPolicy:'never',sandbox:'read-only'});
 assert.equal(actionNeedsApproval('memory_recall'),false);assert.equal(actionNeedsApproval('browser_snapshot'),false);assert.equal(actionNeedsApproval('browser_click'),true);assert.equal(actionNeedsApproval('home_set'),true);
});
test('custom tool approval uses a fresh presenter capability and declines without a presenter',async()=>{
 const approvals=new CodexInteractions(),frames=[];const request={id:1,method:'item/tool/call',params:{turnId:'synthetic-turn',callId:'synthetic-call',tool:'browser_click',arguments:{selector:'synthetic'}}};
 assert.deepEqual(await approvals.tool('synthetic-chat',request),{decision:'cancel'});
 approvals.attach('synthetic-presenter','synthetic-chat',frame=>frames.push(frame));const pending=approvals.tool('synthetic-chat',request),frame=frames[0];
 assert.equal(frame.method,'approval/requested');approvals.answer(frame.rpcId,'synthetic-chat',{sessionId:'synthetic-chat',approvalId:frame.rpcId,outcome:'allowed-once'});assert.deepEqual(await pending,{decision:'accept'});approvals.close();
});
