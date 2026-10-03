// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {settingsSections} from '../extension/workspace-settings.mjs'

test('SDK settings cannot offer shared dictation, harness or installation administration',()=>{
 const sections=['dictation','voice','appearance','models','harnesses','prompts','home','memory','support'].map(id=>[id,id])
 assert.equal(settingsSections(sections),sections)
 assert.equal(settingsSections(sections,{id:'legacy'}),sections)
 assert.deepEqual(settingsSections(sections,{sdkProtocol:'augmentor-app/1'}).map(([id])=>id),['voice','appearance','models','prompts','memory'])
})
