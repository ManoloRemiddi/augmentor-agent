// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// A private Unix endpoint for the existing admission protocol. No install commands.
import {createServer} from 'node:net'
import {chmodSync,lstatSync,unlinkSync,fstatSync,closeSync} from 'node:fs'
import {join,resolve} from 'node:path'

export const UNIX_CONTROL='augmentor-unix-maintenance/1'

export function releaseStartup(runtime) {
 const value=process.env.AUGMENTOR_UNIX_STARTUP_FD
 delete process.env.AUGMENTOR_UNIX_STARTUP_FD
 if(value===undefined)return
 if(!/^[0-9]{1,10}$/.test(value)||Number(value)<3)throw Error('Invalid inherited startup observation.')
 const fd=Number(value),held=fstatSync(fd),expected=lstatSync(join(runtime,'startup.lock'))
 if(!held.isFile()||held.uid!==process.getuid()||(held.mode&0o077)||held.nlink!==1||
    !expected.isFile()||expected.dev!==held.dev||expected.ino!==held.ino)
  throw Error('The inherited startup observation belongs to another file.')
 closeSync(fd)
}

export async function unixControl({runtime,root,component,control,onCommitted}) {
 if(!['linux','darwin'].includes(process.platform))throw Error('Unix control requires Linux or macOS.')
 if(!['dsh','browser'].includes(component)||typeof control!=='function'||typeof onCommitted!=='function')
  throw Error('A supported component and normal shutdown callback are required.')
 const directory=lstatSync(runtime)
 if(!directory.isDirectory()||directory.uid!==process.getuid()||(directory.mode&0o077))
  throw Error('Maintenance requires a private runtime directory owned by this user.')
 const endpoint=join(runtime,`augmentor-${component}-${process.pid}.sock`)
 const identity={protocol:UNIX_CONTROL,pid:process.pid,buildRoot:resolve(root),maintenanceAdmission:1,component}
 let owned=null,closed=false,committed=false
 const peers=new Set()
 const commit=()=>{if(!committed){committed=true;onCommitted()}}
 const server=createServer(socket=>{
  peers.add(socket);socket.once('close',()=>peers.delete(socket));socket.on('error',()=>{})
  socket.setTimeout(15000,()=>socket.destroy())
  let buffer=Buffer.alloc(0),started=false
  socket.on('data',chunk=>{
   if(started){socket.destroy();return}
   buffer=Buffer.concat([buffer,chunk])
   if(buffer.length>16384){socket.destroy();return}
   const end=buffer.indexOf(10)
   if(end<0)return
   started=true
   void (async()=>{
    let shuttingDown=false,response
    try{
     if(end!==buffer.length-1)throw Error('Use one maintenance request per connection.')
     const request=JSON.parse(buffer.subarray(0,end))
     if(!request||typeof request!=='object'||Array.isArray(request)||request.protocol!==UNIX_CONTROL)
      throw Error('Unsupported Unix maintenance protocol.')
     if(request.kind==='describe'&&Object.keys(request).sort().join(',')==='kind,protocol')response={...identity,ok:true}
     else{
      if(request.kind!=='maintenance'||Object.keys(request).sort().join(',')!=='kind,method,params,protocol')
       throw Error('Unsupported Unix maintenance fields.')
      const result=await control(request.method,request.params)
      shuttingDown=request.method==='host.maintenance.commit'&&result?.phase==='closing'
      response={...identity,ok:true,result}
     }
    }catch{response={...identity,ok:false,error:'Maintenance was refused; work was preserved. No request was replayed.'}}
    if(shuttingDown)socket.once('close',commit)
    if(socket.destroyed){if(shuttingDown)commit();return}
    socket.end(JSON.stringify(response)+'\n',shuttingDown?commit:undefined)
   })().catch(()=>socket.destroy())
  })
 })
 await new Promise((ready,failed)=>{server.once('error',failed);server.listen(endpoint,()=>{server.off('error',failed);ready()})})
 try{
  chmodSync(endpoint,0o600)
  owned=lstatSync(endpoint)
  if(!owned.isSocket()||owned.uid!==process.getuid())throw Error('The new control endpoint changed during registration.')
 }catch(error){server.close();throw error}
 server.on('error',()=>{})
 return {endpoint,async close(){
  if(closed)return
  closed=true
  for(const peer of peers)peer.destroy()
  await new Promise(done=>server.close(done))
  try{
   const current=lstatSync(endpoint)
   if(current.isSocket()&&current.dev===owned.dev&&current.ino===owned.ino)unlinkSync(endpoint)
  }catch(error){if(error.code!=='ENOENT')throw error}
 }}
}
