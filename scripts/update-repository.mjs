#!/usr/bin/env node
// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Release-owner tool: keys stay outside Git and publication never executes assets.
import fs from 'node:fs/promises'
import syncFS from 'node:fs'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import {createHash,createPrivateKey,createPublicKey,generateKeyPairSync,randomUUID,sign} from 'node:crypto'
import {spawnSync} from 'node:child_process'
import {Metadata,Root,Targets,Snapshot,Timestamp,Key,Signature,TargetFile,MetaFile} from '@tufjs/models'
import {canonicalize} from '@tufjs/canonical-json'
import {validateArtifact} from '../services/updates/repository.mjs'

const ROOT=fileURLToPath(new URL('../',import.meta.url))
const ROLES=['targets','snapshot','timestamp']
const STATE='augmentor-update-publisher/1'
const LIMIT=2*1024**2
const STATE_LIMIT=16*1024**2
const digest=bytes=>createHash('sha256').update(bytes).digest('hex')
const expiration=(now,days)=>new Date(now+days*86400000).toISOString()
const serialize=metadata=>Buffer.from(JSON.stringify(metadata.toJSON()))

async function ordinary(file,{privateFile=false,maximum=LIMIT}={}){
 const info=await fs.lstat(file)
 if(!info.isFile()||info.isSymbolicLink()||info.nlink!==1||info.size>maximum||
  (process.platform!=='win32'&&(info.uid!==process.getuid()||(privateFile&&(info.mode&0o077)))))throw Error('Use ordinary owned publisher files.')
 return info
}
async function directory(folder,{privateFolder=false,create=false}={}){
 if(create)await fs.mkdir(folder,{recursive:true,mode:privateFolder?0o700:0o755})
 const info=await fs.lstat(folder)
 if(!info.isDirectory()||info.isSymbolicLink()||(process.platform!=='win32'&&(info.uid!==process.getuid()||(privateFolder&&(info.mode&0o077)))))throw Error('Unsafe publisher directory.')
}
async function write(file,bytes,{privateFile=false,exclusive=false,maximum=LIMIT}={}){
 if(Buffer.byteLength(bytes)>maximum)throw Error('Publisher output exceeds its supported size limit.')
 const stage=file+'.'+randomUUID()+'.tmp'
 const handle=await fs.open(stage,'wx',privateFile?0o600:0o644)
 try{
  await handle.writeFile(bytes);await handle.sync();await handle.close()
  if(exclusive){await fs.link(stage,file);await fs.unlink(stage)}else{
   try{await ordinary(file,{privateFile,maximum})}catch(error){if(error.code!=='ENOENT')throw error}
   await fs.rename(stage,file)
  }
  if(process.platform!=='win32'){const folder=await fs.open(path.dirname(file),'r');try{await folder.sync()}finally{await folder.close()}}
 }finally{await handle.close().catch(()=>{});await fs.rm(stage,{force:true})}
}
function generatedKey(){
 const {publicKey,privateKey}=generateKeyPairSync('ed25519')
 const json={keytype:'ed25519',scheme:'ed25519',keyval:{public:Buffer.from(publicKey.export({format:'jwk'}).x,'base64url').toString('hex')}}
 return {key:Key.fromJSON(digest(canonicalize(json)),json),privateKey}
}
function signed(signedValue,keys){
 const metadata=new Metadata(signedValue)
 for(const {key,privateKey} of keys)metadata.sign(bytes=>new Signature({keyID:key.keyID,sig:sign(null,bytes,privateKey).toString('hex')}))
 return metadata
}
async function keysFolder(folder){
 const selected=path.resolve(folder)
 if(selected===ROOT.slice(0,-1)||selected.startsWith(ROOT))throw Error('Publisher keys must stay outside the application repository.')
 if(process.platform==='win32')throw Error('Manage publisher keys on Linux or macOS with private file permissions.')
 await directory(selected,{privateFolder:true})
 const real=await fs.realpath(selected),repository=await fs.realpath(ROOT)
 if(real===repository||real.startsWith(repository+path.sep))throw Error('Publisher keys must stay outside Git, including linked paths.')
 for(let ancestor=real;;ancestor=path.dirname(ancestor)){
  try{await fs.lstat(path.join(ancestor,'.git'));throw Error('Publisher keys must not be inside a Git checkout.')}catch(error){if(error.code!=='ENOENT')throw error}
  if(path.dirname(ancestor)===ancestor)break
 }
 return selected
}

export async function initializeRepository({keys,output,now=Date.now()}){
 const folder=path.resolve(keys),destination=path.resolve(output)
 if(folder===destination||destination.startsWith(folder+path.sep)||folder.startsWith(destination+path.sep))throw Error('Keep secret keys separate from public output.')
 if(folder===ROOT.slice(0,-1)||folder.startsWith(ROOT))throw Error('Publisher keys must stay outside Git.')
 // Refuse reuse, including partially completed initialization. Recovery is explicit.
 await fs.mkdir(folder,{mode:0o700});await keysFolder(folder)
 await fs.mkdir(destination,{mode:0o755})
 const root=new Root({version:1,expires:expiration(now,730),consistentSnapshot:true})
 root.roles.root.threshold=2
 const roots=[]
 for(let i=1;i<=3;i++){
  const key=generatedKey();roots.push(key);root.addKey(key.key,'root')
  await write(path.join(folder,`root-${i}.pem`),key.privateKey.export({format:'pem',type:'pkcs8'}),{privateFile:true,exclusive:true})
 }
 for(const role of ROLES){
  const key=generatedKey();root.addKey(key.key,role)
  await write(path.join(folder,role+'.pem'),key.privateKey.export({format:'pem',type:'pkcs8'}),{privateFile:true,exclusive:true})
 }
 const rootBytes=serialize(signed(root,roots.slice(0,2)))
 await write(path.join(folder,'root.json'),rootBytes,{privateFile:true,exclusive:true})
 await write(path.join(folder,'publisher.json'),JSON.stringify({schema:STATE,sequence:0,rootSha256:digest(rootBytes),publication:null,pending:null,artifactIdentities:{}}),{privateFile:true,exclusive:true})
 await write(path.join(destination,'root.json'),rootBytes,{exclusive:true})
 await write(path.join(destination,'1.root.json'),rootBytes,{exclusive:true})
 return {root:path.join(destination,'root.json'),rootSha256:digest(rootBytes),rootThreshold:2,rootKeys:3}
}

async function owner(keys,{allowPending=false}={}){
 const folder=await keysFolder(keys)
 for(const name of ['root.json','publisher.json',...ROLES.map(role=>role+'.pem')])await ordinary(path.join(folder,name),{privateFile:true,maximum:name==='publisher.json'?STATE_LIMIT:LIMIT})
 const state=JSON.parse(await fs.readFile(path.join(folder,'publisher.json'),'utf8'))
 const history=await trustedRoots(folder,state),{bytes:rootBytes,metadata:root}=history.at(-1)
 if(state.schema!==STATE||!Number.isSafeInteger(state.sequence)||state.sequence<0||state.rootSha256!==digest(rootBytes)||(!allowPending&&state.pending))throw Error('Publisher state needs explicit recovery; never repeat an uncertain publication.')
 if(state.pending&&(!Number.isSafeInteger(state.pending.sequence)||state.pending.sequence!==state.sequence+1||typeof state.pending.directory!=='string'||!path.isAbsolute(state.pending.directory)))throw Error('Invalid pending publisher claim.')
 if(!state.artifactIdentities||typeof state.artifactIdentities!=='object'||Array.isArray(state.artifactIdentities))throw Error('The permanent artifact identity ledger is missing.')
 for(const [targetPath,identity] of Object.entries(state.artifactIdentities)){
  if(!identity||Object.keys(identity).sort().join(',')!=='bytes,sha256')throw Error('Invalid permanent artifact identity ledger.')
  validateArtifact({targetPath,...identity})
 }
 const selected={}
 for(const role of ROLES){
  const privateKey=createPrivateKey(await fs.readFile(path.join(folder,role+'.pem')))
  const publicBytes=Buffer.from(createPublicKey(privateKey).export({format:'jwk'}).x,'base64url').toString('hex')
  const ids=root.signed.roles[role].keyIDs
  if(ids.length!==1||root.signed.roles[role].threshold!==1||root.signed.keys[ids[0]].keyVal.public!==publicBytes)throw Error('The online key differs from the trusted publisher root.')
  selected[role]={privateKey,key:root.signed.keys[ids[0]]}
 }
 return {folder,rootBytes,root,state,selected,history}
}

async function trustedRoots(folder,state){
 const entries=state.rootHistory??[{file:'root.json',sha256:state.rootSha256}]
 if(!Array.isArray(entries)||!entries.length||entries.length>256)throw Error('Invalid retained publisher root history.')
 const history=[]
 for(const entry of entries){
  if(!entry||Object.keys(entry).sort().join(',')!=='file,sha256'||
   !/^(?:root\.json|root-[1-9][0-9]*\.json)$/.test(entry.file)||!/^[a-f0-9]{64}$/.test(entry.sha256))throw Error('Invalid retained publisher root identity.')
  const file=path.join(folder,entry.file);await ordinary(file,{privateFile:true})
  const bytes=await fs.readFile(file),metadata=Metadata.fromJSON('root',JSON.parse(bytes))
  metadata.verifyDelegate('root',metadata)
  if(digest(bytes)!==entry.sha256||metadata.signed.version!==history.length+1)throw Error('Publisher root history changed or skipped a version.')
  if(history.length)history.at(-1).metadata.verifyDelegate('root',metadata)
  history.push({file:entry.file,sha256:entry.sha256,bytes,metadata})
 }
 if(history.at(-1).file!==(state.rootFile??'root.json')||history.at(-1).sha256!==state.rootSha256)throw Error('The publisher root selection differs from its history.')
 return history
}

function rootPolicy(root){
 const roles=root.signed.roles
 if(Object.keys(roles).sort().join(',')!=='root,snapshot,targets,timestamp'||
  roles.root.threshold!==2||roles.root.keyIDs.length!==3||new Set(roles.root.keyIDs).size!==3||
  !root.signed.consistentSnapshot)throw Error('Retain the two-of-three root and consistent-snapshot policy.')
 for(const role of ROLES)if(roles[role].threshold!==1||roles[role].keyIDs.length!==1)throw Error('Retain the declared online signing roles.')
}

export async function prepareRootRotation({root,oldKeys,newKeys,output,now=Date.now()}){
 // Offline-only preparation. It never accesses or changes the online owner.
 if(!Array.isArray(oldKeys)||oldKeys.length!==2)throw Error('Provide two independently held current root keys.')
 await ordinary(root);const priorBytes=await fs.readFile(root),prior=Metadata.fromJSON('root',JSON.parse(priorBytes))
 prior.verifyDelegate('root',prior);rootPolicy(prior)
 const old=[]
 for(const file of oldKeys){
  await keysFolder(path.dirname(path.resolve(file)));await ordinary(file,{privateFile:true})
  const privateKey=createPrivateKey(await fs.readFile(file)),publicBytes=Buffer.from(createPublicKey(privateKey).export({format:'jwk'}).x,'base64url').toString('hex')
  const id=prior.signed.roles.root.keyIDs.find(id=>prior.signed.keys[id].keyVal.public===publicBytes)
  if(!id||old.some(item=>item.key.keyID===id))throw Error('Use two distinct keys authorized by the current root.')
  old.push({key:prior.signed.keys[id],privateKey})
 }
 const folder=path.resolve(newKeys),destination=path.resolve(output)
 if(folder===destination||folder.startsWith(destination+path.sep)||destination.startsWith(folder+path.sep))throw Error('Keep new offline secrets separate from public rotation output.')
 if(prior.signed.version>=256)throw Error('The retained root history limit requires a reviewed bridge migration.')
 await fs.mkdir(folder,{mode:0o700});await keysFolder(folder)
 await fs.mkdir(destination,{mode:0o755})
 const next=new Root({version:prior.signed.version+1,expires:expiration(now,730),consistentSnapshot:true})
 next.roles.root.threshold=2
 for(const role of ROLES)next.addKey(prior.signed.keys[prior.signed.roles[role].keyIDs[0]],role)
 const replacement=[]
 for(let i=1;i<=3;i++){
  const key=generatedKey();replacement.push(key);next.addKey(key.key,'root')
  await write(path.join(folder,`root-${i}.pem`),key.privateKey.export({format:'pem',type:'pkcs8'}),{privateFile:true,exclusive:true})
 }
 const metadata=signed(next,[...old,...replacement.slice(0,2)])
 prior.verifyDelegate('root',metadata);metadata.verifyDelegate('root',metadata)
 const bytes=serialize(metadata),file=path.join(destination,`${next.version}.root.json`)
 await write(file,bytes,{exclusive:true});await write(path.join(folder,'root.json'),bytes,{privateFile:true,exclusive:true})
 return {root:file,version:next.version,rootSha256:digest(bytes),previousRootSha256:digest(priorBytes)}
}

export async function activateRootRotation({keys,root,previousRootSha256,now=Date.now()}){
 return exclusivePublisher(keys,async()=>{
  const publisher=await owner(keys),{state,folder}=publisher
  if(publisher.history.length>=256)throw Error('The retained root history limit requires a reviewed bridge migration.')
  if(state.rootSha256!==previousRootSha256)throw Error('Pin the exact current publisher root before activation.')
  await previousPublication(publisher)
  await ordinary(root);const bytes=await fs.readFile(root),next=Metadata.fromJSON('root',JSON.parse(bytes))
  rootPolicy(next)
  if(next.signed.version!==publisher.root.signed.version+1||!Number.isFinite(Date.parse(next.signed.expires))||Date.parse(next.signed.expires)<=now)throw Error('Activate an unexpired immediate next root version.')
  publisher.root.verifyDelegate('root',next);next.verifyDelegate('root',next)
  for(const role of ROLES){
   const before=publisher.root.signed.roles[role],after=next.signed.roles[role]
   if(after.keyIDs[0]!==before.keyIDs[0]||canonicalize(next.signed.keys[after.keyIDs[0]].toJSON())!==canonicalize(publisher.root.signed.keys[before.keyIDs[0]].toJSON()))throw Error('Online key migration needs its separate publication/recovery plan.')
  }
  const name=`root-${next.signed.version}.json`,file=path.join(folder,name)
  try{
   await ordinary(file,{privateFile:true})
   if(!(await fs.readFile(file)).equals(bytes))throw Error('An earlier prepared root differs. Preserve both candidates.')
  }catch(error){if(error.code!=='ENOENT')throw error;await write(file,bytes,{privateFile:true,exclusive:true})}
  state.rootHistory??=[{file:'root.json',sha256:state.rootSha256}]
  state.rootHistory.push({file:name,sha256:digest(bytes)});state.rootFile=name;state.rootSha256=digest(bytes)
  // The state file is the single commit point. Earlier root bytes remain
  // immutable; interruption before this rename leaves the old root selected.
  await write(path.join(folder,'publisher.json'),JSON.stringify(state),{privateFile:true,maximum:STATE_LIMIT})
  return {version:next.signed.version,rootSha256:state.rootSha256,sequence:state.sequence}
 })
}

function validateCatalogs(catalogs){
 const script=path.join(ROOT,'services/updates/validate_catalog.py')
 const result=spawnSync('python3',['-I','-B',script],{input:JSON.stringify(catalogs),encoding:'utf8',maxBuffer:5*1024**2,timeout:10000})
 if(result.error||result.status!==0)throw Error(result.error?.message||result.stderr.trim()||'Update catalog validation failed.')
 return JSON.parse(result.stdout)
}

async function verifiedPublication(publisher,prior){
 const {root}=publisher
 if(!Number.isSafeInteger(prior.sequence)||prior.sequence<1||typeof prior.directory!=='string'||!path.isAbsolute(prior.directory)||!prior.files||Object.keys(prior.files).length!==5)throw Error('Invalid publisher history.')
 await directory(prior.directory)
 const bytes={}
 for(const [name,expected] of Object.entries(prior.files)){
  const file=path.join(prior.directory,name)
  if(!/^(metadata\/[0-9]+\.(?:targets|snapshot)\.json|metadata\/timestamp\.json|targets\/catalog\/[a-f0-9]{64}\.(?:stable|preview)\.json)$/.test(name))throw Error('Invalid publication history path.')
  await ordinary(file);bytes[name]=await fs.readFile(file)
  if(digest(bytes[name])!==expected)throw Error('The previous publication changed. Preserve it for recovery.')
 }
 const targets=Metadata.fromJSON('targets',JSON.parse(bytes[`metadata/${prior.sequence}.targets.json`]))
 const snapshot=Metadata.fromJSON('snapshot',JSON.parse(bytes[`metadata/${prior.sequence}.snapshot.json`]))
 const timestamp=Metadata.fromJSON('timestamp',JSON.parse(bytes['metadata/timestamp.json']))
 root.verifyDelegate('targets',targets)
 root.verifyDelegate('snapshot',snapshot);root.verifyDelegate('timestamp',timestamp)
 if([targets,snapshot,timestamp].some(metadata=>metadata.signed.version!==prior.sequence))throw Error('Publisher history has an old metadata sequence.')
 const checkReference=(reference,content)=>{
  if(!reference||reference.version!==prior.sequence||reference.length!==content.length||reference.hashes.sha256!==digest(content))throw Error('Publisher metadata references differ from retained bytes.')
 }
 checkReference(snapshot.signed.meta['targets.json'],bytes[`metadata/${prior.sequence}.targets.json`])
 checkReference(timestamp.signed.snapshotMeta,bytes[`metadata/${prior.sequence}.snapshot.json`])
 const catalogs={}
 for(const channel of ['stable','preview']){
  const target=targets.signed.targets['catalog/'+channel+'.json']
  if(!target)throw Error('Publisher history is missing a channel catalog.')
  const file=bytes[`targets/catalog/${target.hashes.sha256}.${channel}.json`]
  if(!file||file.length!==target.length||digest(file)!==target.hashes.sha256)throw Error('The retained catalog identity differs.')
  catalogs[channel]=JSON.parse(file)
 }
 const values=validateCatalogs(catalogs),expected=new Set(['catalog/stable.json','catalog/preview.json'])
 for(const channel of ['stable','preview'])for(const release of values[channel].releases)for(const artifact of release.artifacts){
  validateArtifact(artifact);expected.add(artifact.targetPath)
  const target=targets.signed.targets[artifact.targetPath]
  if(!target||target.length!==artifact.bytes||target.hashes.sha256!==artifact.sha256)throw Error('A retained artifact differs from its signed catalog.')
 }
 if(Object.keys(targets.signed.targets).length!==expected.size)throw Error('Publisher history contains undeclared targets.')
 return {targets,catalogs:values}
}

async function previousPublication(publisher){
 const {state}=publisher
 if((state.publication?.sequence||0)<state.sequence){
  const file=path.join(publisher.folder,`recovery-${state.sequence}.json`);await ordinary(file,{privateFile:true})
  const audit=JSON.parse(await fs.readFile(file,'utf8'))
  if(audit.schema!=='augmentor-update-publisher-recovery/1'||audit.sequence!==state.sequence||audit.decision!=='abandon'||!publisher.history.some(root=>root.sha256===audit.rootSha256))throw Error('The skipped publisher sequence lacks a matching recovery record.')
 }
 if(!state.publication)return null
 if(state.publication.sequence>state.sequence)throw Error('Invalid publisher history sequence.')
 return verifiedPublication(publisher,state.publication)
}

async function buildPublication({keys,output,catalogs,artifacts,refresh=false,now=Date.now()}){
 const publisher=await owner(keys),{folder,root,rootBytes,state,selected}=publisher
 if(Date.parse(root.signed.expires)<=now)throw Error('Rotate and distribute the offline root before publishing.')
 const previous=await previousPublication(publisher)
 const values=validateCatalogs(refresh?(previous?.catalogs):catalogs)
 if(refresh&&!previous)throw Error('Publish a reviewed release catalog before refreshing it.')
 const targets={},files={}
 for(const channel of ['stable','preview']){
  const bytes=Buffer.from(JSON.stringify(values[channel])),sha256=digest(bytes),name='catalog/'+channel+'.json'
  targets[name]=new TargetFile({path:name,length:bytes.length,hashes:{sha256}})
  files[`targets/catalog/${sha256}.${channel}.json`]=bytes
  for(const release of values[channel].releases)for(const artifact of release.artifacts){
   validateArtifact(artifact)
   const old=previous?.targets.signed.targets[artifact.targetPath],permanent=state.artifactIdentities[artifact.targetPath]
   if((old&&(old.length!==artifact.bytes||old.hashes.sha256!==artifact.sha256))||(permanent&&(permanent.bytes!==artifact.bytes||permanent.sha256!==artifact.sha256)))throw Error('An immutable published artifact was relabeled.')
   if(!old){
    if(!artifacts)throw Error('New releases need their actual reviewed artifact bytes.')
    const base=path.resolve(artifacts),file=path.join(base,artifact.targetPath)
    await ordinary(file,{maximum:artifact.bytes})
    if(!(await fs.realpath(file)).startsWith(await fs.realpath(base)+path.sep))throw Error('The artifact escaped its reviewed directory.')
    const hash=createHash('sha256');let count=0
    for await(const chunk of syncFS.createReadStream(file)){hash.update(chunk);count+=chunk.length}
    if(count!==artifact.bytes||hash.digest('hex')!==artifact.sha256)throw Error('The release artifact differs from its catalog identity.')
   }
   const existing=targets[artifact.targetPath]
   if(existing&&(existing.length!==artifact.bytes||existing.hashes.sha256!==artifact.sha256))throw Error('Catalogs contain conflicting artifact identities.')
   targets[artifact.targetPath]=new TargetFile({path:artifact.targetPath,length:artifact.bytes,hashes:{sha256:artifact.sha256}})
  }
 }
 const destination=path.resolve(output)
 if(destination===folder||destination.startsWith(folder+path.sep)||folder.startsWith(destination+path.sep))throw Error('Do not publish the secret key directory.')
 // Claim the sequence durably before signing or producing any candidate output.
 const sequence=state.sequence+1
 await fs.mkdir(destination,{mode:0o755})
 state.pending={sequence,directory:destination}
 // Reserve names before any signature can escape, retaining withdrawn releases
 // and failed attempts so no later catalog can reuse a URL for different bytes.
 for(const [name,target] of Object.entries(targets))if(!name.startsWith('catalog/'))state.artifactIdentities[name]={bytes:target.length,sha256:target.hashes.sha256}
 await write(path.join(folder,'publisher.json'),JSON.stringify(state),{privateFile:true,maximum:STATE_LIMIT})
 const targetBytes=serialize(signed(new Targets({version:sequence,expires:expiration(now,90),targets}),[selected.targets]))
 const snapshotBytes=serialize(signed(new Snapshot({version:sequence,expires:expiration(now,30),meta:{
  'targets.json':new MetaFile({version:sequence,length:targetBytes.length,hashes:{sha256:digest(targetBytes)}})}}),[selected.snapshot]))
 const timestampBytes=serialize(signed(new Timestamp({version:sequence,expires:expiration(now,7),snapshotMeta:
  new MetaFile({version:sequence,length:snapshotBytes.length,hashes:{sha256:digest(snapshotBytes)}})}),[selected.timestamp]))
 files[`metadata/${sequence}.targets.json`]=targetBytes;files[`metadata/${sequence}.snapshot.json`]=snapshotBytes
 files['metadata/timestamp.json']=timestampBytes
 const hashes={}
 for(const [name,bytes] of Object.entries(files)){
  const file=path.join(destination,name);await directory(path.dirname(file),{create:true})
  await write(file,bytes,{exclusive:true});hashes[name]=digest(bytes)
 }
 await directory(path.join(destination,'metadata'),{create:true})
 await write(path.join(destination,'metadata/root.json'),rootBytes,{exclusive:true})
 for(const retained of publisher.history)await write(path.join(destination,`metadata/${retained.metadata.signed.version}.root.json`),retained.bytes,{exclusive:true})
 const manifest={schema:'augmentor-update-publication/1',sequence,rootSha256:state.rootSha256,files:hashes,createdAt:new Date(now).toISOString()}
 await write(path.join(destination,'publication.json'),JSON.stringify(manifest,null,2),{exclusive:true})
 state.sequence=sequence;state.publication={directory:destination,sequence,files:hashes};state.pending=null
 await write(path.join(folder,'publisher.json'),JSON.stringify(state),{privateFile:true,maximum:STATE_LIMIT})
 return manifest
}

async function exclusivePublisher(keys,operation){
 const folder=await keysFolder(keys),lock=path.join(folder,'publisher.lock')
 // A killed owner leaves this lock and its durable pending claim for deliberate
 // recovery. Concurrent writers must never sign the same role version twice.
 const handle=await fs.open(lock,'wx',0o600)
 try{
  await handle.writeFile(JSON.stringify({pid:process.pid,createdAt:new Date().toISOString()}));await handle.sync()
  return await operation()
 }finally{await handle.close();await fs.unlink(lock)}
}

export async function publishRepository(options){
 return exclusivePublisher(options.keys,()=>buildPublication(options))
}

export async function recoverRepository({keys,output,sequence,decision}){
 if(!['finalize','abandon'].includes(decision)||!Number.isSafeInteger(sequence)||sequence<1)throw Error('Recovery needs an explicit finalize/abandon decision and exact sequence.')
 return exclusivePublisher(keys,async()=>{
  const publisher=await owner(keys,{allowPending:true}),{state,folder,rootBytes}=publisher,pending=state.pending
  if(!pending||pending.sequence!==sequence||pending.directory!==path.resolve(output))throw Error('Recovery must match the exact pending publication sequence and directory.')
  await previousPublication(publisher)
  let publication=null
  if(decision==='finalize'){
   const manifestFile=path.join(pending.directory,'publication.json')
   await ordinary(manifestFile)
   const manifest=JSON.parse(await fs.readFile(manifestFile,'utf8'))
   if(manifest.schema!=='augmentor-update-publication/1'||manifest.sequence!==sequence||manifest.rootSha256!==state.rootSha256)throw Error('Recovery manifest differs from the pending publisher claim.')
   for(const [name,expected] of [['root.json',rootBytes],...publisher.history.map(root=>[`${root.metadata.signed.version}.root.json`,root.bytes])]){
    const file=path.join(pending.directory,'metadata',name);await ordinary(file)
    if(!(await fs.readFile(file)).equals(expected))throw Error('Recovery root differs from the private publisher trust anchor.')
   }
   publication={directory:pending.directory,sequence,files:manifest.files}
   const recovered=await verifiedPublication(publisher,publication),previous=await previousPublication(publisher)
   for(const [name,target] of Object.entries(recovered.targets.signed.targets)){
    if(name.startsWith('catalog/'))continue
    const old=previous?.targets.signed.targets[name]
    if(old&&(old.length!==target.length||old.hashes.sha256!==target.hashes.sha256))throw Error('Recovery attempted to relabel an immutable artifact.')
    const permanent=state.artifactIdentities[name]
    if(!permanent||permanent.bytes!==target.length||permanent.sha256!==target.hashes.sha256)throw Error('Recovery differs from the permanent artifact identity ledger.')
   }
  }
  const audit={schema:'augmentor-update-publisher-recovery/1',sequence,directory:pending.directory,decision,rootSha256:state.rootSha256}
  const auditFile=path.join(folder,`recovery-${sequence}.json`),auditBytes=Buffer.from(JSON.stringify(audit))
  try{
   await ordinary(auditFile,{privateFile:true})
   if(!(await fs.readFile(auditFile)).equals(auditBytes))throw Error('A prior recovery decision differs; preserve the uncertain state.')
  }catch(error){if(error.code!=='ENOENT')throw error;await write(auditFile,auditBytes,{privateFile:true,exclusive:true})}
  // Even abandoned signatures may have escaped: consume their version forever.
  state.sequence=sequence;state.pending=null
  if(publication)state.publication=publication
  await write(path.join(folder,'publisher.json'),JSON.stringify(state),{privateFile:true,maximum:STATE_LIMIT})
  return audit
 })
}

async function main(){
 const [operation,...arguments_]=process.argv.slice(2),options={}
 for(let i=0;i<arguments_.length;i+=2){const name=arguments_[i],value=arguments_[i+1];if(!['--keys','--out','--catalogs','--artifacts','--sequence','--decision','--root','--old-key-1','--old-key-2','--new-keys','--previous-root-sha256'].includes(name)||!value||options[name])throw Error('Use explicit keys/output/catalog/artifact/recovery options.');options[name]=value}
 if(operation==='prepare-root')return prepareRootRotation({root:options['--root'],oldKeys:[options['--old-key-1'],options['--old-key-2']],newKeys:options['--new-keys'],output:options['--out']})
 if(operation==='activate-root')return activateRootRotation({keys:options['--keys'],root:options['--root'],previousRootSha256:options['--previous-root-sha256']})
 if(!options['--keys']||!options['--out'])throw Error('Provide --keys outside Git and a new --out directory.')
 if(operation==='init')return initializeRepository({keys:options['--keys'],output:options['--out']})
 if(operation==='recover')return recoverRepository({keys:options['--keys'],output:options['--out'],sequence:/^[1-9][0-9]*$/.test(options['--sequence']||'')?Number(options['--sequence']):NaN,decision:options['--decision']})
 if(!['publish','refresh'].includes(operation))throw Error('Choose init, publish, refresh, recover, prepare-root or activate-root.')
 let catalogs
 if(operation==='publish'){
  if(!options['--catalogs'])throw Error('Provide both reviewed catalogs.')
  await ordinary(options['--catalogs'],{maximum:4*1024**2})
  catalogs=JSON.parse(await fs.readFile(options['--catalogs'],'utf8'))
 }
 return publishRepository({keys:options['--keys'],output:options['--out'],catalogs,artifacts:options['--artifacts'],refresh:operation==='refresh'})
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().then(result=>process.stdout.write(JSON.stringify(result)+'\n')).catch(error=>{process.stderr.write(error.message+'\n');process.exitCode=1})
