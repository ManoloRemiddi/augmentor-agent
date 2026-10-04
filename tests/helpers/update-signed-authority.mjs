// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Private qualification fixture: temporary in-memory keys and loopback HTTP.
// No installed config changes, signing credentials, installer or model execution.
import http from 'node:http'
import readline from 'node:readline'
import {generateKeyPairSync,sign,createHash} from 'node:crypto'
import {Metadata,Root,Targets,Snapshot,Timestamp,Key,Signature,TargetFile,MetaFile} from '@tufjs/models'
import {UpdateRepository,BoundedFetcher} from '../../services/updates/repository.mjs'

const digest=bytes=>createHash('sha256').update(bytes).digest('hex')
const expiry=()=>new Date(Date.now()+3600000).toISOString()
const keys={}
for(const role of ['root','targets','snapshot','timestamp']){
  const {privateKey,publicKey}=generateKeyPairSync('ed25519')
  const value={keytype:'ed25519',scheme:'ed25519',keyval:{public:Buffer.from(publicKey.export({format:'jwk'}).x,'base64url').toString('hex')}}
  const id=digest(JSON.stringify(value));keys[role]={privateKey,id,key:Key.fromJSON(id,value)}
}
const serialize=(metadata,role)=>{
  metadata.sign(bytes=>new Signature({keyID:keys[role].id,sig:sign(null,bytes,keys[role].privateKey).toString('hex')}))
  return Buffer.from(JSON.stringify(metadata.toJSON()))
}
const root=new Root({version:1,expires:expiry(),consistentSnapshot:false})
for(const role of Object.keys(keys))root.addKey(keys[role].key,role)
const rootBytes=serialize(new Metadata(root),'root')
const files=new Map([['/metadata/root.json',rootBytes]])
const requests=[]
const server=http.createServer((request,response)=>{
  requests.push(request.url)
  if(!files.has(request.url)){response.writeHead(404);response.end();return}
  response.writeHead(200);response.end(files.get(request.url))
})
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve))
const base=`http://127.0.0.1:${server.address().port}/`
const config={root:rootBytes,metadataBaseUrl:base+'metadata/',catalogBaseUrl:base+'targets/',artifactBaseUrl:base}
let cache,release,payload,sequence=0
function publish(releases){
  sequence++
  const catalog=Buffer.from(JSON.stringify({schema:'augmentor-update-catalog/1',releases}))
  files.set('/targets/catalog/preview.json',catalog)
  const artifact=release.artifacts[0]
  files.set('/'+artifact.targetPath,payload)
  const targets=new Targets({version:sequence,expires:expiry(),targets:{
    'catalog/preview.json':new TargetFile({path:'catalog/preview.json',length:catalog.length,hashes:{sha256:digest(catalog)}}),
    [artifact.targetPath]:new TargetFile({path:artifact.targetPath,length:payload.length,hashes:{sha256:digest(payload)}}),
  }})
  const targetsBytes=serialize(new Metadata(targets),'targets')
  const snapshot=serialize(new Metadata(new Snapshot({version:sequence,expires:expiry(),meta:{
    'targets.json':new MetaFile({version:sequence,length:targetsBytes.length,hashes:{sha256:digest(targetsBytes)}}),
  }})),'snapshot')
  const timestamp=serialize(new Metadata(new Timestamp({version:sequence,expires:expiry(),
    snapshotMeta:new MetaFile({version:sequence,length:snapshot.length,hashes:{sha256:digest(snapshot)}})})),'timestamp')
  files.set('/metadata/targets.json',targetsBytes);files.set('/metadata/snapshot.json',snapshot);files.set('/metadata/timestamp.json',timestamp)
}
const repository=()=>new UpdateRepository({cache,config,fetcher:new BoundedFetcher({allowLocalhost:true,timeout:5000})})
const input=readline.createInterface({input:process.stdin,crlfDelay:Infinity})
try{
  for await(const line of input){
    let result
    try{
      if(Buffer.byteLength(line)>65536)throw Error('Fixture command exceeds its bound.')
      const command=JSON.parse(line)
      if(command.operation==='seed'&&!cache){
        cache=command.cache;release=command.release;payload=Buffer.from(command.payload,'base64')
        if(command.fixtureOnly!==true||!cache||release.artifacts.length!==1||digest(payload)!==release.artifacts[0].sha256)
          throw Error('Use only a private inert fixture.')
        publish([release]);const client=repository();const catalog=await client.catalog('preview')
        const file=await client.download(release.artifacts[0])
        result={authenticated:true,catalog,downloads:[{...release.artifacts[0],file}]}
      }else if(command.operation==='refresh'&&cache){
        result={authenticated:true,catalog:await repository().catalog('preview')}
      }else if(command.operation==='withdraw'&&cache){publish([]);result={published:true}}
      else if(command.operation==='damage-signature'&&cache){
        const timestamp=JSON.parse(files.get('/metadata/timestamp.json'))
        timestamp.signatures[0].sig='00'.repeat(64)
        files.set('/metadata/timestamp.json',Buffer.from(JSON.stringify(timestamp)));result={damaged:true}
      }else if(command.operation==='requests'){result={requests}}
      else if(command.operation==='quit'){process.stdout.write(JSON.stringify({ok:true})+'\n');break}
      else throw Error('Unsupported fixture operation.')
      process.stdout.write(JSON.stringify({ok:true,...result})+'\n')
    }catch(error){process.stdout.write(JSON.stringify({ok:false,error:String(error.message).slice(0,512)})+'\n')}
  }
}finally{
  input.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve))
}
