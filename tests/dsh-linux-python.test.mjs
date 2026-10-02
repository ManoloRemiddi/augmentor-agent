// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test'
import assert from 'node:assert/strict'
import {mkdtemp,writeFile,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {runDesktop} from '../adapters/dsh-desktop/linux-support.mjs'

test('DSH Linux helpers execute the selected interpreter with the shared environment', {skip:process.platform!=='linux'}, async () => {
  const directory=await mkdtemp(join(tmpdir(),'augmentor selected python '))
  const selected=join(directory,'python')
  const previous=process.env.AUGMENTOR_PYTHON
  try {
    await writeFile(selected,`#!/usr/bin/python3
import json,os,sys
print(json.dumps({'request':json.load(sys.stdin),'python':os.environ.get('AUGMENTOR_PYTHON'),'noBytecode':os.environ.get('PYTHONDONTWRITEBYTECODE'),'backend':sys.argv[1]}))
`,{mode:0o700})
    process.env.AUGMENTOR_PYTHON=selected
    const result=await runDesktop({action:'profile'},new AbortController().signal)
    assert.equal(result.python,selected)
    assert.equal(result.noBytecode,'1')
    assert.deepEqual(result.request,{action:'profile'})
    assert.match(result.backend,/services\/desktop\/linux-support\/desktop\.py$/)
    process.env.AUGMENTOR_PYTHON=join(directory,'missing')
    await assert.rejects(runDesktop({action:'profile'},new AbortController().signal),{code:'ENOENT'})
  } finally {
    if(previous===undefined)delete process.env.AUGMENTOR_PYTHON
    else process.env.AUGMENTOR_PYTHON=previous
    await rm(directory,{recursive:true,force:true})
  }
})
