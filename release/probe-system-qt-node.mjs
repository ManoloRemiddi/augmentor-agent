// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Actual fast selection in a marked source-only fixture; no product or device use.
import assert from 'node:assert/strict'
import {readFileSync,writeFileSync,lstatSync} from 'node:fs'
import {userInfo} from 'node:os'
import {resolve,join,dirname} from 'node:path'
import {createHash} from 'node:crypto'
import {pathToFileURL} from 'node:url'

const app=resolve(process.argv[2]),expected=process.argv[3]
assert.equal(userInfo().uid,1000)
assert(app.startsWith('/tmp/augmentor-proof/system-node'))
const marker=readFileSync('/etc/augmentor-package-test-container','utf8')
assert(['Owned Arch 20261001 Augmentor package guard synthetic qualification\n','Owned Leap 16 Augmentor RPM synthetic qualification\n'].includes(marker))
assert.equal(process.version,'v24.19.0')
const {declaredLinuxPython,pythonExecutable,componentEnvironment}=await import(pathToFileURL(join(app,'dist/platform/src/index.js')))
const {voicePython}=await import(pathToFileURL(join(app,'apps/browser/shared/voice-client.mjs')))
const before=readFileSync(join(dirname(dirname(expected)),'augmentor-python-runtime.json'))
assert.equal(process.env.AUGMENTOR_PYTHON,expected)
assert.equal(declaredLinuxPython(app),expected)
assert.equal(pythonExecutable(),expected)
assert.equal(componentEnvironment().AUGMENTOR_PYTHON,expected)
assert.equal(voicePython(app),expected)
const implicit={...process.env};delete implicit.AUGMENTOR_PYTHON
assert.equal(declaredLinuxPython(app,implicit),expected)
assert.equal(voicePython(app,implicit),expected)
const negatives=[]
const refuse=(name,fn,pattern)=>{assert.throws(fn,pattern);negatives.push(name)}
refuse('explicit system Python',()=>declaredLinuxPython(app,{...process.env,AUGMENTOR_PYTHON:'/usr/bin/python3'}),/does not match/)
for(const key of ['LD_PRELOAD','LD_AUDIT','LD_LIBRARY_PATH'])refuse(key,()=>declaredLinuxPython(app,{...process.env,[key]:'/unreviewed'}),/loader override/)
const manifest=join(dirname(dirname(expected)),'system-qt-inventory.json'),saved=readFileSync(manifest)
try{
  const changed=Buffer.from(saved);changed[changed.length-2]^=1;writeFileSync(manifest,changed)
  refuse('changed native manifest',()=>declaredLinuxPython(app),/manifest or import receipt changed/)
  refuse('Browser manifest refusal',()=>voicePython(app),/manifest or import receipt changed/)
}finally{writeFileSync(manifest,saved)}
assert.equal(declaredLinuxPython(app),expected)
assert.deepEqual(readFileSync(join(dirname(dirname(expected)),'augmentor-python-runtime.json')),before)
assert.equal(lstatSync(dirname(dirname(expected))).mode&0o077,0)
console.log(JSON.stringify({format:'augmentor-system-qt-node-selection-proof/1',profile:JSON.parse(readFileSync(join(app,'linux-python-runtime.json'),'utf8')).profile,node:process.version,explicitAndImplicitSelectionPassed:true,platformAndBrowserAgree:true,refusals:negatives,receiptBytesPreserved:true,manifestRestored:true,compiledPythonSelectorSha256:createHash('sha256').update(readFileSync(join(app,'dist/platform/src/python.js'))).digest('hex'),compiledPlatformSha256:createHash('sha256').update(readFileSync(join(app,'dist/platform/src/index.js'))).digest('hex'),browserVoiceSourceSha256:createHash('sha256').update(readFileSync(join(app,'apps/browser/shared/voice-client.mjs'))).digest('hex'),installedProductTested:false,graphicalBrowserTested:false,physicalAudioTested:false,dependencyMaintenanceQualified:false,publicReleaseQualified:false}))
