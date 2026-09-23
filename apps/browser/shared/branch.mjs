// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import {pythonExecutable,componentEnvironment} from '../../../dist/platform/src/index.js'
export function dshBranch(params) {
  return new Promise((resolve,reject)=>{
    const child=spawn(pythonExecutable(),[fileURLToPath(new URL('../../../services/dsh/branch.py',import.meta.url))],{stdio:['pipe','pipe','ignore'],env:componentEnvironment()})
    let output=''
    const timer=setTimeout(()=>{child.kill();reject(new Error('Branch outcome is unknown. Check DSH chats before retrying.'))},90000)
    child.on('error',error=>{clearTimeout(timer);reject(error)})
    child.stdin.on('error',()=>{})
    child.stdout.on('data',data=>{output+=data;if(output.length>65536)child.kill()})
    child.on('close',code=>{clearTimeout(timer);try{const result=JSON.parse(output);if(code||result.error)reject(new Error(result.error??'DSH branch failed'));else resolve(result)}catch{reject(new Error('Branch outcome is unknown. Check DSH chats before retrying.'))}})
    child.stdin.end(JSON.stringify(params))
  })
}
