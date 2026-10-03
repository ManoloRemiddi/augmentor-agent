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
async function write(file,bytes,{privateFile=false,exclusive=false}={}){
 const stage=file+'.'+randomUUID()+'.tmp'
 const handle=await fs.open(stage,'wx',privateFile?0o600:0o644)
 try{
  await handle.writeFile(bytes);await handle.sync();await handle.close()
  if(exclusive){await fs.link(stage,file);await fs.unlink(stage)}else{
   try{await ordinary(file,{privateFile})}catch(error){if(error.code!=='ENOENT')throw error}
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
 await write(path.join(folder,'publisher.json'),JSON.stringify({schema:STATE,sequence:0,rootSha256:digest(rootBytes),publication:null,pending:null}),{privateFile:true,exclusive:true})
 await write(path.join(destination,'root.json'),rootBytes,{exclusive:true})
 await write(path.join(destination,'1.root.json'),rootBytes,{exclusive:true})
 return {root:path.join(destination,'root.json'),rootSha256:digest(rootBytes),rootThreshold:2,rootKeys:3}
}

async function owner(keys){
 const folder=await keysFolder(keys)
 for(const name of ['root.json','publisher.json',...ROLES.map(role=>role+'.pem')])await ordinary(path.join(folder,name),{privateFile:true})
 const rootBytes=await fs.readFile(path.join(folder,'root.json'))
 const state=JSON.parse(await fs.readFile(path.join(folder,'publisher.json'),'utf8'))
 if(state.schema!==STATE||!Number.isSafeInteger(state.sequence)||state.sequence<0||state.rootSha256!==digest(rootBytes)||state.pending)throw Error('Publisher state needs explicit recovery; never repeat an uncertain publication.')
 const root=Metadata.fromJSON('root',JSON.parse(rootBytes));root.verifyDelegate('root',root)
 const selected={}
 for(const role of ROLES){
  const privateKey=createPrivateKey(await fs.readFile(path.join(folder,role+'.pem')))
  const publicBytes=Buffer.from(createPublicKey(privateKey).export({format:'jwk'}).x,'base64url').toString('hex')
  const ids=root.signed.roles[role].keyIDs
  if(ids.length!==1||root.signed.roles[role].threshold!==1||root.signed.keys[ids[0]].keyVal.public!==publicBytes)throw Error('The online key differs from the trusted publisher root.')
  selected[role]={privateKey,key:root.signed.keys[ids[0]]}
 }
 return {folder,rootBytes,root,state,selected}
}

function validateCatalogs(catalogs){
 const script=path.join(ROOT,'services/updates/validate_catalog.py')
 const result=spawnSync('python3',['-I','-B',script],{input:JSON.stringify(catalogs),encoding:'utf8',maxBuffer:5*1024**2,timeout:10000})
 if(result.error||result.status!==0)throw Error(result.error?.message||result.stderr.trim()||'Update catalog validation failed.')
 return JSON.parse(result.stdout)
}

async function previousPublication(publisher){
 const {state,root}=publisher
 if(!state.publication){if(state.sequence!==0)throw Error('The previous publication is missing.');return null}
 const prior=state.publication
 if(prior.sequence!==state.sequence||!path.isAbsolute(prior.directory))throw Error('Invalid publisher history.')
 await directory(prior.directory)
 const bytes={}
 for(const [name,expected] of Object.entries(prior.files)){
  const file=path.join(prior.directory,name)
  if(!/^(metadata\/[0-9]+\.(?:targets|snapshot)\.json|metadata\/timestamp\.json|targets\/catalog\/[a-f0-9]{64}\.(?:stable|preview)\.json)$/.test(name))throw Error('Invalid publication history path.')
  await ordinary(file);bytes[name]=await fs.readFile(file)
  if(digest(bytes[name])!==expected)throw Error('The previous publication changed. Preserve it for recovery.')
 }
 const targets=Metadata.fromJSON('targets',JSON.parse(bytes[`metadata/${state.sequence}.targets.json`]))
 root.verifyDelegate('targets',targets)
 if(targets.signed.version!==state.sequence)throw Error('Publisher history has an old target sequence.')
 const catalogs={}
 for(const channel of ['stable','preview']){
  const target=targets.signed.targets['catalog/'+channel+'.json']
  if(!target)throw Error('Publisher history is missing a channel catalog.')
  const file=bytes[`targets/catalog/${target.hashes.sha256}.${channel}.json`]
  if(!file||file.length!==target.length||digest(file)!==target.hashes.sha256)throw Error('The retained catalog identity differs.')
  catalogs[channel]=JSON.parse(file)
 }
 return {targets,catalogs}
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
   const old=previous?.targets.signed.targets[artifact.targetPath]
   if(old&&(old.length!==artifact.bytes||old.hashes.sha256!==artifact.sha256))throw Error('An immutable published artifact was relabeled.')
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
 await write(path.join(folder,'publisher.json'),JSON.stringify(state),{privateFile:true})
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
 await write(path.join(destination,`metadata/${root.signed.version}.root.json`),rootBytes,{exclusive:true})
 const manifest={schema:'augmentor-update-publication/1',sequence,rootSha256:state.rootSha256,files:hashes,createdAt:new Date(now).toISOString()}
 await write(path.join(destination,'publication.json'),JSON.stringify(manifest,null,2),{exclusive:true})
 state.sequence=sequence;state.publication={directory:destination,sequence,files:hashes};state.pending=null
 await write(path.join(folder,'publisher.json'),JSON.stringify(state),{privateFile:true})
 return manifest
}

export async function publishRepository(options){
 const folder=await keysFolder(options.keys),lock=path.join(folder,'publisher.lock')
 // A killed owner leaves this lock and its durable pending claim for deliberate
 // recovery. Concurrent writers must never sign the same role version twice.
 const handle=await fs.open(lock,'wx',0o600)
 try{
  await handle.writeFile(JSON.stringify({pid:process.pid,createdAt:new Date().toISOString()}));await handle.sync()
  return await buildPublication(options)
 }finally{await handle.close();await fs.unlink(lock)}
}

async function main(){
 const [operation,...arguments_]=process.argv.slice(2),options={}
 for(let i=0;i<arguments_.length;i+=2){const name=arguments_[i],value=arguments_[i+1];if(!['--keys','--out','--catalogs','--artifacts'].includes(name)||!value||options[name])throw Error('Use explicit keys/output/catalog/artifact options.');options[name]=value}
 if(!options['--keys']||!options['--out'])throw Error('Provide --keys outside Git and a new --out directory.')
 if(operation==='init')return initializeRepository({keys:options['--keys'],output:options['--out']})
 if(!['publish','refresh'].includes(operation))throw Error('Choose init, publish or refresh.')
 let catalogs
 if(operation==='publish'){
  if(!options['--catalogs'])throw Error('Provide both reviewed catalogs.')
  await ordinary(options['--catalogs'],{maximum:4*1024**2})
  catalogs=JSON.parse(await fs.readFile(options['--catalogs'],'utf8'))
 }
 return publishRepository({keys:options['--keys'],output:options['--out'],catalogs,artifacts:options['--artifacts'],refresh:operation==='refresh'})
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().then(result=>process.stdout.write(JSON.stringify(result)+'\n')).catch(error=>{process.stderr.write(error.message+'\n');process.exitCode=1})
