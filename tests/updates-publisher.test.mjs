// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Temporary signing authorities and inert assets; no production key generation.
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import http from 'node:http'
import {createHash} from 'node:crypto'
import {Metadata} from '@tufjs/models'
import {initializeRepository,publishRepository,recoverRepository,prepareRootRotation,activateRootRotation} from '../scripts/update-repository.mjs'
import {UpdateRepository,BoundedFetcher} from '../services/updates/repository.mjs'

const digest=bytes=>createHash('sha256').update(bytes).digest('hex')
const empty=()=>({schema:'augmentor-update-catalog/1',releases:[]})
async function fixture(t){
 const base=await fs.mkdtemp(path.join(os.tmpdir(),'augmentor-publisher-'));t.after(()=>fs.rm(base,{recursive:true,force:true}))
 const keys=path.join(base,'keys'),output=path.join(base,'trust'),artifacts=path.join(base,'artifacts')
 const initialized=await initializeRepository({keys,output}),rootBytes=await fs.readFile(initialized.root)
 const payload=Buffer.from('MZ inert synthetic publisher installer'),targetPath='releases/download/v1.1.0-windows-preview.1/Augmentor-1.1.0-windows-x64-preview.exe'
 await fs.mkdir(path.dirname(path.join(artifacts,targetPath)),{recursive:true})
 await fs.writeFile(path.join(artifacts,targetPath),payload)
 const release={version:'1.1.0',build:1,sourceCommit:'a'.repeat(40),channel:'preview',target:'windows-x64',installType:'windows-inno',
  releaseUrl:'https://github.com/ManoloRemiddi/augmentor-agent/releases/tag/v1.1.0-windows-preview.1',protocols:{product:'augmentor/1'},
  dataSchema:1,readableDataSchemas:[1],minimumOS:'26200',artifacts:[{role:'installer',targetPath,bytes:payload.length,sha256:digest(payload)}]}
 const catalogs={stable:empty(),preview:{schema:'augmentor-update-catalog/1',releases:[release]}}
 const stage=sequence=>path.join(base,'publication-'+sequence)
 return {base,keys,artifacts,initialized,rootBytes,payload,targetPath,release,catalogs,stage}
}

test('publisher separates two-of-three root keys, emits hash-prefixed catalogs and serves the real TUF client',async t=>{
 const f=await fixture(t),root=Metadata.fromJSON('root',JSON.parse(f.rootBytes))
 root.verifyDelegate('root',root);assert.equal(root.signed.roles.root.threshold,2);assert.equal(root.signed.roles.root.keyIDs.length,3)
 for(const name of ['root-1.pem','root-2.pem','root-3.pem','targets.pem','snapshot.pem','timestamp.pem'])assert.equal((await fs.stat(path.join(f.keys,name))).mode&0o077,0)
 const result=await publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts})
 assert.equal(result.sequence,1)
 assert.equal(JSON.stringify(result).includes('PRIVATE KEY'),false)
 const server=http.createServer(async(req,res)=>{
  const relative=decodeURIComponent(req.url.slice(1))
  if(relative.includes('..')){res.writeHead(400);res.end();return}
  const file=relative.startsWith('releases/')?path.join(f.artifacts,relative):path.join(f.stage(1),relative)
  try{res.end(await fs.readFile(file))}catch{res.writeHead(404);res.end()}
 })
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>server.close(resolve)))
 const base=`http://127.0.0.1:${server.address().port}/`
 const client=new UpdateRepository({cache:path.join(f.base,'cache'),config:{root:f.rootBytes,metadataBaseUrl:base+'metadata/',catalogBaseUrl:base+'targets/',artifactBaseUrl:base},fetcher:new BoundedFetcher({allowLocalhost:true})})
 assert.deepEqual(await client.catalog('preview'),f.catalogs.preview)
 assert.deepEqual(await fs.readFile(await client.download(f.release.artifacts[0])),f.payload)
})

test('daily refresh needs online keys only and advances metadata while retaining exact release bytes',async t=>{
 const f=await fixture(t)
 await publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts})
 for(const name of ['root-1.pem','root-2.pem','root-3.pem'])await fs.unlink(path.join(f.keys,name))
 await fs.rm(f.artifacts,{recursive:true})
 const result=await publishRepository({keys:f.keys,output:f.stage(2),refresh:true})
 assert.equal(result.sequence,2)
 const targets=JSON.parse(await fs.readFile(path.join(f.stage(2),'metadata/2.targets.json'),'utf8'))
 assert.equal(targets.signed.targets[f.targetPath].hashes.sha256,digest(f.payload))
 const timestamp=JSON.parse(await fs.readFile(path.join(f.stage(2),'metadata/timestamp.json'),'utf8'))
 assert.equal(timestamp.signed.meta['snapshot.json'].version,2)
})

test('new artifacts, mismatched bytes and reused public target names cannot be signed',async t=>{
 const f=await fixture(t),release=f.release
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs}),/actual reviewed artifact bytes/)
 await fs.writeFile(path.join(f.artifacts,f.targetPath),'damaged')
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts}),/differs from its catalog/)
 await fs.writeFile(path.join(f.artifacts,f.targetPath),f.payload)
 await publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts})
 release.artifacts[0].sha256='b'.repeat(64)
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(2),catalogs:f.catalogs,artifacts:f.artifacts}),/relabeled/)
})

test('tampered history, unsafe keys and unfinished publication state refuse without a new sequence',async t=>{
 const f=await fixture(t)
 await publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts})
 const source=path.join(f.stage(1),'metadata/1.targets.json'),original=await fs.readFile(source)
 await fs.writeFile(source,'altered')
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(2),refresh:true}),/previous publication changed/)
 await fs.writeFile(source,original)
 await fs.chmod(path.join(f.keys,'timestamp.pem'),0o644)
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(2),refresh:true}),/ordinary owned publisher/)
 await fs.chmod(path.join(f.keys,'timestamp.pem'),0o600)
 const stateFile=path.join(f.keys,'publisher.json'),state=JSON.parse(await fs.readFile(stateFile,'utf8'))
 state.pending={sequence:2,directory:f.stage(2)};await fs.writeFile(stateFile,JSON.stringify(state))
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(2),refresh:true}),/explicit recovery/)
 assert.equal(JSON.parse(await fs.readFile(stateFile,'utf8')).sequence,1)
})

test('publisher serializes concurrent signing owners and never overwrites earlier output',async t=>{
 const f=await fixture(t)
 const results=await Promise.allSettled([1,2].map(n=>publishRepository({keys:f.keys,output:f.stage(n),catalogs:f.catalogs,artifacts:f.artifacts})))
 assert.equal(results.filter(result=>result.status==='fulfilled').length,1)
 const successful=results.find(result=>result.status==='fulfilled').value
 assert.equal(successful.sequence,1)
 const directory=results[0].status==='fulfilled'?f.stage(1):f.stage(2)
 await assert.rejects(publishRepository({keys:f.keys,output:directory,refresh:true}),/EEXIST/)
 assert.equal(JSON.parse(await fs.readFile(path.join(f.keys,'publisher.json'),'utf8')).sequence,1)
})

test('completed output after a failed private checkpoint requires exact explicit recovery and verified signatures',async t=>{
 const f=await fixture(t),stateFile=path.join(f.keys,'publisher.json')
 await publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts})
 const rename=fs.rename
 const failure=t.mock.method(fs,'rename',async(source,target)=>{
  if(target===stateFile&&!JSON.parse(await fs.readFile(source,'utf8')).pending)throw Error('synthetic lost publisher checkpoint')
  return rename(source,target)
 })
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(2),refresh:true}),/lost publisher checkpoint/)
 failure.mock.restore()
 assert.equal(JSON.parse(await fs.readFile(stateFile,'utf8')).pending.sequence,2)
 const recovery={keys:f.keys,output:f.stage(2),sequence:2,decision:'finalize'}
 await assert.rejects(recoverRepository({...recovery,sequence:3}),/exact pending/)
 await assert.rejects(recoverRepository({...recovery,output:f.stage(3)}),/exact pending/)
 const file=path.join(f.stage(2),'metadata/2.snapshot.json'),original=await fs.readFile(file)
 const altered=JSON.parse(original);altered.signed.expires='2099-01-01T00:00:00Z'
 await fs.writeFile(file,JSON.stringify(altered))
 const manifestFile=path.join(f.stage(2),'publication.json'),manifestBytes=await fs.readFile(manifestFile)
 const manifest=JSON.parse(manifestBytes);manifest.files['metadata/2.snapshot.json']=digest(await fs.readFile(file))
 await fs.writeFile(manifestFile,JSON.stringify(manifest))
 await assert.rejects(recoverRepository(recovery),/signature|threshold|signed by 0/i)
 assert.equal(JSON.parse(await fs.readFile(stateFile,'utf8')).pending.sequence,2)
 await fs.writeFile(file,original);await fs.writeFile(manifestFile,manifestBytes)
 const audit=await recoverRepository(recovery)
 assert.equal(audit.decision,'finalize')
 assert.equal(JSON.parse(await fs.readFile(stateFile,'utf8')).publication.sequence,2)
 await assert.rejects(recoverRepository(recovery),/exact pending/)
 assert.equal((await publishRepository({keys:f.keys,output:f.stage(3),refresh:true})).sequence,3)
})

test('partial publication stays preserved, abandonment burns its version and stale locks cannot be evicted automatically',async t=>{
 const f=await fixture(t),stateFile=path.join(f.keys,'publisher.json')
 await publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts})
 const link=fs.link
 const failure=t.mock.method(fs,'link',async(source,target)=>{
  if(target===path.join(f.stage(2),'metadata/timestamp.json'))throw Error('synthetic interrupted timestamp')
  return link(source,target)
 })
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(2),refresh:true}),/interrupted timestamp/)
 failure.mock.restore()
 const partial=await fs.readFile(path.join(f.stage(2),'metadata/2.targets.json'))
 const recovery={keys:f.keys,output:f.stage(2),sequence:2,decision:'finalize'}
 await assert.rejects(recoverRepository(recovery),/ENOENT/)
 assert.equal(JSON.parse(await fs.readFile(stateFile,'utf8')).pending.sequence,2)
 const lock=path.join(f.keys,'publisher.lock')
 await fs.writeFile(lock,'preserved stale or live owner',{mode:0o600})
 await assert.rejects(recoverRepository({...recovery,decision:'abandon'}),/EEXIST/)
 assert.equal(await fs.readFile(lock,'utf8'),'preserved stale or live owner')
 await fs.unlink(lock) // Fixture owner explicitly releases its inert lock.
 await recoverRepository({...recovery,decision:'abandon'})
 const state=JSON.parse(await fs.readFile(stateFile,'utf8'))
 assert.equal(state.sequence,2);assert.equal(state.publication.sequence,1);assert.equal(state.pending,null)
 assert.deepEqual(await fs.readFile(path.join(f.stage(2),'metadata/2.targets.json')),partial)
 assert.equal((await publishRepository({keys:f.keys,output:f.stage(3),refresh:true})).sequence,3)
 assert.equal(await fs.stat(path.join(f.stage(3),'metadata/3.targets.json')).then(stat=>stat.isFile()),true)
})

test('withdrawing a release never frees its immutable URL for different bytes',async t=>{
 const f=await fixture(t)
 await publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts})
 await publishRepository({keys:f.keys,output:f.stage(2),catalogs:{stable:empty(),preview:empty()}})
 const replacement=Buffer.from('different synthetic installer')
 await fs.writeFile(path.join(f.artifacts,f.targetPath),replacement)
 f.release.artifacts[0]={...f.release.artifacts[0],bytes:replacement.length,sha256:digest(replacement)}
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(3),catalogs:f.catalogs,artifacts:f.artifacts}),/relabeled/)
 assert.equal(JSON.parse(await fs.readFile(path.join(f.keys,'publisher.json'),'utf8')).sequence,2)
})

async function rotation(f){
 return prepareRootRotation({root:f.initialized.root,oldKeys:[1,2].map(n=>path.join(f.keys,`root-${n}.pem`)),
  newKeys:path.join(f.base,'next-offline-keys'),output:path.join(f.base,'rotation')})
}

test('offline root replacement cross-signs both thresholds and the real client advances from its original trust root',async t=>{
 const f=await fixture(t)
 await publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts})
 const rotated=await rotation(f),bytes=await fs.readFile(rotated.root),next=Metadata.fromJSON('root',JSON.parse(bytes)),old=Metadata.fromJSON('root',JSON.parse(f.rootBytes))
 old.verifyDelegate('root',next);next.verifyDelegate('root',next)
 assert.equal(next.signed.version,2);assert.equal(next.toJSON().signatures.length,4)
 assert.equal(next.signed.roles.root.keyIDs.some(id=>old.signed.roles.root.keyIDs.includes(id)),false)
 for(const role of ['targets','snapshot','timestamp'])assert.deepEqual(next.signed.roles[role],old.signed.roles[role])
 assert.deepEqual(await fs.readdir(path.dirname(rotated.root)),['2.root.json'])
 for(const n of [1,2,3])await fs.unlink(path.join(f.keys,`root-${n}.pem`))
 assert.equal((await activateRootRotation({keys:f.keys,root:rotated.root,previousRootSha256:rotated.previousRootSha256})).sequence,1)
 assert.deepEqual(await fs.readFile(path.join(f.keys,'root.json')),f.rootBytes)
 await publishRepository({keys:f.keys,output:f.stage(2),refresh:true})
 assert.deepEqual(await fs.readFile(path.join(f.stage(2),'metadata/1.root.json')),f.rootBytes)
 assert.deepEqual(await fs.readFile(path.join(f.stage(2),'metadata/2.root.json')),bytes)
 const third=await prepareRootRotation({root:rotated.root,
  oldKeys:[1,2].map(n=>path.join(f.base,'next-offline-keys',`root-${n}.pem`)),
  newKeys:path.join(f.base,'third-offline-keys'),output:path.join(f.base,'third-rotation')})
 await activateRootRotation({keys:f.keys,root:third.root,previousRootSha256:third.previousRootSha256})
 await publishRepository({keys:f.keys,output:f.stage(3),refresh:true})
 const requests=[]
 const server=http.createServer(async(req,res)=>{
  const relative=decodeURIComponent(req.url.slice(1))
  requests.push(relative)
  if(relative.includes('..')){res.writeHead(400);res.end();return}
  try{res.end(await fs.readFile(path.join(relative.startsWith('releases/')?f.artifacts:f.stage(3),relative)))}catch{res.writeHead(404);res.end()}
 })
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>server.close(resolve)))
 const url=`http://127.0.0.1:${server.address().port}/`
 const client=new UpdateRepository({cache:path.join(f.base,'rotated-cache'),config:{root:f.rootBytes,
  metadataBaseUrl:url+'metadata/',catalogBaseUrl:url+'targets/',artifactBaseUrl:url},fetcher:new BoundedFetcher({allowLocalhost:true})})
 assert.deepEqual(await client.catalog('preview'),f.catalogs.preview)
 assert.deepEqual(await fs.readFile(await client.download(f.release.artifacts[0])),f.payload)
 assert.ok(requests.includes('metadata/2.root.json'));assert.ok(requests.includes('metadata/3.root.json'))
})

test('root preparation refuses duplicate authorities and activation refuses changed pins, skipped versions and missing signatures',async t=>{
 const f=await fixture(t),options={root:f.initialized.root,oldKeys:[path.join(f.keys,'root-1.pem'),path.join(f.keys,'root-1.pem')],
  newKeys:path.join(f.base,'duplicate-keys'),output:path.join(f.base,'duplicate-output')}
 await assert.rejects(prepareRootRotation(options),/two distinct/)
 await assert.rejects(fs.stat(options.newKeys),/ENOENT/)
 const rotated=await rotation(f),activate={keys:f.keys,root:rotated.root,previousRootSha256:rotated.previousRootSha256}
 await assert.rejects(activateRootRotation({...activate,previousRootSha256:'0'.repeat(64)}),/exact current/)
 const raw=await fs.readFile(rotated.root),altered=JSON.parse(raw)
 altered.signed.version=3;await fs.writeFile(rotated.root,JSON.stringify(altered))
 await assert.rejects(activateRootRotation(activate),/immediate next/)
 altered.signed.version=2;altered.signatures=altered.signatures.slice(0,2);await fs.writeFile(rotated.root,JSON.stringify(altered))
 await assert.rejects(activateRootRotation(activate),/signature|threshold|signed by 0/i)
 await fs.writeFile(rotated.root,raw)
 await activateRootRotation(activate)
 await assert.rejects(activateRootRotation(activate),/exact current/)
})

test('interrupted root activation leaves the original selected and only the same prepared candidate can finish',async t=>{
 const f=await fixture(t),rotated=await rotation(f),stateFile=path.join(f.keys,'publisher.json')
 const activate={keys:f.keys,root:rotated.root,previousRootSha256:rotated.previousRootSha256},before=await fs.readFile(stateFile)
 const rename=fs.rename,failure=t.mock.method(fs,'rename',async(source,target)=>{
  if(target===stateFile)throw Error('synthetic interrupted root commit')
  return rename(source,target)
 })
 await assert.rejects(activateRootRotation(activate),/interrupted root commit/);failure.mock.restore()
 assert.deepEqual(await fs.readFile(stateFile),before)
 assert.deepEqual(await fs.readFile(path.join(f.keys,'root-2.json')),await fs.readFile(rotated.root))
 await publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts})
 assert.equal(JSON.parse(await fs.readFile(path.join(f.stage(1),'metadata/root.json'))).signed.version,1)
 await activateRootRotation(activate)
 const state=JSON.parse(await fs.readFile(stateFile));assert.equal(state.rootHistory.length,2);assert.equal(state.rootFile,'root-2.json')
 await publishRepository({keys:f.keys,output:f.stage(2),refresh:true})
})

test('root replacement preserves abandoned signing sequences and rejects edited root history',async t=>{
 const f=await fixture(t),stateFile=path.join(f.keys,'publisher.json')
 await publishRepository({keys:f.keys,output:f.stage(1),catalogs:f.catalogs,artifacts:f.artifacts})
 const link=fs.link,failure=t.mock.method(fs,'link',async(source,target)=>{
  if(target===path.join(f.stage(2),'metadata/timestamp.json'))throw Error('synthetic pending publication')
  return link(source,target)
 })
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(2),refresh:true}),/pending publication/);failure.mock.restore()
 const rotated=await rotation(f),activate={keys:f.keys,root:rotated.root,previousRootSha256:rotated.previousRootSha256}
 await assert.rejects(activateRootRotation(activate),/explicit recovery/)
 await recoverRepository({keys:f.keys,output:f.stage(2),sequence:2,decision:'abandon'})
 await activateRootRotation(activate)
 assert.equal((await publishRepository({keys:f.keys,output:f.stage(3),refresh:true})).sequence,3)
 const state=JSON.parse(await fs.readFile(stateFile));assert.equal(state.artifactIdentities[f.targetPath].sha256,digest(f.payload))
 await fs.writeFile(path.join(f.keys,'root.json'),'edited retained root')
 await assert.rejects(publishRepository({keys:f.keys,output:f.stage(4),refresh:true}))
 assert.equal(JSON.parse(await fs.readFile(stateFile)).sequence,3)
})
