// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,statSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {modelSettings,loadModelSettings,saveModelSettings,publicModelSettings} from '../settings.mjs';
const selected={model:'fixture',modelUrl:'https://model.example.com/v1',contextWindow:16384,key:'fixture-credential'};
test('endpoint changes never inherit another provider credential and LAN HTTP requires explicit choice',()=>{
 assert.throws(()=>modelSettings({...selected,modelUrl:'https://different.example.com/v1',key:undefined},selected),/explicit credential/);
 assert.throws(()=>modelSettings({...selected,modelUrl:'http://nas.local:11434/v1'}),/private LAN/);
 assert.equal(modelSettings({...selected,modelUrl:'http://nas.local:11434/v1',allowLanHttp:true,key:''}).key,'');
 assert.throws(()=>modelSettings({...selected,modelUrl:'https://user:secret@model.example.com/v1'}));
});
test('model choice and secret persist atomically and public settings never contain the credential',t=>{
 const stateDir=mkdtempSync(join(tmpdir(),'home-model-')),config={stateDir,...selected};t.after(()=>rmSync(stateDir,{recursive:true,force:true}));
 saveModelSettings(config,modelSettings(selected));assert.deepEqual(loadModelSettings(config),modelSettings(selected));
 assert.equal(statSync(join(stateDir,'model.json')).mode&0o777,0o600);
 assert.ok(!JSON.stringify(publicModelSettings(config)).includes(selected.key));assert.equal(publicModelSettings(config).fallback,'disabled');
});
