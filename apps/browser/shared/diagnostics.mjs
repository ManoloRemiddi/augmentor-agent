// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.
import {constants,openSync,closeSync,writeSync,mkdirSync,lstatSync,chmodSync,readdirSync,unlinkSync,rmdirSync} from 'node:fs'
import {join} from 'node:path'
import {randomUUID} from 'node:crypto'
import {diagnosticFrame} from '../extension/diagnostics.mjs'

const categories=['plugin handshake failed','plugin handshake:','PROTOCOL MISMATCH','plugin ws connected','unexpected plugin name','plugin hello:','plugin ws closed','plugin ws error','plugin ws stale','plugin handshake reports','stream error','downlink open','downlink closed','downlink error','reconnect failed','shutdown requested','dropping frame','history shaped','list shaped','DSH app ready','DSH app not reachable','action-channel token source','bad frame','extension port closed','pipe ']
export function diagnosticCategory(value){return categories.find(prefix=>typeof value==='string'&&value.startsWith(prefix))??'event'}
export class MetadataLog {
  constructor(directory,enabled=false){this.directory=directory;this.enabled=enabled;this.bytes=0;this.fd=null;this.capped=false}
  write(entry){
    if(!this.enabled||this.capped)return
    try{
      const record={at:Date.now(),kind:['log','respond','plugin','ext->pipe'].includes(entry.kind)?entry.kind:'event',frame:diagnosticFrame(entry.msg)}
      if(entry.category)record.category=diagnosticCategory(entry.category)
      const line=Buffer.from(JSON.stringify(record)+'\n')
      if(this.bytes+line.length>1024*1024){this.capped=true;this.close();return}
      if(this.fd===null){
        mkdirSync(this.directory,{recursive:true,mode:0o700});const stat=lstatSync(this.directory)
        if(stat.isSymbolicLink()||!stat.isDirectory()||stat.uid!==process.getuid())throw Error('Invalid diagnostics directory')
        chmodSync(this.directory,0o700)
        const lock=join(this.directory,'.metadata-rotation')
        try{mkdirSync(lock,{mode:0o700})}catch{return} // Never compete with another rotation.
        try{
          const files=readdirSync(this.directory).filter(n=>/^metadata-\d{13}-[a-f0-9-]{36}\.jsonl$/.test(n)).sort().reverse()
          for(const [index,name] of files.entries()){
            const file=join(this.directory,name),info=lstatSync(file)
            if(info.isFile()&&!info.isSymbolicLink()&&info.uid===process.getuid()&&(index>=4||Date.now()-info.mtimeMs>7*86400000))unlinkSync(file)
          }
          this.fd=openSync(join(this.directory,`metadata-${Date.now()}-${randomUUID()}.jsonl`),constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600)
        }finally{rmdirSync(lock)}
      }
      writeSync(this.fd,line);this.bytes+=line.length
    }catch{this.capped=true;this.close()}
  }
  close(){if(this.fd!==null){closeSync(this.fd);this.fd=null}}
}
