// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync,mkdtempSync,symlinkSync,rmSync,writeFileSync} from 'node:fs'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {execFileSync} from 'node:child_process'
import {declaredLinuxPython,pythonRuntimeIdentity} from '../dist/platform/src/index.js'
import {voicePython} from '../apps/browser/shared/voice-client.mjs'

test('Python and Node select the same immutable identity for each declared policy',()=>{
  for(const file of ['ubuntu24.04-python.json','ubuntu24.04-python-voice.json','ubuntu24.04-python-source-qt-voice.json','opensuse-leap16.0-python-voice.json','arch20261001-python-voice.json']){
    const policy=JSON.parse(readFileSync(new URL('../release/'+file,import.meta.url),'utf8'))
    const expected=execFileSync('/usr/bin/python3',['-c',`import importlib.util,json,sys
spec=importlib.util.spec_from_file_location('runtime','scripts/linux-python-runtime.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
print(m.identity(json.loads(sys.stdin.read())))`],{input:JSON.stringify(policy),encoding:'utf8'}).trim()
    assert.equal(pythonRuntimeIdentity(policy),expected)
    policy.wheels.reverse()
    assert.equal(pythonRuntimeIdentity(policy),expected)
  }
})
test('system Qt identity binds the qualified package inventory independently of wheel bytes',()=>{
  for(const file of ['opensuse-leap16.0-python-voice.json','arch20261001-python-voice.json']){
    const policy=JSON.parse(readFileSync(new URL('../release/'+file,import.meta.url),'utf8'))
    const before=pythonRuntimeIdentity(policy)
    policy.systemQtStack.sha256='0'.repeat(64)
    assert.notEqual(pythonRuntimeIdentity(policy),before)
  }
})
test('source runtime identity binds native payload independently of wheel bytes',()=>{
  const policy=JSON.parse(readFileSync(new URL('../release/ubuntu24.04-python-source-qt-voice.json',import.meta.url),'utf8'))
  const before=pythonRuntimeIdentity(policy)
  policy.sourceQt.manifestSha256='0'.repeat(64)
  assert.notEqual(pythonRuntimeIdentity(policy),before)
})
test('broken declared policy cannot silently select system Python or an explicit override',{skip:process.platform!=='linux'},()=>{
  const folder=mkdtempSync(join(tmpdir(),'augmentor-python-selection-'))
  try{
    symlinkSync(join(folder,'missing'),join(folder,'linux-python-runtime.json'))
    assert.throws(()=>declaredLinuxPython(folder),/regular artifact/)
    assert.throws(()=>voicePython(folder,{AUGMENTOR_PYTHON:'/usr/bin/python3'}),/regular artifact/)
  }finally{rmSync(folder,{recursive:true,force:true})}
})
test('distro Qt policies refuse absent, cross-target and broadened contracts before host/runtime selection',{skip:process.platform!=='linux'},()=>{
  const folder=mkdtempSync(join(tmpdir(),'augmentor-system-qt-policy-'))
  try{
    for(const file of ['opensuse-leap16.0-python-voice.json','arch20261001-python-voice.json']){
      const original=JSON.parse(readFileSync(new URL('../release/'+file,import.meta.url),'utf8'))
      const cases=[
        value=>delete value.systemQtStack,
        value=>value.systemQtStack.packageManager='apt',
        value=>value.systemQtStack.file='../outside.json',
        value=>value.systemQtStack.bytes=0,
        value=>value.systemQtStack.sha256='wrong',
        value=>value.pythonAbi=[3,12],
        value=>value.target='ubuntu24.04-amd64',
        value=>value.sourceQt={},
        value=>value.wheels.push(value.wheels[0]),
        value=>value.wheels[0].url='https://unreviewed.invalid/wheel.whl',
      ]
      for(const alter of cases){
        const value=structuredClone(original);alter(value)
        writeFileSync(join(folder,'linux-python-runtime.json'),JSON.stringify(value))
        assert.throws(()=>declaredLinuxPython(folder),/contract|policy|source Qt|wheel record/)
        assert.throws(()=>voicePython(folder,{AUGMENTOR_PYTHON:'/usr/bin/python3'}),/contract|policy|source Qt|wheel record/)
      }
    }
  }finally{rmSync(folder,{recursive:true,force:true})}
})
