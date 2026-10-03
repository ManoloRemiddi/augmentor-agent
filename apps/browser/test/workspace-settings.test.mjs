// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {settingsSections,appearanceStorageKey,restoreWorkspaceAppearance} from '../extension/workspace-settings.mjs'
import {JSDOM} from 'jsdom'

test('SDK settings cannot offer shared dictation, harness or installation administration',()=>{
 const sections=['dictation','voice','appearance','models','harnesses','prompts','home','memory','support'].map(id=>[id,id])
 assert.equal(settingsSections(sections),sections)
 assert.equal(settingsSections(sections,{id:'legacy'}),sections)
 assert.deepEqual(settingsSections(sections,{sdkProtocol:'augmentor-app/1'}).map(([id])=>id),['voice','appearance','models','prompts','memory'])
})

test('same-origin workspaces restore only their own durable appearance and cannot overwrite standalone settings',()=>{
 const dom=new JSDOM('',{url:'https://fixture.test'}),storage=dom.window.localStorage
 try{
  const first={id:'first',sdkProtocol:'augmentor-app/1'},second={id:'second',sdkProtocol:'augmentor-app/1'}
  storage.setItem('augmentor-theme','dark')
  restoreWorkspaceAppearance(storage,first,{'augmentor-theme':'light','augmentor-expand-thinking':'false','private-token':'never cache'})
  restoreWorkspaceAppearance(storage,second,{'augmentor-theme':'dark','augmentor-expand-thinking':'true'})
  assert.equal(storage.getItem(appearanceStorageKey('augmentor-theme',first)),'light')
  assert.equal(storage.getItem(appearanceStorageKey('augmentor-expand-thinking',first)),'false')
  assert.equal(storage.getItem(appearanceStorageKey('augmentor-expand-thinking',second)),'true')
  assert.equal(storage.getItem('augmentor-theme'),'dark')
  assert.equal([...Array(storage.length)].some((_,i)=>storage.key(i).includes('private-token')),false)
  restoreWorkspaceAppearance(storage,first,{})
  assert.equal(storage.getItem(appearanceStorageKey('augmentor-theme',first)),null,'deleted server preferences clear a stale local cache')
  assert.equal(storage.getItem(appearanceStorageKey('augmentor-expand-thinking',second)),'true')
 }finally{dom.window.close()}
})
