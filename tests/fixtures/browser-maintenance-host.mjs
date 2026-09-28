// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Qualification-only framing proxy. Real product requests reach the unmodified
// native host; the disposable profile's private files inject maintenance RPCs.
import {spawn} from 'node:child_process'
import {readFileSync,writeFileSync,unlinkSync,renameSync} from 'node:fs'
import {join} from 'node:path'
const [entry,directory]=process.argv.slice(2)
const child=spawn(process.execPath,[entry],{stdio:['pipe','pipe','inherit']})
const request=join(directory,`${process.pid}-request.json`),response=join(directory,`${process.pid}-response.json`)
writeFileSync(join(directory,'host.json'),JSON.stringify({pid:process.pid}),{mode:0o600})
function send(stream,value) { const body=Buffer.from(JSON.stringify(value)),head=Buffer.alloc(4);head.writeUInt32LE(body.length);stream.write(Buffer.concat([head,body])) }
function frames(stream,receive) {
  let buffer=Buffer.alloc(0)
  stream.on('data',chunk=>{
    buffer=Buffer.concat([buffer,chunk])
    while(buffer.length>=4){const size=buffer.readUInt32LE(0);if(size>1024*1024)throw Error('Invalid fixture frame');if(buffer.length<size+4)return;const value=JSON.parse(buffer.subarray(4,size+4));buffer=buffer.subarray(size+4);receive(value)}
  })
}
frames(child.stdout,value=>send(process.stdout,value))
frames(process.stdin,value=>{
  if(typeof value.id==='string'&&value.id.startsWith('maintenance-proof-')){
    writeFileSync(response+'.tmp',JSON.stringify(value),{mode:0o600});renameSync(response+'.tmp',response)
  }else send(child.stdin,value)
})
const timer=setInterval(()=>{
  let value
  try{value=JSON.parse(readFileSync(request,'utf8'));unlinkSync(request)}catch(error){if(error.code==='ENOENT')return;throw error}
  if(!value.id?.startsWith('maintenance-proof-')||!['augmentor/maintenance','browser/execute'].includes(value.method))throw Error('Invalid fixture control request')
  send(process.stdout,value)
},30)
process.stdin.on('end',()=>{clearInterval(timer);child.stdin.end()})
child.stdin.on('error',()=>{clearInterval(timer);process.stdin.destroy()})
child.on('close',code=>{clearInterval(timer);process.stdin.destroy();process.exitCode=code??1;process.stdout.end()})
