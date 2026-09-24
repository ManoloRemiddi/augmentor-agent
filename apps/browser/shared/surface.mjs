// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
import {voicePython} from './voice-client.mjs'
export function surfaceRequest(value,root=fileURLToPath(new URL('../../../',import.meta.url))){
 return new Promise((resolve,reject)=>{
  const child=spawn(voicePython(root),[path.join(root,'services/surface/browser.py')],{stdio:['pipe','pipe','ignore'],env:{...process.env,AUGMENTOR_WINDOW_ID:'main'}})
  let output='';const timer=setTimeout(()=>{child.kill();reject(Error('Desktop operation timed out; your draft was preserved.'))},75000)
  child.on('error',error=>{clearTimeout(timer);reject(error)});child.stdin.on('error',()=>{})
  child.stdout.on('data',data=>{output+=data;if(output.length>131072)child.kill()})
  child.on('close',code=>{clearTimeout(timer);try{const result=JSON.parse(output);if(code||result.error)throw Error(result.error||'Desktop operation failed');resolve(result)}catch(error){reject(error)}})
  child.stdin.end(JSON.stringify(value))
 })
}
