// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {mkdtempSync,rmSync} from 'node:fs'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {describeWorkspace} from '../services/workspaces/capabilities.mjs'
import {preferences} from '../services/workspaces/profiles.mjs'
import {guardWorkspaceMethod} from '../services/workspaces/policy.mjs'
import {definitions} from '../dist/desktop/src/index.js'

test('workspace capabilities separate platform support, app grants and voice opt-in',t=>{
 const dir=mkdtempSync(join(tmpdir(),'workspace-capabilities-')),before=process.env.XDG_STATE_HOME
 process.env.XDG_STATE_HOME=dir
 t.after(()=>{if(before===undefined)delete process.env.XDG_STATE_HOME;else process.env.XDG_STATE_HOME=before;rmSync(dir,{recursive:true,force:true})})
 const profile={id:'fixture',sdkProtocol:'augmentor-app/1',policy:{tools:[],voice:false,sharedSettings:false}}
 let description=describeWorkspace(profile,{platform:'win32',desktop:{available:false}})
 assert.equal(description.platform,'win32');assert.equal(description.readinessVerified,false)
 assert.equal(description.features['application-context'].binding,'session-selection');
 assert.equal(describeWorkspace({...profile,harness:'codex'}).features['application-context'].binding,'operation');
 assert.equal(description.features['computer-use'].state,'unsupported')
 assert.equal(description.features['dictation-settings'].state,'denied')
 assert.throws(()=>guardWorkspaceMethod(profile,'augmentor/surface',{action:'dictation',method:'enable'}),/cannot administer/)
 for(const action of ['dual.configure','configure','describe','retain','search'])assert.throws(()=>guardWorkspaceMethod(profile,'augmentor/memory',{action}),/Shared memory administration/)
 assert.doesNotThrow(()=>guardWorkspaceMethod(profile,'augmentor/memory',{action:'dual.recall',session:'dsh:fixture'}))
 assert.equal(description.features.voice.state,'disabled')
 description=describeWorkspace(profile,{desktop:{available:true}})
 assert.equal(description.features['computer-use'].state,'denied')
 profile.policy.tools=[definitions[0].name]
 description=describeWorkspace(profile,{desktop:{available:true}})
 assert.equal(description.features['computer-use'].state,'supported')
 assert.deepEqual(description.features['computer-use'].tools,profile.policy.tools)
 assert.equal(description.features['computer-use'].requiresUserConsent,true)
 preferences(profile,{set:{'experimental-voice-enabled':true}})
 assert.equal(describeWorkspace(profile).features.voice.state,'supported')
 preferences(profile,{set:{'experimental-voice-enabled':false}})
 assert.equal(describeWorkspace(profile).features.voice.state,'disabled')
})
